# ============================================================
# pages/06_driver_rating.py — Driver Performance Rating
# ============================================================
# What this page does:
#
#   Computes a composite rating (0-100) for every driver
#   based on 6 measurable signals from the race data.
#
#   The 6 signals:
#     1. Finish Score       — final race position
#     2. Positions Gained   — grid vs finish delta
#     3. Race Pace          — median clean lap time vs field
#     4. Consistency        — lap-time std deviation
#     5. Qualifying         — qualifying position (optional)
#     6. Teammate Delta     — pace vs direct teammate
#
#   Three views:
#     Tab 1 — Bar chart of final ratings (ranked)
#     Tab 2 — Radar chart (compare up to 4 drivers)
#     Tab 3 — Score heatmap (all drivers × all metrics)
#
#   Weight sliders let users change how much each signal
#   contributes — great for showing "what if I weighted
#   pace more than finishing position?"
# ============================================================

import streamlit as st
import pandas as pd
from utils.data_loader import compute_driver_ratings, load_session
from utils.chart_helpers import (driver_rating_bar, driver_radar_chart,
                                  score_heatmap)

st.set_page_config(page_title='Driver Rating · F1', layout='wide')

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
           margin-bottom:4px'>Driver Performance Rating</h1>
<p style='color:#555577;margin-bottom:4px'>
  A composite rating built from 6 data signals — goes beyond
  just finishing position to measure true race performance.
</p>
<div style='display:inline-block;background:#0f3460;
            border:1px solid #1e4a80;border-radius:6px;
            padding:5px 14px;margin-bottom:20px;font-size:13px'>
  📍 Showing: <b style='color:white'>{loaded_year} {event_name}</b>
  &nbsp;·&nbsp;
  <span style='color:#555577'>Not right? Go to Home and reload.</span>
</div>
""", unsafe_allow_html=True)

# ── Methodology explainer ─────────────────────────────────────
with st.expander('📖  How the rating works', expanded=False):
    st.markdown("""
    Each driver is scored on **6 independent signals**. Every signal is
    normalized to **0–100** so they can be fairly combined regardless of
    their original units (seconds, positions, etc.).

    | Signal | What it measures | Raw value |
    |---|---|---|
    | **Finish Score** | Final race position | P1=100, last=0 |
    | **Positions Gained** | Grid position vs finish | +5 places = high score |
    | **Race Pace** | Median clean lap time vs field | Lower time = higher score |
    | **Consistency** | Lap time std deviation | Lower deviation = higher score |
    | **Qualifying** | Qualifying position | Pole = 100 |
    | **Teammate Delta** | Pace vs direct teammate | Beat teammate = higher score |

    The final **Rating** is a weighted average of all 6 scores.
    Use the sliders below to change the weights and see how the
    ranking changes — this shows sensitivity to assumptions.

    > **Why normalize?** Raw lap times (~90s) and positions (1–20)
    > can't be added directly. Normalizing puts everything on the
    > same 0–100 scale so each signal contributes fairly.
    """)

st.divider()

# ── Weight controls ───────────────────────────────────────────
st.markdown("#### ⚖️ Adjust signal weights")
st.markdown("""
<p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
  Change how much each signal contributes to the final rating.
  Weights don't need to sum to 100 — they're normalized automatically.
</p>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

with col1:
    w_finish = st.slider('🏁 Finish Position', 0, 100, 25, 5)
with col2:
    w_gained = st.slider('📈 Positions Gained', 0, 100, 15, 5)
with col3:
    w_pace   = st.slider('⚡ Race Pace',        0, 100, 25, 5)
with col4:
    w_consist= st.slider('📊 Consistency',      0, 100, 15, 5)
with col5:
    w_quali  = st.slider('⏱ Qualifying',        0, 100, 10, 5)
with col6:
    w_tmmate = st.slider('👥 Teammate Delta',   0, 100, 10, 5)

# Normalize weights so they sum to 1
total = w_finish + w_gained + w_pace + w_consist + w_quali + w_tmmate
if total == 0:
    st.error('At least one weight must be above 0.')
    st.stop()

weights = {
    'finish'          : w_finish  / total,
    'positions_gained': w_gained  / total,
    'pace'            : w_pace    / total,
    'consistency'     : w_consist / total,
    'quali'           : w_quali   / total,
    'teammate'        : w_tmmate  / total,
}

# Show effective weights
eff_cols = st.columns(6)
labels   = ['Finish', 'Pos Gained', 'Pace',
            'Consistency', 'Qualifying', 'Teammate']
