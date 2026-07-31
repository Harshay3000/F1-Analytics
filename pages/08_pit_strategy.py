# pit_strategy.py — Pit Stop Strategy Optimizer
import streamlit as st
import pandas as pd
import numpy as np
from utils.data_loader import (
    build_tyre_degradation_model,
    optimize_pit_strategy,
    get_actual_strategies,
    COMPOUND_COLORS,
)
from utils.chart_helpers import (
    strategy_comparison_chart,
    pit_window_heatmap,
)

st.set_page_config(page_title='Pit Strategy · F1', layout='wide')

# ── Guards ────────────────────────────────────────────────────
if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

if not st.session_state.get('loaded_race'):
    st.warning('No session loaded. Go to the **Home** page and click **Load Session**.')
    st.stop()

session     = st.session_state['session_obj']
laps        = st.session_state['laps_df']
loaded_year = st.session_state['loaded_year']
loaded_race = st.session_state['loaded_race']
event_name  = session.event.get('EventName', loaded_race)

# ── Header ────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='color:white;font-size:1.6rem;font-weight:800;margin-bottom:4px'>
  Pit Stop Strategy Optimizer
</h1>
<p style='color:#555577;margin-bottom:4px'>
  Simulates every possible pit strategy and finds the one that
  minimises total predicted race time using the tyre degradation model.
</p>
<div style='display:inline-block;background:#0f3460;border:1px solid #1e4a80;
            border-radius:6px;padding:5px 14px;margin-bottom:20px;font-size:13px'>
  📍 Showing: <b style='color:white'>{loaded_year} {event_name}</b>
  &nbsp;·&nbsp;
  <span style='color:#555577'>Not right? Go to Home and reload.</span>
