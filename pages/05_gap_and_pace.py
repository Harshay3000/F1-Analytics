# ============================================================
# pages/05_gap_and_pace.py — Gap to Leader & Race Pace
# ============================================================
# What this page does:
#
#   Tab 1 — Gap to Leader
#     The classic F1 broadcast chart. Shows every driver's
#     time gap to the race leader, lap by lap.
#     - Flat line   = matching the leader's pace exactly
#     - Rising line = falling behind
#     - Dropping line = closing in (or leader pitted)
#     - Sudden spike/drop = pit stop
#
#   Tab 2 — Race Pace
#     Box plot of each driver's lap time distribution.
#     Tells you who was fast AND consistent, not just who
#     set one quick lap.
#
# Why these two charts together?
#   Gap to leader shows WHAT happened in the race.
#   Race pace shows WHY — who had the underlying speed.
# ============================================================

import streamlit as st
import pandas as pd
from utils.chart_helpers import gap_to_leader_chart, race_pace_chart

st.set_page_config(page_title='Gap & Race Pace · F1', layout='wide')

# ── Guards ────────────────────────────────────────────────────
if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the **Home** page and '
               'click **Load Session**.')
    st.stop()

if not st.session_state.get('loaded_race'):
    st.warning('No session loaded. Go to the **Home** page and '
               'click **Load Session**.')
    st.stop()

session        = st.session_state['session_obj']
laps           = st.session_state['laps_df']
loaded_year    = st.session_state['loaded_year']
loaded_race    = st.session_state['loaded_race']
event_name     = session.event.get('EventName', loaded_race)

# ── Header ────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='color:white;font-size:1.6rem;font-weight:800;
           margin-bottom:4px'>Gap to Leader & Race Pace</h1>
<p style='color:#555577;margin-bottom:4px'>
  Understand the race story and underlying pace of every driver.
</p>
<div style='display:inline-block;background:#0f3460;
            border:1px solid #1e4a80;border-radius:6px;
            padding:5px 14px;margin-bottom:20px;font-size:13px'>
  📍 Showing: <b style='color:white'>{loaded_year} {event_name}</b>
  &nbsp;·&nbsp;
  <span style='color:#555577'>Not right? Go to Home and reload.</span>
</div>
""", unsafe_allow_html=True)

# ── Driver filter (shared across both tabs) ───────────────────
all_drivers = sorted(laps['Driver'].unique().tolist())
default_top6 = (
    laps.groupby('Driver')['Position']
    .last().dropna().sort_values().head(6).index.tolist()
)

st.markdown("**Highlight drivers**")
selected_drivers = st.multiselect(
    label            = 'Highlight drivers',
    options          = all_drivers,
    default          = default_top6,
    label_visibility = 'collapsed',
    help             = 'Gap chart: selected drivers shown in color. '
                       'Pace chart: only selected drivers shown.',
)
if not selected_drivers:
    selected_drivers = default_top6

st.divider()

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2 = st.tabs(['📉  Gap to Leader', '📦  Race Pace'])

with tab1:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      Each line shows a driver's cumulative time gap to the race leader.
      <br>
      <b style='color:#ccccdd'>Rising line</b> = losing time to leader &nbsp;·&nbsp;
      <b style='color:#ccccdd'>Falling line</b> = closing the gap &nbsp;·&nbsp;
      <b style='color:#ccccdd'>Sharp spike</b> = pit stop &nbsp;·&nbsp;
      <b style='color:#ccccdd'>Dotted line at 0</b> = leader
    </p>
    """, unsafe_allow_html=True)

    with st.spinner('Calculating gaps...'):
        fig_gap = gap_to_leader_chart(laps, session, selected_drivers)
        st.plotly_chart(fig_gap, use_container_width=True)

    # ── Gap at end of race table ──────────────────────────────
    with st.expander('📋  Final gap to winner'):
        laps_copy = laps.copy()
        laps_copy['LapTimeSeconds'] = laps_copy['LapTime'].dt.total_seconds()
        clean = laps_copy[laps_copy['IsAccurate'] == True].copy()

        # Compute cumulative times
        cum_rows = []
        for driver in clean['Driver'].unique():
            dlaps = (clean[clean['Driver'] == driver]
                     .sort_values('LapNumber').copy())
            dlaps['CumTime'] = dlaps['LapTimeSeconds'].cumsum()
            cum_rows.append(dlaps[['Driver', 'LapNumber', 'CumTime']])

        if cum_rows:
            cum_df = pd.concat(cum_rows, ignore_index=True)
            # Get each driver's final cumulative time
            final_cum = (
                cum_df.groupby('Driver')['CumTime'].last().reset_index()
            )
            winner_time = final_cum['CumTime'].min()
            final_cum['Gap to Winner'] = final_cum['CumTime'] - winner_time
            final_cum['Gap to Winner'] = final_cum['Gap to Winner'].apply(
                lambda x: '—' if x < 0.001 else f'+{x:.3f}s'
            )

            # Add driver names and finishing positions
            fin_pos = (laps.groupby('Driver')['Position']
                       .last().dropna().astype(int).reset_index()
                       .rename(columns={'Position': 'Pos'}))
            final_cum = final_cum.merge(fin_pos, on='Driver', how='left')

            name_map = {}
            for d in clean['Driver'].unique():
                try:
                    info = session.get_driver(d)
                    name_map[d] = info['FullName']
                except Exception:
                    name_map[d] = d
            final_cum['Name'] = final_cum['Driver'].map(name_map)
            final_cum = final_cum.sort_values('Pos')

            st.dataframe(
                final_cum[['Pos', 'Driver', 'Name', 'Gap to Winner']]
                .rename(columns={'Pos': 'Position'}),
                use_container_width=True,
                hide_index=True,
            )

