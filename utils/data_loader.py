# ============================================================
# utils/data_loader.py
# ============================================================
# Central place for ALL data fetching.
#
# Key concept: @st.cache_data
#   Streamlit re-runs your entire script on every user
#   interaction. Without caching, it would re-download
#   FastF1 data on every button click (30s+ wait each time).
#   @st.cache_data stores the result in memory — next call
#   with the same arguments returns instantly.
# ============================================================

import fastf1
import pandas as pd
import streamlit as st
import os

# Enable FastF1's own file-level cache too (saves to disk)
os.makedirs('cache', exist_ok=True)
fastf1.Cache.enable_cache('cache')

# ── Season & race catalogue ───────────────────────────────────
# Hardcoded list so the sidebar dropdowns work without an API call.
# Update AVAILABLE_SEASONS each year.
AVAILABLE_SEASONS = [2025, 2024, 2023, 2022, 2021, 2020]

# Key races across the calendar (works for most seasons)
AVAILABLE_RACES = [
    'Bahrain', 'Saudi Arabia', 'Australia', 'Japan',
    'China', 'Miami', 'Emilia Romagna', 'Monaco',
    'Canada', 'Spain', 'Austria', 'British',
    'Hungary', 'Belgian', 'Dutch', 'Italian',
    'Azerbaijan', 'Singapore', 'United States',
    'Mexico City', 'São Paulo', 'Las Vegas', 'Qatar',
    'Abu Dhabi',
]

# ── Compound colors (used across multiple charts) ─────────────
COMPOUND_COLORS = {
    'SOFT'        : '#e63946',
    'MEDIUM'      : '#f4d03f',
    'HARD'        : '#e8e8e8',
    'INTERMEDIATE': '#57c785',
    'WET'         : '#4a90d9',
    'UNKNOWN'     : '#888888',
}

# ── Team colors (2023/2024 approximate) ──────────────────────
TEAM_COLORS = {
    'Red Bull Racing'   : '#3671C6',
    'Ferrari'           : '#E8002D',
    'Mercedes'          : '#27F4D2',
    'McLaren'           : '#FF8000',
    'Aston Martin'      : '#229971',
    'Alpine'            : '#FF87BC',
    'Williams'          : '#64C4FF',
    'RB'                : '#6692FF',
    'Haas F1 Team'      : '#B6BABD',
    'Kick Sauber'       : '#52E252',
}


# ── Core data loader ──────────────────────────────────────────
def load_session(year: int, race: str, session_type: str = 'R'):
    """
    Load a FastF1 session and return (session, laps).

    NOT cached at the Streamlit level — FastF1 session objects
    contain locks and file handles that aren't safely serializable
    by st.cache_data. FastF1's own disk cache (the 'cache/' folder)
    handles the performance side: second load is instant from disk.

    Parameters
    ----------
    year         : int  — season year (e.g. 2023)
    race         : str  — race name (e.g. 'Bahrain')
    session_type : str  — 'R' race, 'Q' qualifying, 'FP1' etc.
    """
    fastf1.set_log_level('WARNING')   # suppress verbose output
    session = fastf1.get_session(year, race, session_type)
    session.load(telemetry=True, laps=True, weather=False)

    # Verify data actually loaded — raises clear error if empty
    if session.laps is None or len(session.laps) == 0:
        raise ValueError(
            f"No lap data returned for {year} {race} {session_type}. "
            f"This race may not be available yet or the session "
            f"type may be incorrect."
        )

    laps = session.laps.copy()
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
    return session, laps


def get_driver_list(year: int, race: str):
    """Return list of (abbreviation, full name, team) tuples."""
    session, laps = load_session(year, race)
    drivers = []
    for abbr in session.drivers:
        info = session.get_driver(abbr)
        drivers.append({
            'abbr'    : abbr,
            'name'    : info['FullName'],
            'lastname': info['LastName'],
            'team'    : info['TeamName'],
        })
    return sorted(drivers, key=lambda d: d['abbr'])


def get_driver_telemetry(year: int, race: str,
                          driver: str, session_type: str = 'R'):
    """
    Get telemetry for a driver's fastest lap.
    Returns telemetry DataFrame with Distance column added.
    """
    session, laps = load_session(year, race, session_type)
    driver_laps   = laps.pick_driver(driver)

    if len(driver_laps) == 0:
        return None, None

    fastest   = driver_laps.pick_fastest()
    telemetry = fastest.get_telemetry().add_distance()
    return fastest, telemetry


