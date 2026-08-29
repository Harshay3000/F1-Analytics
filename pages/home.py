import streamlit as st
import pandas as pd
from utils.data_loader import get_finishing_order

# ── Home page content ─────────────────────────────────────────
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
    <h2 style='color:white;font-size:1.3rem;font-weight:600;margin-bottom:20px'>
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