with tab2:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      Box plot of clean lap times for each driver.
      The <b style='color:#ccccdd'>box</b> shows the middle 50% of laps
      (interquartile range). The <b style='color:#ccccdd'>line inside</b>
      = median pace. Dots outside = outlier laps.
      <br>
      <b>Narrow box + low median</b> = fast AND consistent — the ideal.
      Safety car laps and pit-out laps are automatically filtered out.
    </p>
    """, unsafe_allow_html=True)

    with st.spinner('Building pace chart...'):
        fig_pace = race_pace_chart(laps, session, selected_drivers)
        st.plotly_chart(fig_pace, use_container_width=True)

    # ── Pace stats table ──────────────────────────────────────
    with st.expander('📋  Pace statistics per driver'):
        laps_copy2 = laps.copy()
        laps_copy2['LapTimeSeconds'] = \
            laps_copy2['LapTime'].dt.total_seconds()
        clean2 = laps_copy2[laps_copy2['IsAccurate'] == True].copy()
        p95    = clean2['LapTimeSeconds'].quantile(0.95)
        clean2 = clean2[clean2['LapTimeSeconds'] <= p95]

        pace_rows = []
        for driver in selected_drivers:
            dlaps = clean2[clean2['Driver'] == driver]['LapTimeSeconds']
            if len(dlaps) < 3:
                continue
            try:
                info = session.get_driver(driver)
                name = info['FullName']
                team = info['TeamName']
            except Exception:
                name, team = driver, '—'

            pace_rows.append({
                'Driver'  : driver,
                'Name'    : name,
                'Team'    : team,
                'Median'  : f"{dlaps.median():.3f}s",
                'Best'    : f"{dlaps.min():.3f}s",
                'Worst'   : f"{dlaps.max():.3f}s",
                'Std Dev' : f"{dlaps.std():.3f}s",
                'Laps'    : len(dlaps),
            })

        if pace_rows:
            pace_df = pd.DataFrame(pace_rows)
            st.dataframe(
                pace_df,
                use_container_width=True,
                hide_index=True,
            )

    # ── What to look for ─────────────────────────────────────
    st.markdown("""
    <div style='background:#16213e;border:1px solid #1e1e3a;
                border-radius:10px;padding:20px;margin-top:16px'>
      <div style='color:white;font-weight:600;margin-bottom:12px'>
        📖 How to read this chart
      </div>
      <div style='color:#8888aa;font-size:13px;line-height:1.8'>
        <b style='color:#ccccdd'>Median line position</b>
        — lower = faster overall race pace<br>
        <b style='color:#ccccdd'>Box height</b>
        — smaller = more consistent lap-to-lap<br>
        <b style='color:#ccccdd'>Outlier dots above the box</b>
        — slow laps from traffic, minor mistakes, or late SC periods<br>
        <b style='color:#ccccdd'>Outlier dots below the box</b>
        — rare fast laps, often on fresh tyres early in a stint
      </div>
    </div>
    """, unsafe_allow_html=True)
