# tyre_degradation.py — Tyre Degradation Predictor
# What this page does:
#
#   Trains a Random Forest regression model on real lap time
#   and tyre age data to model and predict tyre degradation.
#
#   Three tabs:
#     Tab 1 — Degradation curves (actual vs predicted)
#     Tab 2 — Degradation rates per compound (linear slope)
#     Tab 3 — Driver comparison on same compound
#
#   Key ML concepts shown:
#     - Feature engineering (tyre age, compound encoding, fuel proxy)
#     - Random Forest regression for non-linear curve fitting
#     - Linear regression for interpretable degradation rate
#     - Cross-validated MAE for model evaluation
#     - Prediction over a synthetic input range
#
# What is tyre degradation?
#   As a tyre wears, the rubber thins and grip reduces.
#   This shows up as increasing lap times per lap on the same set.
#   Quantifying this rate is critical for pit stop strategy —
#   if your tyres degrade at +0.08s/lap vs opponent's +0.05s/lap,
#   you need to pit earlier or you'll lose time on track.
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
from utils.data_loader import (build_tyre_degradation_model,
                                predict_lap_times,
                                COMPOUND_COLORS)
from utils.chart_helpers import (tyre_deg_chart, deg_rate_chart,
                                  driver_deg_comparison)

st.set_page_config(page_title='Tyre Degradation · F1', layout='wide')

# ── Guards ────────────────────────────────────────────────────
if not st.session_state.get('session_loaded'):
    st.warning('No session loaded. Go to the **Home** page and '
               'click **Load Session**.')
    st.stop()

if not st.session_state.get('loaded_race'):
    st.warning('No session loaded. Go to the **Home** page and '
               'click **Load Session**.')
    st.stop()

session     = st.session_state['session_obj']
laps        = st.session_state['laps_df']
loaded_year = st.session_state['loaded_year']
loaded_race = st.session_state['loaded_race']
event_name  = session.event.get('EventName', loaded_race)

# ── Header ────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='color:white;font-size:1.6rem;font-weight:800;
           margin-bottom:4px'>Tyre Degradation Predictor</h1>
<p style='color:#555577;margin-bottom:4px'>
  A Random Forest model trained on real race lap times to predict
  how quickly each tyre compound degrades lap by lap.
</p>
<div style='display:inline-block;background:#0f3460;
            border:1px solid #1e4a80;border-radius:6px;
            padding:5px 14px;margin-bottom:20px;font-size:13px'>
  📍 Showing: <b style='color:white'>{loaded_year} {event_name}</b>
  &nbsp;·&nbsp;
  <span style='color:#555577'>Not right? Go to Home and reload.</span>
</div>
""", unsafe_allow_html=True)

# ── ML explainer ──────────────────────────────────────────────
with st.expander('🤖  How the ML model works', expanded=False):
    st.markdown("""
    #### Model: Random Forest Regressor

    **What we're predicting:** Lap time (seconds) given tyre age,
    compound type, and approximate fuel load.

    **Features used:**

    | Feature | Description | Why |
    |---|---|---|
    | `TyreLife` | Laps on current tyre set | Main predictor of degradation |
    | `Compound_enc` | SOFT=0, MEDIUM=1, HARD=2 | Each compound degrades differently |
    | `FuelProxy` | Lap number in the race | More fuel early = slower; less fuel late = faster |

    **Why Random Forest?**
    Tyre degradation isn't perfectly linear — it often accelerates
    on very worn tyres (the "cliff"). A Random Forest captures this
    non-linear behaviour better than simple linear regression.

    **Why also show a linear rate?**
    The RF curve is accurate but hard to interpret.
    A linear slope gives a human-readable number:
    *"Soft tyres degrade at +0.08 seconds per lap"* — that's
    something an F1 engineer can immediately act on.

    **Model evaluation:**
    We use 5-fold cross-validation and report **MAE**
    (Mean Absolute Error) in milliseconds. If MAE = 120ms,
    the model's lap time predictions are accurate to within
    0.12 seconds on unseen laps.
    """)

st.divider()

# ── Train the model ───────────────────────────────────────────
with st.spinner('Training Random Forest model on race data...'):
    result = build_tyre_degradation_model(laps, session)

if result is None:
    st.error('Not enough clean lap data to train the model. '
             'Try a different race — some wet races have too few '
             'accurate dry laps.')
    st.stop()

# ── Model performance metrics ─────────────────────────────────
st.markdown("#### Model performance")
col1, col2, col3, col4 = st.columns(4)

mae_ms    = result['mae'] * 1000
r2        = result['r2']
n_samples = len(result['training_df'])
n_features= len(result['features'])

col1.metric('MAE',         f"{mae_ms:.0f} ms",
            help='Mean Absolute Error — average prediction error per lap')
col2.metric('R² Score',    f"{r2:.3f}",
            help='1.0 = perfect fit. Above 0.85 = good model.')
col3.metric('Training laps', f"{n_samples:,}",
            help='Clean accurate laps used to train the model')
col4.metric('Features',    str(n_features),
            help='TyreLife, Compound encoding, Fuel proxy')

# Colour the R² metric to indicate model quality
if r2 >= 0.85:
    quality_msg = "✅ Good fit — model captures degradation well"
    quality_col = "#57c785"
elif r2 >= 0.65:
    quality_msg = "⚠️ Moderate fit — some degradation patterns not captured"
    quality_col = "#f4d03f"
else:
    quality_msg = "❌ Weak fit — limited data or very inconsistent lap times"
    quality_col = "#e63946"

st.markdown(f"""
<div style='background:#16213e;border:1px solid #1e1e3a;
            border-radius:8px;padding:10px 16px;
            margin:12px 0 24px;font-size:13px'>
  <span style='color:{quality_col}'>{quality_msg}</span>
  &nbsp;·&nbsp;
  <span style='color:#555577'>
    MAE of {mae_ms:.0f}ms means predictions are accurate to
    ±{mae_ms/1000:.3f}s per lap on average.
  </span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Generate predictions for all compounds ────────────────────
