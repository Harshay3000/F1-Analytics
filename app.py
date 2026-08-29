import streamlit as st
import pandas as pd
from utils.data_loader import (
    AVAILABLE_SEASONS, AVAILABLE_RACES,
    load_session, get_finishing_order
)

# ── Page definitions ──────────────────────────────────────────
home             = st.Page("pages/home.py",                 title="Home",             icon=None, default=True)
race_overview    = st.Page("pages/01_race_overview.py",     title="Race Overview",    icon=None)
tyre_strategy    = st.Page("pages/02_tyre_strategy.py",     title="Tyre Strategy",    icon=None)
driver_compare   = st.Page("pages/03_driver_comparison.py", title="Driver Comparison",icon=None)
circuit_map      = st.Page("pages/04_circuit_map.py",       title="Circuit Map",      icon=None)
gap_pace         = st.Page("pages/05_gap_and_pace.py",      title="Gap and Race Pace",icon=None)
driver_rating    = st.Page("pages/06_driver_rating.py",     title="Driver Rating",    icon=None)
tyre_deg         = st.Page("pages/07_tyre_degradation.py",  title="Tyre Degradation", icon=None)
pit_strategy     = st.Page("pages/08_pit_strategy.py",      title="Pit Strategy",     icon=None)
ai_narrator      = st.Page("pages/09_ai_narrator.py",       title="AI Narrator",      icon=None)

pg = st.navigation(
    {
        "": [home],
        "Analysis": [
            race_overview, tyre_strategy, driver_compare,
            circuit_map, gap_pace,
        ],
        "Machine Learning": [
            driver_rating, tyre_deg, pit_strategy,
        ],
        "AI": [ai_narrator],
    },
    position="hidden",   # hide from sidebar — we render manually below
)

st.set_page_config(
    page_title           = 'F1 Analytics',
    page_icon            = '🏎️',
    layout               = 'wide',
    initial_sidebar_state= 'expanded',
)

# ── Session state defaults ────────────────────────────────────
_DEFAULTS = {
    'session_loaded'  : False,
    'session_obj'     : None,
    'laps_df'         : None,
    'selected_year'   : 2025,
    'selected_race'   : 'Bahrain',
    'selected_session': 'R',
    'loaded_year'     : None,
    'loaded_race'     : None,
    'loaded_session'  : None,
}
for _key, _val in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

# ── Global CSS ────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background: #0f0f1a; }
  [data-testid="stSidebar"] {
    background: #16213e;
    border-right: 1px solid #1e1e3a;
  }
  [data-baseweb="select"] > div:focus-within {
    border-color: #e63946 !important;
  }
  [data-testid="metric-container"] {
    background: #16213e;
    border: 1px solid #1e1e3a;
    border-radius: 10px;
    padding: 16px;
  }
  hr { border-color: #1e1e3a; }
  .stTabs [data-baseweb="tab"] { background: transparent; color: #888899; }
  .stTabs [aria-selected="true"] {
    color: #e63946 !important;
    border-bottom: 2px solid #e63946;
  }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:

    # 1. Title
    st.markdown("""
    <div style='padding:4px 0 16px'>
      <span style='color:#e63946;font-size:22px;font-weight:800;
                   letter-spacing:-0.5px'>F1</span>
      <span style='color:white;font-size:18px;font-weight:600'>
        Analytics</span>
      <div style='color:#555577;font-size:11px;letter-spacing:1px;margin-top:2px'>
        POST-RACE PLATFORM
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 2. Race selector
    st.markdown("#### Select Race")

    selected_year = st.selectbox(
        'Season', options=AVAILABLE_SEASONS, index=0, key='selected_year'
    )
    selected_race = st.selectbox(
        'Grand Prix', options=AVAILABLE_RACES, index=0, key='selected_race'
    )
    selected_session = st.selectbox(
        'Session',
        options     = ['R', 'Q', 'FP1', 'FP2', 'FP3'],
        format_func = lambda x: {
            'R': 'Race', 'Q': 'Qualifying',
            'FP1': 'Practice 1', 'FP2': 'Practice 2', 'FP3': 'Practice 3',
        }.get(x, x),
        key='selected_session',
    )

    if st.button('Load Session', type='primary', use_container_width=True):
        st.session_state['session_loaded'] = False
        with st.spinner(f'Loading {selected_year} {selected_race}...'):
            try:
                session, laps = load_session(
                    selected_year, selected_race, selected_session
                )
                st.session_state['session_loaded']  = True
                st.session_state['session_obj']     = session
                st.session_state['laps_df']         = laps
                st.session_state['loaded_year']     = selected_year
                st.session_state['loaded_race']     = selected_race
                st.session_state['loaded_session']  = selected_session
                st.success('Session loaded ✓')
            except Exception as e:
                err = str(e)
                if 'No lap data' in err or 'misspelled' in err:
                    st.error(
                        f'No data found for {selected_year} {selected_race}. '
                        f'Try: 2023 · Bahrain · Race.'
                    )
                else:
                    st.error(f'Error: {type(e).__name__}: {e}')
                st.session_state['session_loaded'] = False

    if st.session_state.get('session_loaded'):
        try:
            sess       = st.session_state['session_obj']
            event_name = sess.event['EventName']
            event_date = sess.date.strftime('%d %b %Y')
        except Exception:
            event_name = st.session_state.get('loaded_race', '')
            event_date = str(st.session_state.get('loaded_year', ''))

        st.markdown(f"""
        <div style='background:#0f3460;border-radius:8px;padding:10px 14px;
                    margin-top:8px;border:1px solid #1e4a80'>
          <div style='color:#4a90d9;font-size:10px;letter-spacing:1px'>LOADED</div>
          <div style='color:white;font-weight:600;font-size:13px'>{event_name}</div>
          <div style='color:#8888aa;font-size:11px'>{event_date}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 3. Pages — rendered via st.page_link (fully clickable)
    st.markdown("""
    <div style='color:#555577;font-size:11px;letter-spacing:1px;
                margin-bottom:6px'>PAGES</div>
    """, unsafe_allow_html=True)

    page_links = [
        ("pages/home.py",                 "Home"),
        ("pages/01_race_overview.py",     "Race Overview"),
        ("pages/02_tyre_strategy.py",     "Tyre Strategy"),
        ("pages/03_driver_comparison.py", "Driver Comparison"),
        ("pages/04_circuit_map.py",       "Circuit Map"),
        ("pages/05_gap_and_pace.py",      "Gap and Race Pace"),
        ("pages/06_driver_rating.py",     "Driver Rating"),
        ("pages/07_tyre_degradation.py",  "Tyre Degradation"),
        ("pages/08_pit_strategy.py",      "Pit Strategy"),
        ("pages/09_ai_narrator.py",       "AI Narrator"),
    ]

    for path, label in page_links:
        st.page_link(path, label=label, icon=None)

    st.divider()
    st.markdown("""
    <div style='color:#333355;font-size:11px;line-height:1.6'>
      Data via FastF1 · Jolpica-F1
    </div>
    """, unsafe_allow_html=True)

# ── Run the current page ──────────────────────────────────────
pg.run()
