# ============================================================
# app.py — Main entry point
# ============================================================
# This is the file Streamlit runs: `streamlit run app.py`
#
# What this file does:
#   1. Configures the page (title, layout, theme)
#   2. Renders the sidebar with race/session selectors
#   3. Stores the user's selections in st.session_state
#      so every page can read them without asking again
#   4. Shows a home page with race summary stats
#
# How Streamlit multi-page apps work:
#   - app.py = home page + shared sidebar
#   - Any .py file inside pages/ = an extra page
#   - Streamlit auto-adds them to the sidebar nav
# ============================================================

import streamlit as st
import pandas as pd
from utils.data_loader import (
    AVAILABLE_SEASONS, AVAILABLE_RACES,
    load_session, get_finishing_order
)

# ── Page config — must be the FIRST Streamlit call ───────────
st.set_page_config(
    page_title = 'F1 Analytics',
    page_icon  = '🏎️',
    layout     = 'wide',
    initial_sidebar_state='expanded',
)

# ── Session state defaults ────────────────────────────────────
# Initialize all keys with safe defaults on first run.
# This runs every time ANY page loads (because app.py is always
# executed as the shared entry point), so pages can safely read
# these keys without KeyError even before a session is loaded.
_DEFAULTS = {
    'session_loaded'  : False,
    'session_obj'     : None,
    'laps_df'         : None,
    'selected_year'   : 2025,
    'selected_race'   : 'Bahrain',
    'selected_session': 'R',
    # Confirmed snapshot — set ONLY when Load Session is clicked.
    # None means "user has never clicked Load" — pages check for
    # this and show a warning instead of fetching wrong data.
    'loaded_year'     : None,
    'loaded_race'     : None,
    'loaded_session'  : None,
}
for _key, _val in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