</div>
""", unsafe_allow_html=True)

with st.expander('⚙️  How the optimizer works', expanded=False):
    st.markdown("""
    #### Brute-force strategy simulation

    **Step 1 — Train degradation model**
    The same Random Forest model from the Tyre Degradation page is trained
    on this race's clean lap data.

    **Step 2 — Simulate all strategies**
    For every possible pit lap and compound combination:
    ```
    total_race_time = Σ predicted_lap_times + pit_loss × n_stops
    ```

    **Step 3 — Rank by total time**
    Lowest predicted total = optimal strategy.

    **Assumptions:**

    | Assumption | Reality |
    |---|---|
    | Pit loss is fixed | Varies ±2-3s per stop |
    | No safety car modelled | SC can flip any strategy |
    | No traffic | Undercut/overcut changes timing |
    | No weather | Rain invalidates dry strategies |

    > This is a simplified model — real F1 teams use far more complex
    > simulations. But the core logic is identical.
    """)

st.divider()

# ── Settings ──────────────────────────────────────────────────
st.markdown("#### ⚙️ Optimizer settings")
col1, col2, col3 = st.columns(3)

with col1:
    pit_loss = st.slider('Pit lane loss (seconds)',
                         min_value=15.0, max_value=35.0,
                         value=22.0, step=0.5,
                         help='Time lost driving through the pit lane. '
                              'Monaco ~24s, Monza ~19s.')
with col2:
    max_stops = st.selectbox('Max stops to evaluate',
                             options=[1, 2], index=0,
                             format_func=lambda x: f'{x}-stop strategies',
                             help='1-stop: instant. 2-stop: ~5-10s.')
with col3:
    selected_driver = st.selectbox(
        'Compare vs driver',
        options=sorted(laps['Driver'].unique().tolist()),
        help="Show this driver's actual strategy vs the optimal."
    )

st.divider()

# ── Train model ───────────────────────────────────────────────
with st.spinner('Training tyre degradation model...'):
    deg_result = build_tyre_degradation_model(laps, session)

if deg_result is None:
    st.error('Not enough data to build the degradation model. Try a different race.')
    st.stop()

total_laps = int(laps['LapNumber'].max())
compounds  = deg_result['training_df']['Compound'].str.upper().unique().tolist()
dry        = [c for c in compounds if c in ['SOFT', 'MEDIUM', 'HARD']]

# ── Run optimizer ─────────────────────────────────────────────
with st.spinner(f'Simulating {max_stops}-stop strategies across all compound combos...'):
    opt_result = optimize_pit_strategy(
        model_result        = deg_result,
        total_laps          = total_laps,
        pit_loss_seconds    = pit_loss,
        compounds_available = dry or compounds,
        max_stops           = max_stops,
    )

if opt_result is None:
    st.error('Could not compute strategies — not enough compound variety in this race.')
    st.stop()

actual_df = get_actual_strategies(laps, session)

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    '🏆  Optimal vs Actual',
    '📍  Pit Window',
    '📋  All Strategies',
])

with tab1:
    opt = opt_result['optimal']
    one = opt_result['one_stop']
    two = opt_result['two_stop']

    st.markdown("#### 🥇 Optimal strategy found")
    ocol1, ocol2, ocol3 = st.columns(3)

    def strat_card(col, title, strat, border='#1e4a80'):
        if strat is None:
            return
        with col:
            st.markdown(f"""
            <div style='background:#16213e;border:1px solid {border};
                        border-radius:10px;padding:16px;height:110px'>
              <div style='color:#8888aa;font-size:11px;letter-spacing:0.5px'>
                {title}</div>
              <div style='color:white;font-weight:700;font-size:13px;margin:6px 0'>
                {strat['label']}</div>
              <div style='color:#aaaacc;font-size:12px'>
                Est. {strat['total_time']/60:.1f} min total</div>
            </div>
            """, unsafe_allow_html=True)

    strat_card(ocol1, 'OVERALL OPTIMAL', opt, '#2a9d8f')
    strat_card(ocol2, 'BEST 1-STOP',     one)
    strat_card(ocol3, 'BEST 2-STOP',     two)

    st.markdown("<br>", unsafe_allow_html=True)

    # Driver actual vs optimal
    drv_actual = actual_df[actual_df['Driver'] == selected_driver]
    if len(drv_actual) > 0:
        drv_row = drv_actual.iloc[0]
        st.markdown(f"#### {selected_driver} — {drv_row['Name']} · Actual vs Optimal")
        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown(f"""
            <div style='background:#16213e;border:1px solid #e63946;
                        border-radius:10px;padding:16px'>
              <div style='color:#e63946;font-size:11px;letter-spacing:0.5px'>
                ACTUAL STRATEGY</div>
              <div style='color:white;font-weight:700;font-size:14px;margin:6px 0'>
                {drv_row['strategy']}</div>
              <div style='color:#aaaacc;font-size:12px'>
                {drv_row['n_stops']} pit stop(s) · Finished P{drv_row['Finish']}</div>
            </div>
            """, unsafe_allow_html=True)
        with ac2:
            st.markdown(f"""
            <div style='background:#16213e;border:1px solid #2a9d8f;
                        border-radius:10px;padding:16px'>
              <div style='color:#2a9d8f;font-size:11px;letter-spacing:0.5px'>
                MODEL OPTIMAL</div>
              <div style='color:white;font-weight:700;font-size:14px;margin:6px 0'>
                {opt['label']}</div>
              <div style='color:#aaaacc;font-size:12px'>
                Lowest predicted total race time</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:12px'>
      Bars = extra time vs the optimal strategy.
      <span style='color:#2a9d8f'>■</span> 1-stop ·
      <span style='color:#e9c46a'>■</span> 2-stop ·
      <span style='color:#888'>■</span> 0-stop.
      Red dashed line = selected driver's actual total lap time.
    </p>
    """, unsafe_allow_html=True)

    # Actual time from clean laps sum
    actual_time, actual_label = None, None
    if len(drv_actual) > 0:
        drv_laps = laps[laps['Driver'] == selected_driver].copy()
        drv_laps['LapTimeSeconds'] = drv_laps['LapTime'].dt.total_seconds()
        clean_drv = drv_laps[drv_laps['IsAccurate'] == True]
        if len(clean_drv) > 0:
            actual_time  = float(clean_drv['LapTimeSeconds'].sum())
            actual_label = drv_actual.iloc[0]['strategy']

    fig_bar = strategy_comparison_chart(
        opt_result['strategies'],
        actual_time  = actual_time,
        actual_label = actual_label,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander('📋  All drivers — actual strategies'):
        st.dataframe(
            actual_df[['Driver','Name','Team','Finish','n_stops','strategy']]
            .rename(columns={'n_stops':'Stops','strategy':'Strategy'}),
            use_container_width=True, hide_index=True,
        )

with tab2:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      For a fixed compound pair, this shows how sensitive total time
      is to the chosen pit lap.
      <span style='color:#57c785'>Green line</span> = optimal pit lap.
      A flat curve = flexible window. A sharp V = must pit on that exact lap.
    </p>
    """, unsafe_allow_html=True)

    if len(dry) >= 2:
        pw1, pw2 = st.columns(2)
        with pw1:
            c1 = st.selectbox('First stint',  dry, index=0, key='pw_c1')
        with pw2:
            c2 = st.selectbox('Second stint', dry,
                              index=min(1, len(dry)-1), key='pw_c2')

        fig_pw = pit_window_heatmap(opt_result['strategies'],
                                    c1, c2, total_laps)
        if fig_pw:
            st.plotly_chart(fig_pw, use_container_width=True)

            one_filt = opt_result['strategies'][
                (opt_result['strategies']['stops'] == 1) &
                (opt_result['strategies']['stint1_comp'] == c1) &
                (opt_result['strategies']['stint2_comp'] == c2)
            ]
            if len(one_filt) > 0:
                best_row   = one_filt.iloc[0]
                best_lap   = int(best_row['pit1_lap'])
                window_df  = one_filt[
                    one_filt['total_time'] <= best_row['total_time'] + 2.0
                ]
                w_start    = int(window_df['pit1_lap'].min())
                w_end      = int(window_df['pit1_lap'].max())
                st.markdown(f"""
                <div style='background:#16213e;border:1px solid #1e1e3a;
                            border-radius:10px;padding:16px;margin-top:8px'>
                  <div style='color:white;font-weight:600;margin-bottom:8px'>
                    📍 {c1.capitalize()} → {c2.capitalize()} pit window
                  </div>
                  <div style='color:#8888aa;font-size:13px;line-height:1.9'>
                    <b style='color:#57c785'>Optimal pit lap:</b> Lap {best_lap}<br>
                    <b style='color:#ccccdd'>Window within 2s of optimal:</b>
                    Laps {w_start}–{w_end} ({w_end - w_start} lap window)<br>
                    <b style='color:#ccccdd'>Pit loss assumed:</b> {pit_loss}s
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f'No 1-stop data for {c1.capitalize()} → {c2.capitalize()}.')
    else:
        st.info('Need at least 2 dry compounds in the race to show pit window.')

with tab3:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      All simulated strategies ranked by predicted total time.
    </p>
    """, unsafe_allow_html=True)

    stop_filter = st.multiselect('Filter by stops',
                                  options=[0, 1, 2], default=[1, 2],
                                  format_func=lambda x: f'{x} stop')

    filtered = opt_result['strategies'][
        opt_result['strategies']['stops'].isin(stop_filter)
    ].head(50).copy()

    best_t = filtered['total_time'].min()
    filtered['Δ vs Optimal'] = (filtered['total_time'] - best_t).apply(
        lambda x: '+{:.2f}s'.format(x) if x > 0.01 else '⭐ Optimal'
    )
    filtered['Total Time'] = filtered['total_time'].apply(
        lambda x: f"{int(x//60)}m {x%60:.1f}s"
    )

    st.dataframe(
        filtered[['stops','label','Total Time','Δ vs Optimal']]
        .rename(columns={'stops':'Stops','label':'Strategy'}),
        use_container_width=True, hide_index=True, height=500,
    )

    csv = filtered[['stops','label','Total Time','Δ vs Optimal']].to_csv(index=False)
    st.download_button('⬇️  Download CSV', csv,
                       f'strategies_{loaded_year}_{loaded_race}.csv',
                       'text/csv')