compounds_in_race = (result['training_df']['Compound']
                     .str.upper().unique().tolist())
max_tyre_life     = int(result['training_df']['TyreLife'].max())
avg_lap           = float(result['training_df']['LapNumber'].median())

predictions = {}
for compound in compounds_in_race:
    predictions[compound] = predict_lap_times(
        result,
        compound,
        range(1, max_tyre_life + 1),
        avg_lap,
    )

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    '📈  Degradation Curves',
    '📊  Degradation Rates',
    '👥  Driver Comparison',
])

with tab1:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      <b style='color:#ccccdd'>Dots</b> = actual lap times from the race
      (coloured by compound). &nbsp;
      <b style='color:#ccccdd'>Solid lines</b> = Random Forest model
      prediction. &nbsp;
      Rising lines = tyre degradation. The steeper the rise,
      the faster the compound wears out.
    </p>
    """, unsafe_allow_html=True)

    # Compound filter
    selected_compounds = st.multiselect(
        'Show compounds',
        options = compounds_in_race,
        default = compounds_in_race,
    )

    filtered_stints = result['stint_data'][
        result['stint_data']['Compound'].isin(selected_compounds)
    ]
    filtered_preds  = {c: v for c, v in predictions.items()
                       if c in selected_compounds}

    fig_deg = tyre_deg_chart(filtered_stints, filtered_preds, session)
    st.plotly_chart(fig_deg, use_container_width=True)

    # ── Prediction tool ───────────────────────────────────────
    st.markdown("#### 🔮 Predict a specific lap time")
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:12px'>
      Enter a tyre age to get the model's predicted lap time
      for any compound.
    </p>
    """, unsafe_allow_html=True)

    pred_col1, pred_col2 = st.columns(2)
    with pred_col1:
        pred_compound = st.selectbox('Compound', compounds_in_race)
    with pred_col2:
        pred_age = st.slider(
            'Tyre age (laps)', 1, max_tyre_life, 10
        )

    pred_df = predict_lap_times(
        result, pred_compound, range(pred_age, pred_age + 1), avg_lap
    )
    pred_time = pred_df['PredictedTime'].iloc[0]
    mins      = int(pred_time // 60)
    secs      = pred_time % 60

    st.markdown(f"""
    <div style='background:#0f3460;border:1px solid #1e4a80;
                border-radius:10px;padding:20px;
                display:inline-block;margin-top:8px'>
      <div style='color:#555577;font-size:12px;
                  letter-spacing:0.5px'>PREDICTED LAP TIME</div>
      <div style='color:white;font-size:2rem;font-weight:800;
                  margin:4px 0'>
        {mins}:{secs:06.3f}
      </div>
      <div style='color:#8888aa;font-size:12px'>
        {pred_compound.capitalize()} · Lap age {pred_age}
        · Fuel proxy lap {avg_lap:.0f}
      </div>
    </div>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      Linear degradation rate = how many seconds per lap
      the tyre loses as it wears. Derived by fitting a straight
      line through each compound's lap times vs tyre age.
      <br>
      <b style='color:#ccccdd'>Higher bar = faster degradation
      = need to pit sooner.</b>
    </p>
    """, unsafe_allow_html=True)

    if result['deg_rates']:
        fig_rates = deg_rate_chart(result['deg_rates'])
        st.plotly_chart(fig_rates, use_container_width=True)

        # ── Rates table ───────────────────────────────────────
        st.markdown("#### Degradation rate summary")
        rate_rows = []
        for compound, rate in sorted(result['deg_rates'].items(),
                                     key=lambda x: x[1],
                                     reverse=True):
            rate_rows.append({
                'Compound'              : compound.capitalize(),
                'Rate (s/lap)'          : f"{rate:.4f}",
                'Rate (ms/lap)'         : f"{rate*1000:.1f}",
                '10-lap loss (s)'       : f"{rate*10:.3f}",
                '20-lap loss (s)'       : f"{rate*20:.3f}",
                'Interpretation'        :
                    'Fast wear — short stints' if rate > 0.08
                    else 'Moderate wear' if rate > 0.04
                    else 'Durable — can run long stints',
            })

        st.dataframe(
            pd.DataFrame(rate_rows),
            use_container_width=True,
            hide_index=True,
        )

        # ── Strategy implication ──────────────────────────────
        if len(result['deg_rates']) >= 2:
            sorted_rates = sorted(result['deg_rates'].items(),
                                  key=lambda x: x[1])
            most_durable = sorted_rates[0][0].capitalize()
            fastest_deg  = sorted_rates[-1][0].capitalize()
            rate_diff    = sorted_rates[-1][1] - sorted_rates[0][1]

            st.markdown(f"""
            <div style='background:#16213e;border:1px solid #1e1e3a;
                        border-radius:10px;padding:20px;margin-top:16px'>
              <div style='color:white;font-weight:600;margin-bottom:8px'>
                📋 Strategy implication
              </div>
              <div style='color:#8888aa;font-size:13px;line-height:1.8'>
                <b style='color:#ccccdd'>{most_durable}</b>
                is the most durable compound at this circuit
                ({sorted_rates[0][1]*1000:.1f} ms/lap degradation).
                <br>
                <b style='color:#ccccdd'>{fastest_deg}</b>
                degrades {rate_diff*1000:.1f} ms/lap faster —
                meaning over a 20-lap stint it costs an extra
                <b style='color:#e63946'>
                  {rate_diff*20:.2f}s</b> vs {most_durable}.
                <br>
                Teams on {fastest_deg} need to pit
                proportionally earlier to avoid losing net time.
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info('Not enough data to compute linear degradation rates.')

with tab3:
    st.markdown("""
    <p style='color:#8888aa;font-size:13px;margin-bottom:16px'>
      Compare how different drivers degraded the same compound.
      Steeper slope = faster degradation = harder on tyres.
      Same car teammates on the same compound reveal driving style
      differences in tyre management.
    </p>
    """, unsafe_allow_html=True)

    col_c, col_d = st.columns([1, 2])

    with col_c:
        compare_compound = st.selectbox(
            'Compound to compare',
            options = compounds_in_race,
            index   = 0,
            key     = 'compare_compound',
        )

    # Drivers who ran this compound
    compound_drivers = (
        result['stint_data'][
            result['stint_data']['Compound'] == compare_compound
        ]['Driver'].unique().tolist()
    )

    with col_d:
        selected_drivers_deg = st.multiselect(
            'Select drivers',
            options = compound_drivers,
            default = compound_drivers[:6],
            key     = 'drivers_deg',
        )

    if len(selected_drivers_deg) < 2:
        st.info('Select at least 2 drivers to compare.')
    else:
        fig_drv = driver_deg_comparison(
            result['stint_data'],
            selected_drivers_deg,
            compare_compound,
            session,
        )
        st.plotly_chart(fig_drv, use_container_width=True)

        # ── Per-driver degradation rates ──────────────────────
        with st.expander('📋  Per-driver degradation rates'):
            from sklearn.linear_model import LinearRegression

            drv_rate_rows = []
            for driver in selected_drivers_deg:
                subset = result['stint_data'][
                    (result['stint_data']['Driver'] == driver) &
                    (result['stint_data']['Compound'] == compare_compound)
                ]
                if len(subset) < 3:
                    continue

                lr = LinearRegression()
                lr.fit(subset[['TyreLife']].values,
                       subset['LapTime'].values)
                rate = lr.coef_[0]

                try:
                    info = session.get_driver(driver)
                    name = info['FullName']
                    team = info['TeamName']
                except Exception:
                    name, team = driver, '—'

                drv_rate_rows.append({
                    'Driver'       : driver,
                    'Name'         : name,
                    'Team'         : team,
                    'Deg Rate s/lap': f"{rate:.4f}",
                    'Deg Rate ms/lap': f"{rate*1000:.1f}",
                    '10-lap loss'  : f"{rate*10:.3f}s",
                    'Tyre Management':
                        '🟢 Gentle' if rate < 0.04
                        else '🟡 Average' if rate < 0.08
                        else '🔴 Aggressive',
                })

            if drv_rate_rows:
                drv_rate_df = pd.DataFrame(drv_rate_rows) \
                              .sort_values('Deg Rate s/lap')
                st.dataframe(drv_rate_df, use_container_width=True,
                             hide_index=True)
