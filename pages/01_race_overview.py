# ============================================================
# pages/01_race_overview.py — Race Overview
# ============================================================
# What this page does:
#   - Tab 1: Lap Time chart (all drivers, interactive)
#   - Tab 2: Position Changes bump chart
#   - Both charts respond to a driver multi-select filter
#
# How it reads shared data:
#   - app.py stores the loaded session in st.session_state
#   - This page reads from session_state — no re-downloading
# ============================================================

import streamlit as st
import pandas as pd
from utils.chart_helpers import lap_time_chart, position_chart

st.set_page_config(page_title='Race Overview · F1', layout='wide')

# ── Guard: require session to be loaded ───────────────────────
if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the Home page and click **Load Session**.')
    st.stop()   # stop() halts execution of the rest of this page

session = st.session_state['session_obj']
laps    = st.session_state['laps_df']

# ── Page header ───────────────────────────────────────────────
loaded_year = st.session_state.get('loaded_year')
loaded_race = st.session_state.get('loaded_race')

if not loaded_year or not loaded_race:
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

event_name = session.event.get('EventName', loaded_race)

st.markdown(f"""
<h1 style='color:white;font-size:1.6rem;font-weight:800;
           margin-bottom:4px'>Race Overview</h1>
<p style='color:#555577;margin-bottom:4px'>
  Lap times and position changes across the full race.
  Click a driver in the legend to hide/show them.
</p>
<div style='display:inline-block;background:#0f3460;border:1px solid #1e4a80;
            border-radius:6px;padding:5px 14px;margin-bottom:20px;font-size:13px'>
  📍 Showing: <b style='color:white'>{loaded_year} {event_name}</b>
  &nbsp;·&nbsp; <span style='color:#555577'>
  Not what you expected? Go to Home and reload.</span>
</div>
""", unsafe_allow_html=True)

# ── Driver filter ─────────────────────────────────────────────
# Multiselect lets users choose which drivers to highlight.
# Others are shown as faint gray lines for context.
all_drivers = sorted(laps['Driver'].unique().tolist())

# Default: highlight top 5 finishers
default_top5 = (
    laps.groupby('Driver')['Position']
    .last().dropna().sort_values().head(5).index.tolist()
)

st.markdown("**Highlight drivers**")
selected_drivers = st.multiselect(
    label     = 'Highlight drivers',
    options   = all_drivers,
    default   = default_top5,
    label_visibility='collapsed',
    help      = 'Selected drivers are shown in color. Others appear dimmed.',
)

if not selected_drivers:
    selected_drivers = default_top5

st.divider()

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2 = st.tabs(['📈  Lap Times', '🔄  Position Changes'])

with tab1:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:12px'>
      Each line = one driver's lap time per lap.
      Spikes indicate slow laps (pit exits, safety cars).
      Hover over any point to see exact lap time.
    </p>
    """, unsafe_allow_html=True)

    with st.spinner('Rendering chart...'):
        fig_lap = lap_time_chart(laps, session, selected_drivers)
        st.plotly_chart(fig_lap, use_container_width=True)

    # ── Fastest lap table below the chart ─────────────────────
    with st.expander('📋  Fastest lap per driver'):
        fastest_per_driver = (
            laps.groupby('Driver')
            .apply(lambda g: g.nsmallest(1, 'LapTimeSeconds'))
            .reset_index(drop=True)
            [['Driver', 'LapNumber', 'LapTimeSeconds', 'Compound']]
        )
        fastest_per_driver['LapTime'] = fastest_per_driver['LapTimeSeconds'].apply(
            lambda s: f"{int(s // 60)}:{s % 60:06.3f}" if pd.notna(s) else 'N/A'
        )
        fastest_per_driver = fastest_per_driver.sort_values('LapTimeSeconds')
        fastest_per_driver['Gap'] = (
            fastest_per_driver['LapTimeSeconds'] -
            fastest_per_driver['LapTimeSeconds'].iloc[0]
        ).apply(lambda x: f'+{x:.3f}s' if x > 0 else '—')

        st.dataframe(
            fastest_per_driver[['Driver', 'LapNumber',
                                  'LapTime', 'Compound', 'Gap']]
            .rename(columns={'LapNumber': 'On Lap'}),
            use_container_width=True,
            hide_index=True,
        )

with tab2:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:12px'>
      Each line = one driver's position lap by lap.
      P1 is at the top. Lines crossing = overtakes.
      Steep drops = pit stop (position loss while in pits).
    </p>
    """, unsafe_allow_html=True)

    with st.spinner('Rendering chart...'):
        fig_pos = position_chart(laps, session, selected_drivers)
        st.plotly_chart(fig_pos, use_container_width=True)

    # ── Position gained/lost table ─────────────────────────────
    with st.expander('📋  Positions gained / lost'):
        start_pos = laps[laps['LapNumber'] == 1][['Driver', 'Position']] \
                    .rename(columns={'Position': 'StartPos'})
        end_pos   = (
            laps.groupby('Driver')['Position']
            .last().reset_index()
            .rename(columns={'Position': 'EndPos'})
        )
        merged = start_pos.merge(end_pos, on='Driver')
        merged['StartPos'] = pd.to_numeric(merged['StartPos'], errors='coerce')
        merged['EndPos']   = pd.to_numeric(merged['EndPos'],   errors='coerce')
        # Drop NaN BEFORE casting — drivers with no lap 1 position
        # (pit lane starts, early retirements) cause IntCastingNaNError
        merged = merged.dropna(subset=['StartPos', 'EndPos'])
        merged['StartPos']    = merged['StartPos'].astype(int)
        merged['EndPos']      = merged['EndPos'].astype(int)
        merged['Δ Positions'] = merged['StartPos'] - merged['EndPos']
        merged = merged.sort_values('Δ Positions', ascending=False)

        # Color-code the delta column
        def color_delta(val):
            if val > 0: return 'color: #57c785'   # green = gained
            if val < 0: return 'color: #e63946'   # red = lost
            return 'color: #888888'

        st.dataframe(
            merged.rename(columns={
                'StartPos': 'Grid', 'EndPos': 'Finish'
            }).style.applymap(color_delta, subset=['Δ Positions']),
            use_container_width=True,
            hide_index=True,
        )