def get_stints(year: int, race: str):
    """
    Derive tyre stints for all drivers.
    Returns DataFrame: Driver, Stint, Compound, StartLap, EndLap, LapCount
    """
    session, laps = load_session(year, race)
    stint_rows    = []

    for driver in laps['Driver'].unique():
        driver_laps = (
            laps[laps['Driver'] == driver]
            .sort_values('LapNumber')
            .reset_index(drop=True)
        )
        current_compound = None
        stint_num        = 0
        start_lap        = None

        for _, lap in driver_laps.iterrows():
            compound = str(lap['Compound']).upper() \
                       if pd.notna(lap['Compound']) else 'UNKNOWN'

            if compound != current_compound:
                if current_compound is not None:
                    stint_rows.append({
                        'Driver'  : driver,
                        'Stint'   : stint_num,
                        'Compound': current_compound,
                        'StartLap': start_lap,
                        'EndLap'  : int(lap['LapNumber']) - 1,
                        'LapCount': int(lap['LapNumber']) - start_lap,
                    })
                stint_num       += 1
                current_compound = compound
                start_lap        = int(lap['LapNumber'])

        # Close last stint
        if current_compound is not None:
            last_lap = int(driver_laps['LapNumber'].max())
            stint_rows.append({
                'Driver'  : driver,
                'Stint'   : stint_num,
                'Compound': current_compound,
                'StartLap': start_lap,
                'EndLap'  : last_lap,
                'LapCount': last_lap - start_lap + 1,
            })

    return pd.DataFrame(stint_rows)


def get_finishing_order(year: int, race: str):
    """Return drivers sorted by final race position."""
    session, laps = load_session(year, race)
    order = (
        laps.groupby('Driver')['Position']
        .last()
        .dropna()
        .sort_values()
        .reset_index()
    )
    result = []
    for _, row in order.iterrows():
        info = session.get_driver(row['Driver'])
        result.append({
            'position': int(row['Position']),
            'abbr'    : row['Driver'],
            'name'    : info['FullName'],
            'lastname': info['LastName'],
            'team'    : info['TeamName'],
        })
    return result


# ── Functions that work from already-loaded data ──────────────
# These take a laps DataFrame + session object directly instead
# of re-fetching via FastF1. Use these in pages so that charts
# always reflect exactly the session the user loaded.

def derive_stints(laps, session):
    """
    Derive tyre stints from an already-loaded laps DataFrame.
    Returns DataFrame: Driver, Stint, Compound, StartLap, EndLap, LapCount
    """
    stint_rows = []

    for driver in laps['Driver'].unique():
        driver_laps = (
            laps[laps['Driver'] == driver]
            .sort_values('LapNumber')
            .reset_index(drop=True)
        )
        current_compound = None
        stint_num        = 0
        start_lap        = None

        for _, lap in driver_laps.iterrows():
            compound = str(lap['Compound']).upper() \
                       if pd.notna(lap['Compound']) else 'UNKNOWN'

            if compound != current_compound:
                if current_compound is not None:
                    stint_rows.append({
                        'Driver'  : driver,
                        'Stint'   : stint_num,
                        'Compound': current_compound,
                        'StartLap': start_lap,
                        'EndLap'  : int(lap['LapNumber']) - 1,
                        'LapCount': int(lap['LapNumber']) - start_lap,
                    })
                stint_num       += 1
                current_compound = compound
                start_lap        = int(lap['LapNumber'])

        if current_compound is not None:
            last_lap = int(driver_laps['LapNumber'].max())
            stint_rows.append({
                'Driver'  : driver,
                'Stint'   : stint_num,
                'Compound': current_compound,
                'StartLap': start_lap,
                'EndLap'  : last_lap,
                'LapCount': last_lap - start_lap + 1,
            })

    return pd.DataFrame(stint_rows)


def derive_finishing_order(laps, session):
    """
    Derive finishing order from an already-loaded laps DataFrame.
    Returns list of dicts sorted by finishing position.
    """
    order = (
        laps.groupby('Driver')['Position']
        .last()
        .dropna()
        .sort_values()
        .reset_index()
    )
    result = []
    for _, row in order.iterrows():
        try:
            info = session.get_driver(row['Driver'])
            result.append({
                'position': int(row['Position']),
                'abbr'    : row['Driver'],
                'name'    : info['FullName'],
                'lastname': info['LastName'],
                'team'    : info['TeamName'],
            })
        except Exception:
            result.append({
                'position': int(row['Position']),
                'abbr'    : row['Driver'],
                'name'    : row['Driver'],
                'lastname': row['Driver'],
                'team'    : 'Unknown',
            })
    return result


def derive_driver_list(session):
    """
    Return driver list from an already-loaded session object.
    """
    drivers = []
    for abbr in session.drivers:
        try:
            info = session.get_driver(abbr)
            drivers.append({
                'abbr'    : abbr,
                'name'    : info['FullName'],
                'lastname': info['LastName'],
                'team'    : info['TeamName'],
            })
        except Exception:
            drivers.append({
                'abbr'    : abbr,
                'name'    : abbr,
                'lastname': abbr,
                'team'    : 'Unknown',
            })
    return sorted(drivers, key=lambda d: d['abbr'])


# ── Driver Performance Rating Engine ─────────────────────────
# Computes a composite driver rating for a single race using
# 6 measurable signals. Each signal is normalized to 0-100
# so they can be fairly combined into one score.
#
# The 6 signals and what they measure:
#
#  1. FINISHING SCORE      — final race position (higher = more points)
#  2. POSITIONS GAINED     — grid position vs finish (reward overtaking)
#  3. RACE PACE SCORE      — median clean lap time vs field median
#  4. CONSISTENCY SCORE    — std deviation of clean laps (lower = better)
#  5. QUALIFYING SCORE     — qualifying position vs field
#  6. TEAMMATE DELTA       — race pace vs direct teammate (same car)
#
# Why normalize?
#   Raw values aren't comparable — lap times are in seconds (90-100),
#   positions are 1-20, std dev is 0.5-3. Normalizing everything to
#   0-100 lets us add them fairly with configurable weights.
#
# Why include teammate delta?
#   It's the purest driver comparison in F1 — same car, same track,
#   same conditions. A driver who beats a strong teammate by 0.3s
#   deserves more credit than one who beats a weak teammate by 0.1s.

