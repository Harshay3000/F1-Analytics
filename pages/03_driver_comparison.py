# ============================================================
# pages/03_driver_comparison.py — Driver Comparison
# ============================================================

import streamlit as st
import pandas as pd
from utils.data_loader import derive_driver_list
from utils.chart_helpers import speed_trace_chart

st.set_page_config(page_title='Driver Comparison · F1', layout='wide')

if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

session = st.session_state['session_obj']
laps    = st.session_state['laps_df']

st.markdown("""
<h1 style='color:white;font-size:1.6rem;font-weight:800;
           margin-bottom:4px'>Driver Comparison</h1>
<p style='color:#555577;margin-bottom:24px'>
  Head-to-head telemetry on the fastest lap.
  Laps aligned by distance so you can see exactly where
  each driver is faster or brakes later.
</p>
""", unsafe_allow_html=True)

# ── Driver list from already-loaded session (no extra API call) ──
driver_list   = derive_driver_list(session)
driver_abbrs  = [d['abbr'] for d in driver_list]
driver_labels = {
    d['abbr']: f"{d['abbr']}  —  {d['name']}  ({d['team']})"
    for d in driver_list
}

col_d1, col_d2, col_s = st.columns([2, 2, 1])

with col_d1:
    d1 = st.selectbox(
        '🔴  Driver 1',
        options     = driver_abbrs,
        index       = 0,
        format_func = lambda x: driver_labels.get(x, x),
    )

with col_d2:
    d2_default = driver_abbrs[1] if len(driver_abbrs) > 1 else driver_abbrs[0]
    d2 = st.selectbox(
        '🔵  Driver 2',
        options     = driver_abbrs,
        index       = driver_abbrs.index(d2_default),
        format_func = lambda x: driver_labels.get(x, x),
    )

with col_s:
    compare_session = st.selectbox(
        'Session',
        options     = ['Q', 'R'],
        format_func = lambda x: {'Q': '⏱ Quali', 'R': '🏁 Race'}[x],
        help        = 'Qualifying gives cleaner single laps.',
    )

if d1 == d2:
    st.warning('Please select two different drivers.')
    st.stop()

st.divider()

# ── Get telemetry from already-loaded laps ────────────────────
# We load telemetry for the chosen session type separately only
# if it differs from the loaded session type. For the same
# session, pick directly from the laps DataFrame in session_state.
@st.cache_data(show_spinner=False)
def _get_telemetry(year, race, driver, sess_type):
    import fastf1, os, tempfile
    cache_dir = os.path.join(tempfile.gettempdir(), 'fastf1_cache')
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    fastf1.set_log_level('WARNING')
    s = fastf1.get_session(year, race, sess_type)
    s.load(telemetry=True, laps=True, weather=False)
    dlaps = s.laps.pick_driver(driver)
    if len(dlaps) == 0:
        return None, None
    fastest = dlaps.pick_fastest()
    tel = fastest.get_telemetry().add_distance()
    return fastest, tel

loaded_year    = st.session_state['loaded_year']
loaded_race    = st.session_state['loaded_race']
loaded_session = st.session_state['loaded_session']

col_a, col_b = st.columns(2)
with col_a:
    with st.spinner(f'Loading {d1} telemetry...'):
        lap1, tel1 = _get_telemetry(loaded_year, loaded_race, d1, compare_session)

with col_b:
    with st.spinner(f'Loading {d2} telemetry...'):
        lap2, tel2 = _get_telemetry(loaded_year, loaded_race, d2, compare_session)

if tel1 is None or tel2 is None:
    st.error('Could not load telemetry for one or both drivers. '
             'Try switching between Quali and Race.')
    st.stop()

# ── Stat cards ────────────────────────────────────────────────
def lap_time_str(lap):
    t    = lap['LapTime'].total_seconds()
    mins = int(t // 60)
    secs = t % 60
    return f"{mins}:{secs:06.3f}"

def stats(tel):
    return {
        'max_speed'   : tel['Speed'].max(),
        'avg_throttle': tel['Throttle'].mean(),
        'brake_pct'   : tel['Brake'].astype(float).mean() * 100,
    }

s1, s2 = stats(tel1), stats(tel2)
st.markdown("#### Lap stats")
stat_cols = st.columns(4)
metrics = [
    ('Lap Time',         lap_time_str(lap1),          lap_time_str(lap2)),
    ('Max Speed (km/h)', f"{s1['max_speed']:.1f}",    f"{s2['max_speed']:.1f}"),
    ('Avg Throttle %',   f"{s1['avg_throttle']:.1f}", f"{s2['avg_throttle']:.1f}"),
    ('Braking %',        f"{s1['brake_pct']:.1f}",    f"{s2['brake_pct']:.1f}"),
]
for col, (label, v1, v2) in zip(stat_cols, metrics):
    with col:
        st.markdown(f"""
        <div style='background:#16213e;border:1px solid #1e1e3a;
                    border-radius:10px;padding:16px'>
          <div style='color:#555577;font-size:11px;letter-spacing:0.5px;
                      margin-bottom:8px'>{label.upper()}</div>
          <div style='display:flex;justify-content:space-between'>
            <div>
              <div style='color:#e63946;font-size:10px'>{d1}</div>
              <div style='color:white;font-size:18px;font-weight:700'>{v1}</div>
            </div>
            <div style='text-align:right'>
              <div style='color:#4a90d9;font-size:10px'>{d2}</div>
              <div style='color:white;font-size:18px;font-weight:700'>{v2}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Speed trace chart ─────────────────────────────────────────
st.markdown("#### Speed · Throttle · Brake trace")
st.markdown("""
<p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
  X-axis = distance from lap start (meters). Both laps aligned so
  you can compare any corner. Where lines diverge = speed difference,
  later braking, or more throttle.
</p>
""", unsafe_allow_html=True)

fig = speed_trace_chart(tel1, tel2, d1, d2, lap1, lap2)
st.plotly_chart(fig, use_container_width=True)

# ── Sector breakdown ──────────────────────────────────────────
with st.expander('📋  Sector time breakdown'):
    def fmt_sector(val):
        if pd.isna(val): return 'N/A'
        t = val.total_seconds()
        return f"{int(t // 60)}:{t % 60:06.3f}"

    st.dataframe(pd.DataFrame({
        'Sector': ['Sector 1', 'Sector 2', 'Sector 3'],
        d1: [fmt_sector(lap1['Sector1Time']),
             fmt_sector(lap1['Sector2Time']),
             fmt_sector(lap1['Sector3Time'])],
        d2: [fmt_sector(lap2['Sector1Time']),
             fmt_sector(lap2['Sector2Time']),
             fmt_sector(lap2['Sector3Time'])],
    }), use_container_width=True, hide_index=True)
