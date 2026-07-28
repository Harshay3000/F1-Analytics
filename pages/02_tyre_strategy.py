# ============================================================
# pages/02_tyre_strategy.py — Tyre Strategy
# ============================================================

import streamlit as st
import pandas as pd
from utils.data_loader import COMPOUND_COLORS, derive_stints, derive_finishing_order
from utils.chart_helpers import tyre_strategy_chart

st.set_page_config(page_title='Tyre Strategy · F1', layout='wide')

if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

# ── Use already-loaded data directly from session state ───────
# This guarantees charts always match whatever race was loaded,
# with no separate API call that could return stale cached data.
session = st.session_state['session_obj']
laps    = st.session_state['laps_df']

# Show which race is actually loaded so user can confirm it's correct
loaded_year = st.session_state.get('loaded_year')
loaded_race = st.session_state.get('loaded_race')

if not loaded_year or not loaded_race:
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

event_name = session.event.get('EventName', loaded_race)

st.markdown(f"""
<h1 style='color:white;font-size:1.6rem;font-weight:800;
           margin-bottom:4px'>Tyre Strategy</h1>
<p style='color:#555577;margin-bottom:4px'>
  Each bar = one tyre stint. Width = laps on that compound.
  Drivers ordered by finishing position.
</p>
<div style='display:inline-block;background:#0f3460;border:1px solid #1e4a80;
            border-radius:6px;padding:5px 14px;margin-bottom:20px;font-size:13px'>
  📍 Showing: <b style='color:white'>{loaded_year} {event_name}</b>
  &nbsp;·&nbsp; <span style='color:#555577'>
  Not what you expected? Go to Home and reload.</span>
</div>
""", unsafe_allow_html=True)

# ── Derive data from loaded laps ──────────────────────────────
with st.spinner('Building stint data...'):
    stints          = derive_stints(laps, session)
    finishing_order = derive_finishing_order(laps, session)

# ── Filters ───────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 1])

with col_f1:
    all_drivers = [d['abbr'] for d in finishing_order]
    selected_drivers = st.multiselect(
        'Filter drivers',
        options = all_drivers,
        default = all_drivers,
        help    = 'Deselect drivers to hide them from the chart',
    )

with col_f2:
    compounds_used = stints['Compound'].unique().tolist()
    selected_compounds = st.multiselect(
        'Filter compounds',
        options = compounds_used,
        default = compounds_used,
    )

# Apply filters
filtered_stints = stints[
    stints['Driver'].isin(selected_drivers) &
    stints['Compound'].isin(selected_compounds)
]
filtered_order = [d for d in finishing_order
                  if d['abbr'] in selected_drivers]

st.divider()

# ── Chart ─────────────────────────────────────────────────────
if len(filtered_stints) == 0:
    st.info('No data matches the selected filters.')
else:
    with st.spinner('Rendering chart...'):
        fig = tyre_strategy_chart(filtered_stints, filtered_order)
        st.plotly_chart(fig, use_container_width=True)

# ── Compound color legend ──────────────────────────────────────
st.markdown("**Compound key**")
legend_cols = st.columns(max(1, len(compounds_used)))
for col, compound in zip(legend_cols, compounds_used):
    color = COMPOUND_COLORS.get(compound, '#888888')
    with col:
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:8px'>
          <div style='width:14px;height:14px;border-radius:3px;
                      background:{color}'></div>
          <span style='color:#ccccdd;font-size:13px'>
            {compound.capitalize()}
          </span>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Stint details table ────────────────────────────────────────
with st.expander('📋  Detailed stint data'):
    display_stints = filtered_stints.copy()

    driver_names = {d['abbr']: d['name'] for d in finishing_order}
    display_stints['Name'] = display_stints['Driver'].map(driver_names)

    compound_emoji = {
        'SOFT': '🔴', 'MEDIUM': '🟡', 'HARD': '⚪',
        'INTERMEDIATE': '🟢', 'WET': '🔵', 'UNKNOWN': '⚫',
    }
    display_stints['Tyre'] = display_stints['Compound'].map(
        lambda c: f"{compound_emoji.get(c, '')} {c.capitalize()}"
    )

    pos_map = {d['abbr']: d['position'] for d in finishing_order}
    display_stints['Finish'] = display_stints['Driver'].map(
        lambda d: f"P{pos_map.get(d, '?')}"
    )

    table = display_stints[[
        'Finish', 'Driver', 'Name', 'Stint', 'Tyre',
        'StartLap', 'EndLap', 'LapCount'
    ]].rename(columns={
        'Stint'   : 'Stint #',
        'StartLap': 'Start Lap',
        'EndLap'  : 'End Lap',
        'LapCount': 'Laps on Tyre',
    }).sort_values(['Finish', 'Stint #'])

    st.dataframe(table, use_container_width=True, hide_index=True)

# ── Strategy summary stats ────────────────────────────────────
st.markdown("#### Strategy summary")
col1, col2, col3 = st.columns(3)

avg_stops = stints.groupby('Driver')['Stint'].max().mean()
most_common = stints['Compound'].mode().iloc[0] if len(stints) > 0 else 'N/A'
longest_stint = stints.loc[stints['LapCount'].idxmax()] if len(stints) > 0 else None

col1.metric('Avg pit stops per driver', f"{avg_stops:.1f}")
col2.metric('Most used compound', most_common.capitalize())
if longest_stint is not None:
    col3.metric('Longest stint',
                f"{int(longest_stint['LapCount'])} laps  "
                f"({longest_stint['Driver']} · "
                f"{longest_stint['Compound'].capitalize()})")
