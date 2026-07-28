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
    session = fastf1.get_session(year, race, session_type)
    session.load(telemetry=True, laps=True, weather=False)
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