# ── Global CSS ────────────────────────────────────────────────
# Injects custom styles that apply to every page in the app.
# We override Streamlit's default white background with our
# dark racing theme.
st.markdown("""
<style>
  /* Dark background for the whole app */
  .stApp { background: #0f0f1a; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #16213e;
    border-right: 1px solid #1e1e3a;
  }

  /* Main content area */
  [data-testid="stAppViewContainer"] > .main {
    background: #0f0f1a;
  }

  /* Red accent on selectbox focus */
  [data-baseweb="select"] > div:focus-within {
    border-color: #e63946 !important;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #16213e;
    border: 1px solid #1e1e3a;
    border-radius: 10px;
    padding: 16px;
  }

  /* Divider color */
  hr { border-color: #1e1e3a; }

  /* Tab styling */
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #888899;
  }
  .stTabs [aria-selected="true"] {
    color: #e63946 !important;
    border-bottom: 2px solid #e63946;
  }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 4px 0 20px'>
      <span style='color:#e63946;font-size:22px;font-weight:800;
                   letter-spacing:-0.5px'>F1</span>
      <span style='color:white;font-size:18px;font-weight:600'>
        Analytics</span>
      <div style='color:#555577;font-size:11px;
                  letter-spacing:1px;margin-top:2px'>
        POST-RACE PLATFORM
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Race selector ─────────────────────────────────────────
    st.markdown("#### Select Race")

    selected_year = st.selectbox(
        'Season',
        options  = AVAILABLE_SEASONS,
        index    = 0,
        key      = 'selected_year',
    )

    selected_race = st.selectbox(
        'Grand Prix',
        options  = AVAILABLE_RACES,
        index    = 0,
        key      = 'selected_race',
    )

    selected_session = st.selectbox(
        'Session',
        options  = ['R', 'Q', 'FP1', 'FP2', 'FP3'],
        format_func=lambda x: {
            'R'  : '🏁 Race',
            'Q'  : '⏱ Qualifying',
            'FP1': '🔧 Practice 1',
            'FP2': '🔧 Practice 2',
            'FP3': '🔧 Practice 3',
        }.get(x, x),
        key='selected_session',
    )

    st.divider()

    # ── Load button ───────────────────────────────────────────
    # We don't load data automatically — user clicks Load so they
    # can change all three dropdowns before triggering the download.
    if st.button('Load Session', type='primary', use_container_width=True):
        st.session_state['session_loaded'] = False
        with st.spinner(f'Loading {selected_year} {selected_race}...'):
            try:
                session, laps = load_session(
                    selected_year, selected_race, selected_session
                )
                # Store in session state so all pages can access it.
                # We save a confirmed snapshot (loaded_year/race/session)
                # separately from the selectbox keys — this guarantees
                # all pages use the race that was actually loaded,
                # not whatever the dropdowns currently show.
                st.session_state['session_loaded']  = True
                st.session_state['session_obj']     = session
                st.session_state['laps_df']         = laps
                st.session_state['loaded_year']     = selected_year
                st.session_state['loaded_race']     = selected_race
                st.session_state['loaded_session']  = selected_session
                st.success('Session loaded ✓')
            except Exception as e:
                err = str(e)
                if 'No lap data' in err:
                    st.error(f'No data available for {selected_year} '
                             f'{selected_race} {selected_session}. '
                             f'Try a different race or session type.')
                elif 'not been loaded' in err:
                    st.error('FastF1 failed to load the session. '
                             'Check your internet connection and try again.')
                elif '404' in err or 'not found' in err.lower():
                    st.error(f'{selected_year} {selected_race} may not exist '
                             f'or is not available yet in FastF1.')
                else:
                    st.error(f'Could not load session: {e}')
                st.session_state['session_loaded'] = False

    # Show current status
    if st.session_state.get('session_loaded'):
        try:
            sess       = st.session_state['session_obj']
            event_name = st.session_state.get('loaded_race', 'Unknown')
            event_date = ''
            try:
                event_name = sess.event['EventName']
                event_date = sess.date.strftime('%d %b %Y')
            except Exception:
                event_date = str(st.session_state.get('loaded_year', ''))
            st.markdown(f"""
            <div style='background:#0f3460;border-radius:8px;
                        padding:10px 14px;margin-top:8px;
                        border:1px solid #1e4a80'>
              <div style='color:#4a90d9;font-size:10px;
                          letter-spacing:1px'>LOADED</div>
              <div style='color:white;font-weight:600;font-size:13px'>
                {event_name}</div>
              <div style='color:#8888aa;font-size:11px'>
                {event_date}</div>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            st.success('Session loaded ✓')

    st.divider()
    st.markdown("""
    <div style='color:#333355;font-size:11px;line-height:1.6'>
      Data via FastF1 · Jolpica-F1<br>
      Phase 2 — Interactive Dashboard
    </div>
    """, unsafe_allow_html=True)


# ── Home page ─────────────────────────────────────────────────
st.markdown("""
<h1 style='color:white;font-size:2rem;font-weight:800;
           margin-bottom:4px'>
  🏎️ F1 Post-Race Analytics
</h1>
<p style='color:#555577;margin-bottom:32px'>
  Select a race in the sidebar and click Load Session to begin.
</p>
""", unsafe_allow_html=True)

if not st.session_state.get('session_loaded'):
    # Show instructions when no session is loaded
    col1, col2, col3 = st.columns(3)
    for col, icon, title, desc in [
        (col1, '📊', 'Race Overview',
         'Lap times & position changes across the full race'),
        (col2, '🔴', 'Tyre Strategy',
         'See every driver\'s stint lengths and compound choices'),
        (col3, '⚡', 'Speed Trace',
         'Compare telemetry between any two drivers'),
    ]:
        with col:
            st.markdown(f"""
            <div style='background:#16213e;border:1px solid #1e1e3a;
                        border-radius:12px;padding:24px;height:130px'>
              <div style='font-size:28px'>{icon}</div>
              <div style='color:white;font-weight:600;
                          margin:8px 0 4px'>{title}</div>
              <div style='color:#555577;font-size:13px'>{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👈  Choose a season, Grand Prix, and session in the sidebar, then click **Load Session**.")

else:
    # ── Race summary stats ─────────────────────────────────────
    session = st.session_state['session_obj']
    laps    = st.session_state['laps_df']

    st.markdown(f"""
    <h2 style='color:white;font-size:1.4rem;font-weight:700;
               margin-bottom:20px'>
      {session.event['EventName']} {session.event.year}
      <span style='color:#555577;font-size:1rem;font-weight:400'>
        · {session.date.strftime('%d %B %Y')}
      </span>
    </h2>
    """, unsafe_allow_html=True)

    # ── Key metrics row ────────────────────────────────────────
    total_laps   = int(laps['LapNumber'].max())
    n_drivers    = laps['Driver'].nunique()
    total_pit    = laps['PitInTime'].notna().sum()
    fastest_time = laps['LapTime'].min()
    fastest_drv  = laps.loc[laps['LapTime'].idxmin(), 'Driver']

    if pd.notna(fastest_time):
        t     = fastest_time.total_seconds()
        mins  = int(t // 60)
        secs  = t % 60
        fl_str = f"{mins}:{secs:06.3f}"
    else:
        fl_str = 'N/A'

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Total Laps',       total_laps)
    col2.metric('Drivers',          n_drivers)
    col3.metric('Total Pit Stops',  total_pit)
    col4.metric('Fastest Lap',      f"{fl_str}  ({fastest_drv})")

    st.divider()

    # ── Finishing order table ──────────────────────────────────
    st.markdown("#### 🏁 Race Result")
    try:
        order = get_finishing_order(
            selected_year, selected_race
        )
        result_df = pd.DataFrame(order)[
            ['position', 'abbr', 'name', 'team']
        ].rename(columns={
            'position': 'Pos',
            'abbr'    : 'Driver',
            'name'    : 'Full Name',
            'team'    : 'Team',
        })
        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True,
            height=min(600, len(result_df) * 36 + 38),
        )
    except Exception as e:
        st.warning(f"Could not load finishing order: {e}")

    st.markdown("""
    <div style='color:#333355;font-size:12px;margin-top:16px'>
      Navigate to the pages in the sidebar to explore charts →
    </div>
    """, unsafe_allow_html=True)