def compute_driver_ratings(
    race_session,
    race_laps: pd.DataFrame,
    quali_session=None,
    weights: dict = None,
) -> pd.DataFrame:
    """
    Compute a composite performance rating for every driver in a race.

    Parameters
    ----------
    race_session  : FastF1 Session object (race)
    race_laps     : DataFrame from load_session (race laps)
    quali_session : FastF1 Session object (qualifying) — optional
                    If provided, adds qualifying score to the rating.
    weights       : dict of signal weights. Defaults to equal weighting.
                    Keys: 'finish', 'positions_gained', 'pace',
                          'consistency', 'quali', 'teammate'

    Returns
    -------
    DataFrame with columns:
        Driver, Name, Team, Finish, GridPos,
        raw_* columns (original values),
        score_* columns (0-100 normalized),
        Rating (weighted composite 0-100)
    """
    import numpy as np

    if weights is None:
        weights = {
            'finish'          : 0.25,
            'positions_gained': 0.15,
            'pace'            : 0.25,
            'consistency'     : 0.15,
            'quali'           : 0.10,
            'teammate'        : 0.10,
        }

    laps = race_laps.copy()
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

    # Clean laps — accurate only, remove top 5% slowest
    clean = laps[laps['IsAccurate'] == True].copy()
    p95   = clean['LapTimeSeconds'].quantile(0.95)
    clean = clean[clean['LapTimeSeconds'] <= p95]

    drivers = list(race_laps['Driver'].unique())
    rows    = []

    # ── Qualifying positions ──────────────────────────────────
    quali_positions = {}
    if quali_session is not None:
        try:
            qlaps = quali_session.laps
            for d in drivers:
                try:
                    best = qlaps.pick_driver(d).pick_fastest()
                    quali_positions[d] = best['Position'] \
                                         if pd.notna(best.get('Position')) \
                                         else None
                except Exception:
                    quali_positions[d] = None
        except Exception:
            pass

    # ── Grid positions from race laps ─────────────────────────
    # Lap 1 position approximates grid position
    grid_positions = {}
    lap1 = laps[laps['LapNumber'] == 1][['Driver', 'Position']]
    for _, row in lap1.iterrows():
        if pd.notna(row['Position']):
            grid_positions[row['Driver']] = int(row['Position'])

    # ── Finishing positions ───────────────────────────────────
    finish_positions = {}
    fin = laps.groupby('Driver')['Position'].last()
    for d, pos in fin.items():
        if pd.notna(pos):
            finish_positions[d] = int(pos)

    # ── Per-driver pace & consistency ─────────────────────────
    pace_map        = {}
    consistency_map = {}
    for d in drivers:
        dlaps = clean[clean['Driver'] == d]['LapTimeSeconds']
        if len(dlaps) >= 3:
            pace_map[d]        = dlaps.median()
            consistency_map[d] = dlaps.std()

    field_median_pace = np.median(list(pace_map.values())) \
                        if pace_map else None

    # ── Teammate mapping ──────────────────────────────────────
    # Group drivers by team, then compare within each pair
    team_map = {}
    for d in drivers:
        try:
            info = race_session.get_driver(d)
            team = info['TeamName']
            team_map.setdefault(team, []).append(d)
        except Exception:
            pass

    teammate_delta = {}   # positive = faster than teammate
    for team, members in team_map.items():
        if len(members) == 2:
            d1, d2 = members
            p1 = pace_map.get(d1)
            p2 = pace_map.get(d2)
            if p1 is not None and p2 is not None:
                # Negative delta means d1 is faster (lower lap time)
                teammate_delta[d1] = p2 - p1   # + means d1 faster
                teammate_delta[d2] = p1 - p2

    # ── Build raw rows ────────────────────────────────────────
    n_drivers = len(drivers)
    for d in drivers:
        try:
            info = race_session.get_driver(d)
            name = info['FullName']
            team = info['TeamName']
        except Exception:
            name = d
            team = 'Unknown'

        finish  = finish_positions.get(d)
        grid    = grid_positions.get(d)
        pace    = pace_map.get(d)
        consist = consistency_map.get(d)
        quali   = quali_positions.get(d)
        t_delta = teammate_delta.get(d)

        rows.append({
            'Driver'           : d,
            'Name'             : name,
            'Team'             : team,
            'Finish'           : finish,
            'GridPos'          : grid,
            'raw_pace'         : pace,
            'raw_consistency'  : consist,
            'raw_quali'        : quali,
            'raw_teammate_delta': t_delta,
        })

    df = pd.DataFrame(rows)

    # ── Normalize each signal to 0-100 ────────────────────────
    # Helper: min-max normalize, with direction control.
    # invert=True means lower raw value → higher score
    # (e.g. faster lap time = higher pace score)
    def normalize(series: pd.Series, invert: bool = False) -> pd.Series:
        s   = pd.to_numeric(series, errors='coerce')
        mn  = s.min()
        mx  = s.max()
        if mx == mn:
            return pd.Series([50.0] * len(s), index=s.index)
        norm = (s - mn) / (mx - mn) * 100
        return (100 - norm) if invert else norm

    # Finish score: P1=100, last=0
    df['score_finish'] = normalize(df['Finish'], invert=True)

    # Positions gained: grid - finish (positive = gained places)
    df['positions_gained'] = (
        pd.to_numeric(df['GridPos'],  errors='coerce') -
        pd.to_numeric(df['Finish'],   errors='coerce')
    )
    df['score_positions_gained'] = normalize(df['positions_gained'],
                                             invert=False)

    # Pace score: lower median lap time = higher score
    df['score_pace'] = normalize(df['raw_pace'], invert=True)

    # Consistency score: lower std dev = higher score
    df['score_consistency'] = normalize(df['raw_consistency'], invert=True)

    # Quali score: lower quali position = higher score
    df['score_quali'] = normalize(df['raw_quali'], invert=True) \
                        if df['raw_quali'].notna().any() \
                        else pd.Series([50.0] * len(df), index=df.index)

    # Teammate delta: larger positive delta = higher score
    df['score_teammate'] = normalize(df['raw_teammate_delta'], invert=False) \
                           if df['raw_teammate_delta'].notna().any() \
                           else pd.Series([50.0] * len(df), index=df.index)

    # ── Weighted composite rating ─────────────────────────────
    df['Rating'] = (
        df['score_finish']           * weights['finish']           +
        df['score_positions_gained'] * weights['positions_gained'] +
        df['score_pace']             * weights['pace']             +
        df['score_consistency']      * weights['consistency']      +
        df['score_quali']            * weights['quali']            +
        df['score_teammate']         * weights['teammate']
    ).round(1)

    return df.sort_values('Rating', ascending=False).reset_index(drop=True)