vals     = [w_finish, w_gained, w_pace, w_consist, w_quali, w_tmmate]
for col, label, val in zip(eff_cols, labels, vals):
    with col:
        st.markdown(f"""
        <div style='text-align:center;color:#555577;font-size:11px'>
          {label}<br>
          <span style='color:#e63946;font-size:15px;font-weight:700'>
            {val/total*100:.0f}%
          </span>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Optionally load qualifying session ────────────────────────
# Qualifying data adds the quali score dimension.
# We make it optional because some sessions (sprints, practice)
# don't have a matching qualifying session.
use_quali = st.toggle(
    'Include qualifying data for Qualifying Score',
    value=True,
    help='Loads the qualifying session for this GP. '
         'Takes ~15s on first load.'
)

quali_session = None
if use_quali and w_quali > 0:
    with st.spinner('Loading qualifying session...'):
        try:
            quali_session, _ = load_session(
                loaded_year, loaded_race, 'Q'
            )
        except Exception as e:
            st.warning(f'Could not load qualifying data: {e}. '
                       'Qualifying score will be set to 50 for all drivers.')

# ── Compute ratings ───────────────────────────────────────────
with st.spinner('Computing driver ratings...'):
    ratings = compute_driver_ratings(
        race_session  = session,
        race_laps     = laps,
        quali_session = quali_session,
        weights       = weights,
    )

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    '🏆  Rankings',
    '🕸️  Radar Chart',
    '🔥  Score Heatmap',
])

with tab1:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      Drivers ranked by composite rating. Bars colored by team.
      Hover for full details. Change the weight sliders above
      to see how the ranking shifts.
    </p>
    """, unsafe_allow_html=True)

    fig_bar = driver_rating_bar(ratings)
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Full ratings table ────────────────────────────────────
    with st.expander('📋  Full ratings table'):
        display = ratings[[
            'Driver', 'Name', 'Team', 'Finish', 'GridPos',
            'positions_gained',
            'score_finish', 'score_positions_gained', 'score_pace',
            'score_consistency', 'score_quali', 'score_teammate',
            'Rating'
        ]].copy()

        display.columns = [
            'Driver', 'Name', 'Team', 'Finish', 'Grid',
            'Pos Gained',
            'S:Finish', 'S:Pos Gained', 'S:Pace',
            'S:Consistency', 'S:Qualifying', 'S:Teammate',
            'Rating'
        ]

        # Round score columns
        score_cols = ['S:Finish', 'S:Pos Gained', 'S:Pace',
                      'S:Consistency', 'S:Qualifying', 'S:Teammate']
        display[score_cols] = display[score_cols].round(1)
        display['Rating']   = display['Rating'].round(1)

        st.dataframe(display, use_container_width=True, hide_index=True)

        # Download button
        csv = display.to_csv(index=False)
        st.download_button(
            label     = '⬇️  Download as CSV',
            data      = csv,
            file_name = f'f1_ratings_{loaded_year}_{loaded_race}.csv',
            mime      = 'text/csv',
        )

with tab2:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      Select up to 4 drivers to compare on all 6 dimensions.
      A larger polygon area = better overall performance.
      The <b style='color:#ccccdd'>shape</b> reveals
      strengths and weaknesses — e.g. strong in Pace but weak
      in Consistency = fast but erratic.
    </p>
    """, unsafe_allow_html=True)

    all_drivers  = ratings['Driver'].tolist()
    top4_default = all_drivers[:4]

    radar_drivers = st.multiselect(
        'Select drivers to compare (max 4)',
        options = all_drivers,
        default = top4_default,
        max_selections=4,
        format_func=lambda d: f"{d}  —  "
                              f"{ratings.loc[ratings['Driver']==d, 'Name'].values[0]}"
                              if d in ratings['Driver'].values else d,
    )

    if len(radar_drivers) < 2:
        st.info('Select at least 2 drivers to compare.')
    else:
        fig_radar = driver_radar_chart(ratings, radar_drivers)
        st.plotly_chart(fig_radar, use_container_width=True)

with tab3:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      Each cell = a driver's score (0–100) on one metric.
      <span style='color:#57c785'>Green</span> = high score ·
      <span style='color:#e63946'>Red</span> = low score.
      Rows ordered by overall rating. Instantly shows who
      dominated which dimension.
    </p>
    """, unsafe_allow_html=True)

    fig_heat = score_heatmap(ratings)
    st.plotly_chart(fig_heat, use_container_width=True)

# ── Key insight box ───────────────────────────────────────────
st.divider()
top3 = ratings.head(3)
insights = []
for _, row in top3.iterrows():
    strongest = max(
        [('Finish',      row['score_finish']),
         ('Pace',        row['score_pace']),
         ('Consistency', row['score_consistency']),
         ('Pos Gained',  row['score_positions_gained']),
         ('Teammate',    row['score_teammate'])],
        key=lambda x: x[1]
    )
    insights.append(
        f"**{row['Driver']}** ({row['Name'].split()[-1]}) — "
        f"Rating **{row['Rating']}** · "
        f"Strongest in **{strongest[0]}** ({strongest[1]:.0f}/100)"
    )

st.markdown("#### 🏆 Top 3 performers this race")
for insight in insights:
    st.markdown(f"- {insight}")
