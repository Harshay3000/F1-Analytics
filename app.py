import streamlit as st
import pandas as pd
from utils.data_loader import (
    AVAILABLE_SEASONS, AVAILABLE_RACES,
    load_session, get_finishing_order
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

  /* Move the built-in page nav to the bottom of the sidebar
     by pushing it down with a large top margin. This keeps
     the links functional while appearing below our content. */
  [data-testid="stSidebarNav"] {
    margin-top: 32px;
    padding-top: 8px;
    border-top: 1px solid #1e1e3a;
  }

  /* Style the nav links to match our dark theme */
  [data-testid="stSidebarNav"] a {
    color: #aaaacc !important;
    font-size: 13px !important;
  }
  [data-testid="stSidebarNav"] a:hover {
    color: white !important;
    background: rgba(255,255,255,0.05) !important;
    border-radius: 6px;
  }
  [data-testid="stSidebarNav"] a span {
    color: #aaaacc !important;
  }
  /* Active page highlight */
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(230,57,70,0.12) !important;
    border-radius: 6px;
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: #e63946 !important;
    font-weight: 600 !important;
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

    # 1. Title
    st.markdown("""
    <div style='padding:4px 0 16px'>
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
                        f'Try a different race. Known working: 2023 · Bahrain · Race.'
                    )
                else:
                    st.error(f'Error: {type(e).__name__}: {e}')
                st.session_state['session_loaded'] = False

    # Loaded status card
    if st.session_state.get('session_loaded'):
        try:
            sess       = st.session_state['session_obj']
            event_name = sess.event['EventName']
            event_date = sess.date.strftime('%d %b %Y')
        except Exception:
            event_name = st.session_state.get('loaded_race', '')
            event_date = str(st.session_state.get('loaded_year', ''))

        st.markdown(f"""
        <div style='background:#0f3460;border-radius:8px;
                    padding:10px 14px;margin-top:8px;
                    border:1px solid #1e4a80'>
          <div style='color:#4a90d9;font-size:10px;letter-spacing:1px'>
            LOADED</div>
          <div style='color:white;font-weight:600;font-size:13px'>
            {event_name}</div>
          <div style='color:#8888aa;font-size:11px'>{event_date}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 3. Pages label — the actual nav links are rendered automatically
    #    by Streamlit below this label (pushed down via CSS margin-top)
    st.markdown("""
    <div style='color:#555577;font-size:11px;letter-spacing:1px'>
      PAGES
    </div>
    """, unsafe_allow_html=True)

    # Spacer so the label sits just above the nav list
    st.markdown("<div style='margin-bottom:4px'></div>",
                unsafe_allow_html=True)

    # Footer pinned at the very bottom
    st.markdown("""
    <div style='position:fixed;bottom:16px;left:0;width:var(--sidebar-width,280px);
                padding:0 16px;box-sizing:border-box'>
      <div style='color:#333355;font-size:11px;line-height:1.6;
                  border-top:1px solid #1e1e3a;padding-top:10px'>
        Data via FastF1 · Jolpica-F1
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Home page ─────────────────────────────────────────────────
st.markdown("""
<h1 style='color:white;font-size:2rem;font-weight:700;
           margin-bottom:4px;letter-spacing:-0.5px'>
  F1 Post-Race Analytics Platform
</h1>
<p style='color:#555577;margin-bottom:32px;font-size:15px'>
  Select a race in the sidebar and click Load Session to begin.
</p>
""", unsafe_allow_html=True)

if not st.session_state.get('session_loaded'):
    col1, col2, col3 = st.columns(3)
    for col, title, desc in [
        (col1, 'Race Overview',
         'Lap time comparison and position changes across the full race distance.'),
        (col2, 'Tyre Strategy',
         "Stint timeline for every driver showing compound choices and pit stop laps."),
        (col3, 'Driver Comparison',
         'Head-to-head telemetry — speed, throttle and brake traces aligned by distance.'),
    ]:
        with col:
            st.markdown(f"""
            <div style='background:#16213e;border:1px solid #1e1e3a;
                        border-radius:10px;padding:24px;min-height:140px;
                        box-sizing:border-box'>
              <div style='color:white;font-weight:600;font-size:15px;
                          margin-bottom:8px'>{title}</div>
              <div style='color:#555577;font-size:13px;line-height:1.6'>
                {desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Choose a season, Grand Prix, and session in the sidebar, "
            "then click **Load Session**.")

else:
    session = st.session_state['session_obj']
    laps    = st.session_state['laps_df']

    try:
        event_title = f"{session.event['EventName']} {session.event.year}"
        event_date  = session.date.strftime('%d %B %Y')
    except Exception:
        event_title = (f"{st.session_state['loaded_year']} "
                       f"{st.session_state['loaded_race']}")
        event_date  = ''

    st.markdown(f"""
    <h2 style='color:white;font-size:1.3rem;font-weight:600;
               margin-bottom:20px'>
      {event_title}
      <span style='color:#555577;font-size:0.95rem;font-weight:400'>
        &nbsp;·&nbsp; {event_date}
      </span>
    </h2>
    """, unsafe_allow_html=True)

    total_laps  = int(laps['LapNumber'].max())
    n_drivers   = laps['Driver'].nunique()
    total_pit   = laps['PitInTime'].notna().sum()
    fastest_lap = laps['LapTime'].min()
    fastest_drv = laps.loc[laps['LapTime'].idxmin(), 'Driver']

    fl_str = 'N/A'
    if pd.notna(fastest_lap):
        t      = fastest_lap.total_seconds()
        fl_str = f"{int(t // 60)}:{t % 60:06.3f}"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Total Laps',      total_laps)
    col2.metric('Drivers',         n_drivers)
    col3.metric('Total Pit Stops', total_pit)
    col4.metric('Fastest Lap',     f"{fl_str}  ({fastest_drv})")

    st.divider()
    st.markdown("#### Race Result")

    try:
        order = get_finishing_order(
            st.session_state['loaded_year'],
            st.session_state['loaded_race'],
        )
        result_df = pd.DataFrame(order)[
            ['position', 'abbr', 'name', 'team']
        ].rename(columns={
            'position': 'Pos', 'abbr': 'Driver',
            'name': 'Full Name', 'team': 'Team',
        })
        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True,
            height=min(600, len(result_df) * 36 + 38),
        )
    except Exception as e:
        st.warning(f'Could not load finishing order: {e}')
