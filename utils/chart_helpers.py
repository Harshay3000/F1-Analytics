# ============================================================
# utils/chart_helpers.py
# ============================================================
# Reusable Plotly chart functions.
#
# Why Plotly instead of Matplotlib?
#   Plotly charts are interactive by default — hover tooltips,
#   zoom, pan, hide/show traces by clicking the legend.
#   In a Streamlit app, st.plotly_chart() renders them natively.
# ============================================================

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from utils.data_loader import COMPOUND_COLORS, TEAM_COLORS

# ── Shared dark theme applied to every chart ──────────────────
DARK_LAYOUT = dict(
    paper_bgcolor='#0f0f1a',
    plot_bgcolor ='#16213e',
    font         =dict(color='#ccccdd', family='Inter, system-ui, sans-serif'),
    legend       =dict(bgcolor='rgba(15,15,26,0.7)',
                       bordercolor='#1e1e3a', borderwidth=1),
    margin       =dict(l=60, r=30, t=60, b=60),
    hoverlabel   =dict(bgcolor='#1a1a2e', bordercolor='#333355',
                       font=dict(color='white', size=12)),
)

# Default axis styling applied after every update_layout call
DARK_AXES = dict(gridcolor='#1e1e3a', zerolinecolor='#1e1e3a',
                 tickfont=dict(size=11))

