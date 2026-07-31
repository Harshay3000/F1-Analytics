# ============================================================
# pages/04_circuit_map.py — Circuit Map & Racing Line
# ============================================================

import streamlit as st
import pandas as pd
from utils.data_loader import derive_driver_list
from utils.chart_helpers import circuit_map_chart

st.set_page_config(page_title='Circuit Map · F1', layout='wide')

if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

session = st.session_state['session_obj']
laps    = st.session_state['laps_df']

# Always use the confirmed loaded race — never the stale selectbox value
loaded_year    = st.session_state['loaded_year']
loaded_race    = st.session_state['loaded_race']
loaded_session = st.session_state['loaded_session']

st.markdown(f"""
<h1 style='color:white;font-size:1.6rem;font-weight:800;
           margin-bottom:4px'>Circuit Map</h1>
<p style='color:#555577;margin-bottom:24px'>
  GPS-based circuit layout from <b style='color:white'>
  {loaded_year} {loaded_race}</b>.
  Green = fast / high throttle · Red = slow / braking.
</p>
""", unsafe_allow_html=True)

# ── Driver list from already-loaded session ───────────────────
driver_list   = derive_driver_list(session)
driver_abbrs  = [d['abbr'] for d in driver_list]
driver_labels = {d['abbr']: f"{d['abbr']}  —  {d['name']}" for d in driver_list}

col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

with col1:
    primary_driver = st.selectbox(
        '🔴  Primary driver (colored line)',
        options     = driver_abbrs,
        index       = 0,
        format_func = lambda x: driver_labels.get(x, x),
    )

with col2:
    overlay_driver = st.selectbox(
        '🔵  Overlay driver (optional)',
        options     = ['None'] + driver_abbrs,
        index       = 0,
        format_func = lambda x: 'No overlay' if x == 'None'
                                else driver_labels.get(x, x),
    )

with col3:
    color_channel = st.selectbox('Color by', ['Speed', 'Throttle', 'Brake'])

with col4:
    map_session = st.selectbox(
        'Session',
        options     = ['Q', 'R'],
        format_func = lambda x: {'Q': '⏱ Quali', 'R': '🏁 Race'}[x],
    )

st.divider()

# ── Telemetry loader — keyed on loaded race, not selectbox race ──
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

with st.spinner(f'Loading {primary_driver} telemetry...'):
    lap1, tel1 = _get_telemetry(loaded_year, loaded_race,
                                 primary_driver, map_session)

if tel1 is None:
    st.error('Could not load telemetry. Try a different driver or session.')
    st.stop()

tel2_data    = None
overlay_name = None
if overlay_driver != 'None' and overlay_driver != primary_driver:
    with st.spinner(f'Loading {overlay_driver} telemetry...'):
        _, tel2_data = _get_telemetry(loaded_year, loaded_race,
                                       overlay_driver, map_session)
    overlay_name = overlay_driver

# ── Chart ─────────────────────────────────────────────────────
st.markdown(f"""
<p style='color:#8888aa;font-size:13px;margin-bottom:12px'>
  Showing <b style='color:#e63946'>{primary_driver}</b>'s fastest
  {map_session} lap colored by <b style='color:white'>{color_channel}</b>.
  {'Overlay: <b style="color:#4a90d9">' + overlay_name + '</b> (blue line).'
   if overlay_name else ''}
  Hover for exact values.
</p>
""", unsafe_allow_html=True)

fig = circuit_map_chart(tel1, primary_driver, tel2_data,
                         overlay_name, color_channel)
st.plotly_chart(fig, use_container_width=True)

# ── Stats ─────────────────────────────────────────────────────
st.markdown("#### Telemetry summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric('Top Speed',       f"{tel1['Speed'].max():.1f} km/h")
c2.metric('Avg Speed',       f"{tel1['Speed'].mean():.1f} km/h")
c3.metric('Full Throttle %', f"{(tel1['Throttle'] == 100).mean() * 100:.1f}%")
c4.metric('Braking %',       f"{tel1['Brake'].astype(float).mean() * 100:.1f}%")

with st.expander('📋  Raw telemetry (first 50 samples)'):
    cols = [c for c in ['Distance','Speed','Throttle','Brake','nGear','DRS','X','Y']
            if c in tel1.columns]
    display = tel1[cols].head(50).copy()
    display['Brake'] = display['Brake'].astype(int)
    st.dataframe(display.round(2), use_container_width=True, hide_index=True)

st.markdown("""
<div style='color:#333355;font-size:12px;margin-top:16px'>
  Circuit layout derived from FastF1 GPS telemetry X/Y coordinates.
</div>
""", unsafe_allow_html=True)