# ── Tyre Degradation ML Engine ────────────────────────────────
#
# What we're modelling:
#   For each tyre stint, lap time increases as the tyre wears.
#   We want to quantify HOW FAST it degrades (deg rate) and
#   PREDICT what lap time will be at any tyre age.
#
# Features used by the model:
#   - TyreLife       : laps on current set (main predictor)
#   - Compound_enc   : encoded compound (SOFT=0, MEDIUM=1, HARD=2)
#   - TrackTemp      : hotter track = faster degradation (if available)
#   - FuelLoad_proxy : lap number proxy for fuel burn (lighter = faster)
#
# Why Random Forest + linear deg rate?
#   Random Forest captures the non-linear relationship (deg
#   accelerates on worn tyres) but is hard to interpret.
#   We also fit a simple linear regression per stint to extract
#   a human-readable "degradation rate" (seconds per lap).
#   Both outputs are shown: the RF curve for accuracy, the
#   linear rate for interpretability.
#
# Model evaluation:
#   We use cross-validation within each compound group and
#   report MAE (Mean Absolute Error) in milliseconds so it's
#   intuitive — "the model is accurate to within X ms per lap".

def build_tyre_degradation_model(laps: pd.DataFrame, session):
    """
    Build a tyre degradation model from race lap data.

    Returns a dict with:
      'model'        : fitted RandomForestRegressor
      'features'     : list of feature column names
      'training_df'  : cleaned DataFrame used for training
      'compound_map' : compound → encoded int mapping
      'mae'          : mean absolute error in seconds
      'r2'           : R² score (1.0 = perfect fit)
      'deg_rates'    : dict of compound → linear deg rate (s/lap)
      'stint_data'   : per-stint summary DataFrame
    """
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import mean_absolute_error, r2_score

    laps = laps.copy()
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

    # ── Step 1: Clean the data ────────────────────────────────
    # We only want accurate laps on known compounds.
    # Remove pit-in/out laps and safety car laps.
    clean = laps[
        (laps['IsAccurate'] == True) &
        (laps['Compound'].notna()) &
        (laps['TyreLife'].notna()) &
        (laps['LapTimeSeconds'] > 0)
    ].copy()

    # Remove outlier lap times (top/bottom 2.5%)
    lo = clean['LapTimeSeconds'].quantile(0.025)
    hi = clean['LapTimeSeconds'].quantile(0.975)
    clean = clean[(clean['LapTimeSeconds'] >= lo) &
                  (clean['LapTimeSeconds'] <= hi)]

    if len(clean) < 20:
        return None   # not enough data to model

    # ── Step 2: Encode categorical features ───────────────────
    compound_map = {'SOFT': 0, 'MEDIUM': 1, 'HARD': 2,
                    'INTERMEDIATE': 3, 'WET': 4}
    clean['Compound_enc'] = (
        clean['Compound'].str.upper()
        .map(compound_map)
        .fillna(1)
        .astype(int)
    )

    # Fuel load proxy: higher lap number = less fuel = slightly faster
    # We model this as a negative offset
    clean['FuelProxy'] = clean['LapNumber'].astype(float)

    # ── Step 3: Feature matrix ────────────────────────────────
    features = ['TyreLife', 'Compound_enc', 'FuelProxy']
    clean['TyreLife'] = clean['TyreLife'].astype(float)

    X = clean[features].values
    y = clean['LapTimeSeconds'].values

    # ── Step 4: Train Random Forest ───────────────────────────
    model = RandomForestRegressor(
        n_estimators = 80,    # reduced from 200 — good accuracy, 3x faster
        max_depth    = 6,
        min_samples_leaf=3,
        random_state = 42,
        n_jobs       = -1,
    )
    model.fit(X, y)

    # Cross-validated MAE (5-fold)
    cv_scores = cross_val_score(
        model, X, y,
        scoring = 'neg_mean_absolute_error',
        cv      = min(5, len(clean) // 10),
    )
    mae = float(-cv_scores.mean())
    r2  = float(r2_score(y, model.predict(X)))

    # ── Step 5: Linear degradation rate per compound ─────────
    # Fit y = a*TyreLife + b for each compound separately.
    # The slope 'a' = degradation rate in seconds per lap.
    deg_rates = {}
    for compound in clean['Compound'].str.upper().unique():
        subset = clean[clean['Compound'].str.upper() == compound]
        if len(subset) < 5:
            continue
        lr = LinearRegression()
        lr.fit(subset[['TyreLife']].values,
               subset['LapTimeSeconds'].values)
        deg_rates[compound] = float(lr.coef_[0])

    # ── Step 6: Per-stint summary ─────────────────────────────
    stint_rows = []
    for driver in clean['Driver'].unique():
        dlaps = clean[clean['Driver'] == driver] \
                .sort_values('LapNumber').copy()
        prev_compound = None
        stint_num     = 0
        stint_start   = None

        for _, lap in dlaps.iterrows():
            compound = str(lap['Compound']).upper()
            if compound != prev_compound:
                if prev_compound is not None:
                    pass  # closed above
                prev_compound = compound
                stint_num    += 1
                stint_start   = lap['LapNumber']

            stint_rows.append({
                'Driver'   : driver,
                'Stint'    : stint_num,
                'Compound' : compound,
                'TyreLife' : lap['TyreLife'],
                'LapTime'  : lap['LapTimeSeconds'],
                'LapNumber': lap['LapNumber'],
            })

    stint_df = pd.DataFrame(stint_rows)

    return {
        'model'       : model,
        'features'    : features,
        'training_df' : clean,
        'compound_map': compound_map,
        'mae'         : mae,
        'r2'          : r2,
        'deg_rates'   : deg_rates,
        'stint_data'  : stint_df,
    }


def predict_lap_times(model_result: dict,
                       compound: str,
                       tyre_life_range: range,
                       avg_lap_number: float = 30.0) -> pd.DataFrame:
    """
    Predict lap times for a given compound across a range of tyre ages.

    Parameters
    ----------
    model_result    : output of build_tyre_degradation_model()
    compound        : tyre compound string e.g. 'SOFT'
    tyre_life_range : range of tyre ages to predict for
    avg_lap_number  : fuel proxy (use midpoint of race)

    Returns
    -------
    DataFrame with columns: TyreLife, PredictedTime, Compound
    """
    import numpy as np

    model        = model_result['model']
    compound_map = model_result['compound_map']
    compound_enc = compound_map.get(compound.upper(), 1)

    tyre_lives = list(tyre_life_range)
    X_pred = np.array([
        [tl, compound_enc, avg_lap_number]
        for tl in tyre_lives
    ])

    preds = model.predict(X_pred)

    return pd.DataFrame({
        'TyreLife'     : tyre_lives,
        'PredictedTime': preds,
        'Compound'     : compound,
    })


# ── Pit Stop Strategy Optimizer ───────────────────────────────
#
# How it works:
#   Given a race length (total laps) and a tyre degradation model,
#   we simulate every possible 1-stop and 2-stop strategy by
#   trying every combination of pit lap(s) and compounds.
#
#   For each strategy we calculate the TOTAL RACE TIME:
#     = sum of all predicted lap times across all stints
#     + pit stop time loss (typically 20-22 seconds)
#
#   The strategy with the lowest total race time is "optimal".
#   We then compare it to what the driver actually did.
#
# Why is this useful?
#   In reality teams use much more complex models (Monte Carlo
#   simulations with safety car probabilities, traffic models,
#   weather forecasts etc.). But this simplified version captures
#   the core trade-off: pit earlier to get fresher tyres faster
#   vs pit later to minimize the number of slow pit laps.
#
# Key simplification:
#   We assume all laps at the same tyre age take the same time
#   regardless of who is around you (no traffic modelling).
#   This is why real F1 strategies sometimes differ from "optimal".

def optimize_pit_strategy(
    model_result: dict,
    total_laps: int,
    pit_loss_seconds: float = 22.0,
    compounds_available: list = None,
    max_stops: int = 2,
) -> dict:
    """
    Find the optimal pit stop strategy by brute-force simulation.

    Parameters
    ----------
    model_result         : output of build_tyre_degradation_model()
    total_laps           : total race laps
    pit_loss_seconds     : time lost per pit stop (default 22s)
    compounds_available  : list of compounds to consider
                           (defaults to all compounds in race)
    max_stops            : 1 or 2 stop strategies to evaluate

    Returns
    -------
    dict with keys:
      'strategies'    : DataFrame of all strategies ranked by total time
      'optimal'       : best strategy dict
      'one_stop'      : best 1-stop strategy
      'two_stop'      : best 2-stop strategy (if max_stops >= 2)
    """
    import numpy as np
    from itertools import product as iproduct

    model        = model_result['model']
    compound_map = model_result['compound_map']

    if compounds_available is None:
        compounds_available = list(
            model_result['training_df']['Compound']
            .str.upper().unique()
        )
        # Only dry compounds for strategy
        compounds_available = [c for c in compounds_available
                               if c in ['SOFT', 'MEDIUM', 'HARD']]

    if not compounds_available:
        return None

    # ── Pre-compute ALL lap times in one batch call ──────────
    # Calling model.predict() once per lap is extremely slow
    # (~500k calls for 2-stop). Instead we predict every possible
    # (compound, tyre_age) in a single matrix call, then use a
    # dictionary lookup — 100-200x faster.
    avg_lap      = total_laps / 2   # fuel proxy midpoint
    max_age      = total_laps

    all_X = []
    lookup_keys = []
    for compound in compounds_available:
        enc = compound_map.get(compound, 1)
        for tyre_age in range(1, max_age + 1):
            all_X.append([float(tyre_age), float(enc), float(avg_lap)])
            lookup_keys.append((compound, tyre_age))

    all_X     = np.array(all_X)
    all_preds = model.predict(all_X)

    # lap_time[(compound, tyre_age)] = predicted lap time (seconds)
    lap_time = {k: float(v) for k, v in zip(lookup_keys, all_preds)}

    # Cumulative sum per compound: cum[(compound, n)] = sum of laps 1..n
    cum = {}
    for compound in compounds_available:
        running = 0.0
        for age in range(1, max_age + 1):
            running += lap_time[(compound, age)]
            cum[(compound, age)] = running
        cum[(compound, 0)] = 0.0

    def stint_time(compound: str, start_lap: int,
                   stint_length: int) -> float:
        """O(1) cumulative stint time from pre-computed lookup."""
        end_age = stint_length          # fresh tyre starts at age 1
        return cum.get((compound, end_age), 0.0)

    strategies = []

    # ── 0-stop (no pit) ───────────────────────────────────────
    for c1 in compounds_available:
        t = stint_time(c1, 1, total_laps)
        strategies.append({
            'stops'       : 0,
            'stint1_comp' : c1,
            'stint1_laps' : total_laps,
            'pit1_lap'    : None,
            'stint2_comp' : None,
            'stint2_laps' : None,
            'pit2_lap'    : None,
            'stint3_comp' : None,
            'stint3_laps' : None,
            'pit_loss'    : 0.0,
            'total_time'  : t,
            'label'       : f'0-stop: {c1.capitalize()}',
        })

    # ── 1-stop ────────────────────────────────────────────────
    # Try every pit lap from lap 5 to total_laps-5
    # Try every combination of compound 1 → compound 2
    for pit_lap in range(5, total_laps - 4):
        s1_len = pit_lap - 1
        s2_len = total_laps - pit_lap

        for c1, c2 in iproduct(compounds_available,
                                compounds_available):
            t1 = stint_time(c1, 1,       s1_len)
            t2 = stint_time(c2, pit_lap, s2_len)
            total = t1 + t2 + pit_loss_seconds

            strategies.append({
                'stops'       : 1,
                'stint1_comp' : c1,
                'stint1_laps' : s1_len,
                'pit1_lap'    : pit_lap,
                'stint2_comp' : c2,
                'stint2_laps' : s2_len,
                'pit2_lap'    : None,
                'stint3_comp' : None,
                'stint3_laps' : None,
                'pit_loss'    : pit_loss_seconds,
                'total_time'  : total,
                'label'       : (f'1-stop: {c1.capitalize()} '
                                 f'→ {c2.capitalize()} '
                                 f'(pit L{pit_lap})'),
            })

    # ── 2-stop ────────────────────────────────────────────────
    if max_stops >= 2:
        # To keep computation fast, sample pit laps every 2 laps
        pit_laps = range(5, total_laps - 9, 2)
        for pit1 in pit_laps:
            for pit2 in range(pit1 + 5, total_laps - 4, 2):
                s1_len = pit1 - 1
                s2_len = pit2 - pit1
                s3_len = total_laps - pit2

                for c1, c2, c3 in iproduct(compounds_available,
                                            compounds_available,
                                            compounds_available):
                    t1 = stint_time(c1, 1,    s1_len)
                    t2 = stint_time(c2, pit1, s2_len)
                    t3 = stint_time(c3, pit2, s3_len)
                    total = t1 + t2 + t3 + pit_loss_seconds * 2

                    strategies.append({
                        'stops'       : 2,
                        'stint1_comp' : c1,
                        'stint1_laps' : s1_len,
                        'pit1_lap'    : pit1,
                        'stint2_comp' : c2,
                        'stint2_laps' : s2_len,
                        'pit2_lap'    : pit2,
                        'stint3_comp' : c3,
                        'stint3_laps' : s3_len,
                        'pit_loss'    : pit_loss_seconds * 2,
                        'total_time'  : total,
                        'label'       : (
                            f'2-stop: {c1.capitalize()} → '
                            f'{c2.capitalize()} → '
                            f'{c3.capitalize()} '
                            f'(L{pit1}, L{pit2})'
                        ),
                    })

    strat_df = pd.DataFrame(strategies)
    strat_df  = strat_df.sort_values('total_time').reset_index(drop=True)

    one_stop = strat_df[strat_df['stops'] == 1].iloc[0].to_dict() \
               if len(strat_df[strat_df['stops'] == 1]) > 0 else None
    two_stop = strat_df[strat_df['stops'] == 2].iloc[0].to_dict() \
               if len(strat_df[strat_df['stops'] == 2]) > 0 else None
    optimal  = strat_df.iloc[0].to_dict()

    return {
        'strategies': strat_df,
        'optimal'   : optimal,
        'one_stop'  : one_stop,
        'two_stop'  : two_stop,
    }


def get_actual_strategies(laps: pd.DataFrame, session) -> pd.DataFrame:
    """
    Extract what each driver actually did — their pit laps,
    compounds, and stint lengths — for comparison vs optimal.
    """
    laps  = laps.copy()
    rows  = []

    for driver in laps['Driver'].unique():
        dlaps = (laps[laps['Driver'] == driver]
                 .sort_values('LapNumber').copy())
        if len(dlaps) == 0:
            continue

        # Find pit stop laps
        pit_laps = dlaps[dlaps['PitInTime'].notna()]['LapNumber'] \
                   .tolist()

        # Build stints
        stints        = []
        prev_compound = None
        stint_start   = 1

        for _, lap in dlaps.iterrows():
            compound = str(lap['Compound']).upper() \
                       if pd.notna(lap['Compound']) else 'UNKNOWN'
            if compound != prev_compound and prev_compound is not None:
                stints.append({
                    'compound': prev_compound,
                    'start'   : stint_start,
                    'end'     : int(lap['LapNumber']) - 1,
                    'laps'    : int(lap['LapNumber']) - stint_start,
                })
                stint_start = int(lap['LapNumber'])
            prev_compound = compound

        # Close final stint
        if prev_compound:
            last_lap = int(dlaps['LapNumber'].max())
            stints.append({
                'compound': prev_compound,
                'start'   : stint_start,
                'end'     : last_lap,
                'laps'    : last_lap - stint_start + 1,
            })

        try:
            info = session.get_driver(driver)
            name = info['FullName']
            team = info['TeamName']
        except Exception:
            name, team = driver, 'Unknown'

        finish = laps[laps['Driver'] == driver]['Position'] \
                 .dropna().iloc[-1] if len(
            laps[laps['Driver'] == driver]['Position'].dropna()
        ) > 0 else None

        rows.append({
            'Driver'   : driver,
            'Name'     : name,
            'Team'     : team,
            'Finish'   : int(finish) if finish is not None else None,
            'n_stops'  : len(pit_laps),
            'pit_laps' : pit_laps,
            'stints'   : stints,
            'strategy' : ' → '.join(
                [f"{s['compound'].capitalize()} ({s['laps']}L)"
                 for s in stints]
            ),
        })

    return pd.DataFrame(rows).sort_values('Finish')


# ── Race Narrator Data Preparation ───────────────────────────
# Extracts the key facts from race data and structures them
# into a clean dict that gets passed to the Claude API.
# We never send raw DataFrames to the API — too large and
# unstructured. Instead we extract only the meaningful numbers.

def build_race_summary_dict(laps: pd.DataFrame,
                             session,
                             deg_result: dict = None) -> dict:
    """
    Extract key race facts into a structured dict for the narrator.

    Returns a dict with:
      - race_info       : event name, year, circuit, date
      - results         : top 10 finishers with team
      - pit_stops       : who pitted when and on what compound
      - fastest_lap     : driver, time, lap number
      - positions_gained: top 3 overtakers
      - tyre_strategies : each driver's stint summary
      - deg_rates       : degradation rates per compound (if available)
      - key_moments     : lap-by-lap lead changes
    """
    summary = {}

    # ── Race info ─────────────────────────────────────────────
    summary['race_info'] = {
        'name'    : session.event.get('EventName', 'Unknown GP'),
        'year'    : int(session.event.year),
        'circuit' : session.event.get('Location', 'Unknown'),
        'date'    : session.date.strftime('%d %B %Y'),
        'total_laps': int(laps['LapNumber'].max()),
    }

    # ── Top 10 results ────────────────────────────────────────
    finish_order = (
        laps.groupby('Driver')['Position']
        .last().dropna().sort_values().reset_index()
    )
    results = []
    for _, row in finish_order.head(10).iterrows():
        try:
            info = session.get_driver(row['Driver'])
            results.append({
                'position': int(row['Position']),
                'driver'  : row['Driver'],
                'name'    : info['FullName'],
                'team'    : info['TeamName'],
            })
        except Exception:
            pass
    summary['results'] = results

    # ── Fastest lap ───────────────────────────────────────────
    laps_copy = laps.copy()
    laps_copy['LapTimeSeconds'] = laps_copy['LapTime'].dt.total_seconds()
    clean = laps_copy[laps_copy['IsAccurate'] == True].copy()

    if len(clean) > 0:
        idx_fl = clean['LapTimeSeconds'].idxmin()
        fl_row = clean.loc[idx_fl]
        fl_t   = fl_row['LapTimeSeconds']
        mins   = int(fl_t // 60)
        secs   = fl_t % 60
        try:
            fl_info = session.get_driver(fl_row['Driver'])
            fl_name = fl_info['FullName']
        except Exception:
            fl_name = fl_row['Driver']

        summary['fastest_lap'] = {
            'driver'  : fl_row['Driver'],
            'name'    : fl_name,
            'lap'     : int(fl_row['LapNumber']),
            'time'    : f"{mins}:{secs:06.3f}",
        }

    # ── Pit stop summary ──────────────────────────────────────
    pit_rows = laps[laps['PitInTime'].notna()].copy()
    pit_summary = []
    for _, row in pit_rows.iterrows():
        try:
            info = session.get_driver(row['Driver'])
            name = info['FullName']
        except Exception:
            name = row['Driver']
        pit_summary.append({
            'driver'  : row['Driver'],
            'name'    : name,
            'lap'     : int(row['LapNumber']),
            'compound': str(row['Compound']).capitalize()
                        if pd.notna(row['Compound']) else 'Unknown',
        })
    summary['pit_stops'] = sorted(pit_summary, key=lambda x: x['lap'])

    # ── Positions gained/lost ─────────────────────────────────
    lap1 = laps[laps['LapNumber'] == 1][['Driver', 'Position']] \
           .rename(columns={'Position': 'Start'})
    last = (laps.groupby('Driver')['Position'].last()
            .reset_index().rename(columns={'Position': 'End'}))
    merged = lap1.merge(last, on='Driver').dropna()
    merged['Start'] = pd.to_numeric(merged['Start'], errors='coerce')
    merged['End']   = pd.to_numeric(merged['End'],   errors='coerce')
    merged          = merged.dropna()
    merged['Delta'] = (merged['Start'] - merged['End']).astype(int)

    pos_gained = []
    for _, row in merged.sort_values('Delta', ascending=False).head(5).iterrows():
        try:
            info = session.get_driver(row['Driver'])
            name = info['FullName']
        except Exception:
            name = row['Driver']
        pos_gained.append({
            'driver': row['Driver'],
            'name'  : name,
            'gained': int(row['Delta']),
            'start' : int(row['Start']),
            'end'   : int(row['End']),
        })
    summary['positions_gained'] = pos_gained

    # ── Tyre strategies ───────────────────────────────────────
    stints_list = []
    for driver in laps['Driver'].unique():
        dlaps = laps[laps['Driver'] == driver].sort_values('LapNumber')
        prev, start_lap, stint_num = None, 1, 0
        stints = []
        for _, lap in dlaps.iterrows():
            comp = str(lap['Compound']).upper() \
                   if pd.notna(lap['Compound']) else 'UNKNOWN'
            if comp != prev:
                if prev:
                    stints.append(f"{prev}({int(lap['LapNumber'])-start_lap}L)")
                prev      = comp
                start_lap = int(lap['LapNumber'])
        if prev:
            stints.append(f"{prev}({int(dlaps['LapNumber'].max())-start_lap+1}L)")

        try:
            name = session.get_driver(driver)['FullName']
        except Exception:
            name = driver

        fin_pos = laps[laps['Driver'] == driver]['Position'] \
                  .dropna().iloc[-1] if len(
            laps[laps['Driver'] == driver]['Position'].dropna()
        ) > 0 else None

        stints_list.append({
            'driver'  : driver,
            'name'    : name,
            'finish'  : int(fin_pos) if fin_pos is not None else None,
            'strategy': ' → '.join(stints),
        })
    summary['tyre_strategies'] = sorted(
        stints_list, key=lambda x: x['finish'] or 99
    )

    # ── Lead changes ──────────────────────────────────────────
    p1_laps     = laps[laps['Position'] == 1][['LapNumber', 'Driver']] \
                  .sort_values('LapNumber')
    lead_changes = []
    prev_leader  = None
    for _, row in p1_laps.iterrows():
        if row['Driver'] != prev_leader:
            try:
                name = session.get_driver(row['Driver'])['FullName']
            except Exception:
                name = row['Driver']
            lead_changes.append({
                'lap'   : int(row['LapNumber']),
                'driver': row['Driver'],
                'name'  : name,
            })
            prev_leader = row['Driver']
    summary['lead_changes'] = lead_changes

    # ── Degradation rates ─────────────────────────────────────
    if deg_result and 'deg_rates' in deg_result:
        summary['deg_rates'] = {
            k: round(v * 1000, 1)   # convert to ms/lap
            for k, v in deg_result['deg_rates'].items()
        }

    return summary


# ── Race Summary Dict ─────────────────────────────────────────
# Extracts structured race facts into a clean dictionary.
# This is the "context" sent to the AI narrator.
# Keeps the narrator page simple — it just calls this function
# and passes the result to the prompt builder.