ACCENT = '#e63946'   # F1 red


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply the shared dark theme to any Plotly figure."""
    fig.update_layout(**DARK_LAYOUT)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 1: Lap Time Line Chart ──────────────────────────────
def lap_time_chart(laps: pd.DataFrame, session,
                   highlight_drivers: list = None) -> go.Figure:
    """
    Multi-driver lap time line chart.
    Highlighted drivers get team colors + visible labels.
    Others are rendered as dim gray lines.

    Parameters
    ----------
    laps              : all laps DataFrame from load_session()
    session           : FastF1 session object
    highlight_drivers : list of driver abbreviations to color
    """
    laps = laps.copy()
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

    # Filter out outlier laps (safety car, first lap, pit-out laps)
    clean = laps[laps['IsAccurate'] == True].copy()
    median_t = clean['LapTimeSeconds'].median()
    clean = clean[
        (clean['LapTimeSeconds'] > median_t * 0.90) &
        (clean['LapTimeSeconds'] < median_t * 1.15)
    ]

    if highlight_drivers is None:
        # Default: highlight top 5 finishers
        highlight_drivers = (
            laps.groupby('Driver')['Position']
            .last().sort_values().head(5).index.tolist()
        )

    fig = go.Figure()

    for driver in laps['Driver'].unique():
        driver_laps = clean[clean['Driver'] == driver] \
                      .sort_values('LapNumber')
        if len(driver_laps) == 0:
            continue

        info      = session.get_driver(driver)
        team      = info['TeamName']
        full_name = info['FullName']
        color     = TEAM_COLORS.get(team, '#888888')

        is_highlighted = driver in highlight_drivers

        # Pit stop laps for hover annotation
        pit_laps = laps[
            (laps['Driver'] == driver) &
            (laps['PitInTime'].notna())
        ]['LapNumber'].tolist()

        custom_data = [
            [full_name, team,
             f"{'🔧 PIT' if ln in pit_laps else ''}"]
            for ln in driver_laps['LapNumber']
        ]

        fig.add_trace(go.Scatter(
            x          = driver_laps['LapNumber'],
            y          = driver_laps['LapTimeSeconds'],
            mode       = 'lines',
            name       = driver,
            line       = dict(
                color = color if is_highlighted else '#2a2a44',
                width = 2.2 if is_highlighted else 0.8,
            ),
            opacity    = 1.0 if is_highlighted else 0.45,
            customdata = custom_data,
            hovertemplate=(
                '<b>%{customdata[0]}</b> (%{x} laps)<br>'
                'Lap time: %{y:.3f}s<br>'
                'Team: %{customdata[1]}<br>'
                '%{customdata[2]}<extra></extra>'
            ),
            legendrank = 1 if is_highlighted else 999,
        ))

    fig.update_layout(
        **DARK_LAYOUT,
        title     =dict(text='Lap Time Comparison', font=dict(size=16,
                        color='white'), x=0.02),
        xaxis_title='Lap Number',
        yaxis_title='Lap Time (seconds)',
        hovermode ='x unified',
        height    =480,
    )
    return fig


# ── Chart 2: Tyre Strategy Gantt ─────────────────────────────
def tyre_strategy_chart(stints: pd.DataFrame,
                         finishing_order: list) -> go.Figure:
    """
    Horizontal bar chart showing each driver's tyre stints.
    Drivers ordered by race finishing position (P1 at top).
    """
    fig = go.Figure()

    driver_order = [d['abbr'] for d in finishing_order]

    for _, stint in stints.iterrows():
        driver   = stint['Driver']
        compound = stint['Compound']
        color    = COMPOUND_COLORS.get(compound, '#888888')

        # Find position label
        pos_label = ''
        for d in finishing_order:
            if d['abbr'] == driver:
                pos_label = f"P{d['position']}  {d['abbr']}  {d['lastname']}"
                break

        fig.add_trace(go.Bar(
            name            = compound,
            orientation     = 'h',
            y               = [pos_label],
            x               = [stint['LapCount']],
            base            = [stint['StartLap']],
            marker_color    = color,
            marker_line     = dict(color='#0f0f1a', width=1),
            opacity         = 0.92,
            showlegend      = False,
            hovertemplate   = (
                f'<b>{driver}</b><br>'
                f'Compound: {compound}<br>'
                f'Laps {stint["StartLap"]}–{stint["EndLap"]} '
                f'({stint["LapCount"]} laps)<extra></extra>'
            ),
        ))

    # Reverse order so P1 is at the top
    ordered_labels = []
    for d in finishing_order:
        label = f"P{d['position']}  {d['abbr']}  {d['lastname']}"
        ordered_labels.append(label)

    fig.update_layout(
        **DARK_LAYOUT,
        title     =dict(text='Tyre Strategy', font=dict(size=16,
                        color='white'), x=0.02),
        xaxis_title='Lap Number',
        barmode   ='overlay',
        height    =max(380, len(finishing_order) * 30 + 80),
        showlegend=False,
    )
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(categoryorder='array',
                     categoryarray=list(reversed(ordered_labels)),
                     gridcolor='#1e1e3a', tickfont=dict(size=10))

    # Add compound color legend manually
    for compound, color in COMPOUND_COLORS.items():
        if compound in stints['Compound'].values:
            fig.add_trace(go.Bar(
                name         = compound.capitalize(),
                x            = [None], y=[None],
                marker_color = color,
                showlegend   = True,
            ))

    return fig


# ── Chart 3: Position Changes Bump Chart ─────────────────────
def position_chart(laps: pd.DataFrame, session,
                   highlight_drivers: list = None) -> go.Figure:
    """
    Animated bump chart: each driver's race position per lap.
    P1 is at the top. Lines crossing = overtakes.
    """
    laps = laps.copy()
    laps['Position']  = pd.to_numeric(laps['Position'], errors='coerce')
    laps              = laps.dropna(subset=['Position'])
    n_drivers         = laps['Driver'].nunique()

    if highlight_drivers is None:
        highlight_drivers = (
            laps.groupby('Driver')['Position']
            .last().sort_values().head(5).index.tolist()
        )

    fig = go.Figure()

    for driver in laps['Driver'].unique():
        driver_laps = (
            laps[laps['Driver'] == driver]
            .sort_values('LapNumber')
        )
        if len(driver_laps) == 0:
            continue

        info      = session.get_driver(driver)
        team      = info['TeamName']
        full_name = info['FullName']
        color     = TEAM_COLORS.get(team, '#888888')
        is_hl     = driver in highlight_drivers

        fig.add_trace(go.Scatter(
            x         = driver_laps['LapNumber'],
            y         = driver_laps['Position'],
            mode      = 'lines',
            name      = driver,
            line      = dict(
                color = color if is_hl else '#252540',
                width = 2.2 if is_hl else 0.8,
            ),
            opacity   = 1.0 if is_hl else 0.3,
            hovertemplate=(
                f'<b>{full_name}</b><br>'
                'Lap %{x}: P%{y}<extra></extra>'
            ),
        ))

    fig.update_layout(
        **DARK_LAYOUT,
        title      =dict(text='Position Changes', font=dict(size=16,
                         color='white'), x=0.02),
        xaxis_title='Lap Number',
        yaxis_title='Position',
        hovermode  ='x unified',
        height     =480,
    )
    # Update yaxis separately to avoid conflict with DARK_LAYOUT's yaxis key
    fig.update_yaxes(
        autorange='reversed',
        tickvals=list(range(1, n_drivers + 1)),
        ticktext=[f'P{i}' for i in range(1, n_drivers + 1)],
        gridcolor='#1e1e3a',
    )
    return fig


# ── Chart 4: Speed Trace ──────────────────────────────────────
def speed_trace_chart(tel1: pd.DataFrame, tel2: pd.DataFrame,
                       driver1: str, driver2: str,
                       lap1, lap2) -> go.Figure:
    """
    Three-panel speed trace: Speed / Throttle / Brake.
    Aligned by distance so both drivers can be compared fairly.
    """
    from plotly.subplots import make_subplots

    COLOR_1 = '#e63946'
    COLOR_2 = '#4a90d9'

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.30, 0.25],
        vertical_spacing=0.04,
        subplot_titles=['Speed (km/h)', 'Throttle (%)', 'Brake']
    )

    def lap_time_str(lap):
        t = lap['LapTime']
        total_s = t.total_seconds()
        mins    = int(total_s // 60)
        secs    = total_s % 60
        return f"{mins}:{secs:06.3f}"

    for row, (channel, name) in enumerate(
        [('Speed', 'Speed (km/h)'),
         ('Throttle', 'Throttle (%)'),
         ('Brake', 'Braking')], start=1
    ):
        for tel, driver, color in [
            (tel1, driver1, COLOR_1),
            (tel2, driver2, COLOR_2)
        ]:
            if channel == 'Brake':
                y_data = tel['Brake'].astype(float) * 100
            else:
                y_data = tel[channel]

            fig.add_trace(
                go.Scatter(
                    x         = tel['Distance'],
                    y         = y_data,
                    mode      = 'lines',
                    name      = driver,
                    line      = dict(color=color, width=1.6),
                    showlegend= (row == 1),
                    hovertemplate=(
                        f'<b>{driver}</b><br>'
                        f'{name}: %{{y:.1f}}<br>'
                        'Distance: %{x:.0f}m<extra></extra>'
                    ),
                ),
                row=row, col=1
            )

    t1_str = lap_time_str(lap1)
    t2_str = lap_time_str(lap2)

    fig.update_layout(
        **DARK_LAYOUT,
        title=dict(
            text=(f'Lap Comparison — {driver1} [{t1_str}] '
                  f'vs {driver2} [{t2_str}]'),
            font=dict(size=15, color='white'), x=0.02
        ),
        xaxis3_title='Distance (m)',
        height=580,
        hovermode='x unified',
    )
    # Style all subplots with dark theme
    for i in range(1, 4):
        fig.update_xaxes(gridcolor='#1e1e3a', row=i, col=1)
        fig.update_yaxes(gridcolor='#1e1e3a', row=i, col=1)

    return fig


# ── Chart 5: Racing Line on Circuit Map ──────────────────────
def circuit_map_chart(tel1: pd.DataFrame, driver1: str,
                       tel2: pd.DataFrame = None,
                       driver2: str = None,
                       color_by: str = 'Speed') -> go.Figure:
    """
    Plots GPS X/Y coordinates as a circuit map.
    Colors the line by Speed (or Throttle, Brake).
    Optionally overlays a second driver.
    """
    fig = go.Figure()

    COLOR_1 = '#e63946'
    COLOR_2 = '#4a90d9'

    # Driver 1 — colored by speed
    fig.add_trace(go.Scatter(
        x          = tel1['X'],
        y          = tel1['Y'],
        mode       = 'markers',
        name       = f'{driver1} ({color_by})',
        marker     = dict(
            color     = tel1[color_by],
            colorscale= 'RdYlGn',
            size      = 3,
            colorbar  = dict(
                title      = dict(
                    text = color_by,
                    font = dict(color='#ccccdd'),
                ),
                tickfont   = dict(color='#ccccdd'),
            ),
        ),
        hovertemplate=(
            f'<b>{driver1}</b><br>'
            f'{color_by}: %{{marker.color:.1f}}<extra></extra>'
        ),
    ))

    # Driver 2 — flat color overlay
    if tel2 is not None and driver2 is not None:
        fig.add_trace(go.Scatter(
            x    = tel2['X'],
            y    = tel2['Y'],
            mode = 'lines',
            name = driver2,
            line = dict(color=COLOR_2, width=1.2),
            opacity = 0.6,
        ))

    fig.update_layout(
        **DARK_LAYOUT,
        title  =dict(text=f'Circuit Map — Colored by {color_by}',
                     font=dict(size=16, color='white'), x=0.02),
        height =520,
    )
    fig.update_xaxes(showticklabels=False, showgrid=False,
                     zeroline=False, scaleanchor='y')
    fig.update_yaxes(showticklabels=False, showgrid=False,
                     zeroline=False)
    return fig
