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
    hoverlabel   =dict(bgcolor='#1a1a2e', bordercolor='#333355',
                       font=dict(color='white', size=12)),
)

# Default margin — applied separately so charts can override without conflict
DARK_MARGIN = dict(l=60, r=30, t=60, b=60)

# Default axis styling applied after every update_layout call
DARK_AXES = dict(gridcolor='#1e1e3a', zerolinecolor='#1e1e3a',
                 tickfont=dict(size=11))


def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    """
    Convert a hex color string like '#e63946' to
    'rgba(230, 57, 70, 0.15)' for use as Plotly fillcolor.
    Falls back to the original color if conversion fails.
    """
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'rgba({r},{g},{b},{alpha})'
    except Exception:
        return hex_color

ACCENT = '#e63946'   # F1 red


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply the shared dark theme to any Plotly figure."""
    fig.update_layout(**DARK_LAYOUT)
    fig.update_layout(margin=DARK_MARGIN)
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

# ── Chart 6: Gap to Leader ────────────────────────────────────
def gap_to_leader_chart(laps: pd.DataFrame, session,
                         highlight_drivers: list = None) -> go.Figure:
    """
    Classic F1 broadcast chart — time gap between every driver
    and the race leader per lap.

    How gap is calculated:
      Each lap, we find the cumulative race time for every driver
      (sum of all lap times up to that lap). The leader has the
      lowest cumulative time. Gap = driver_cumtime - leader_cumtime.

    A growing gap = falling behind.
    A shrinking gap = closing in (or leader pitted).
    Negative gap = that driver IS the leader (shown at 0).
    """
    laps = laps.copy()
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

    # Only use accurate laps — removes safety car distortion
    clean = laps[laps['IsAccurate'] == True].copy()

    # Build cumulative race time per driver per lap
    cum_times = []
    for driver in clean['Driver'].unique():
        dlaps = (clean[clean['Driver'] == driver]
                 .sort_values('LapNumber')
                 .copy())
        dlaps['CumTime'] = dlaps['LapTimeSeconds'].cumsum()
        cum_times.append(dlaps[['Driver', 'LapNumber', 'CumTime']])

    cum_df = pd.concat(cum_times, ignore_index=True)

    # For each lap, find the minimum cumulative time (= leader)
    leader_time = (cum_df.groupby('LapNumber')['CumTime']
                   .min()
                   .reset_index()
                   .rename(columns={'CumTime': 'LeaderTime'}))

    cum_df = cum_df.merge(leader_time, on='LapNumber')
    cum_df['GapToLeader'] = cum_df['CumTime'] - cum_df['LeaderTime']

    if highlight_drivers is None:
        highlight_drivers = (
            laps.groupby('Driver')['Position']
            .last().dropna().sort_values().head(6).index.tolist()
        )

    fig = go.Figure()

    for driver in cum_df['Driver'].unique():
        driver_data = cum_df[cum_df['Driver'] == driver] \
                      .sort_values('LapNumber')
        if len(driver_data) == 0:
            continue

        info      = session.get_driver(driver)
        team      = info['TeamName']
        full_name = info['FullName']
        color     = TEAM_COLORS.get(team, '#888888')
        is_hl     = driver in highlight_drivers

        fig.add_trace(go.Scatter(
            x         = driver_data['LapNumber'],
            y         = driver_data['GapToLeader'],
            mode      = 'lines',
            name      = driver,
            line      = dict(
                color = color if is_hl else '#252540',
                width = 2.0 if is_hl else 0.7,
            ),
            opacity   = 1.0 if is_hl else 0.3,
            hovertemplate=(
                f'<b>{full_name}</b><br>'
                'Lap %{x}<br>'
                'Gap: +%{y:.3f}s<extra></extra>'
            ),
        ))

    # Zero line = the leader's position
    fig.add_hline(
        y=0, line_color='#ffffff',
        line_width=0.8, line_dash='dot',
        annotation_text='Leader',
        annotation_font_color='#888899',
        annotation_position='bottom right',
    )

    fig.update_layout(
        **DARK_LAYOUT,
        title     =dict(text='Gap to Race Leader', font=dict(size=16,
                        color='white'), x=0.02),
        xaxis_title='Lap Number',
        yaxis_title='Gap (seconds)',
        hovermode ='x unified',
        height    =480,
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 7: Race Pace Comparison ─────────────────────────────
def race_pace_chart(laps: pd.DataFrame, session,
                    drivers: list = None) -> go.Figure:
    """
    Box plot showing each driver's race pace distribution.

    Why box plots for pace?
      A single average lap time is misleading — it includes
      outliers like pit-out laps and safety car laps. A box plot
      shows the full distribution: median pace, consistency
      (box height), and outliers (dots outside the whiskers).

      Narrow box + low median = fast AND consistent = ideal race pace.

    Filters applied before plotting:
      - Only accurate laps (IsAccurate == True)
      - Removes laps in the top 5% slowest (safety car, pit out)
    """
    laps = laps.copy()
    laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

    clean = laps[laps['IsAccurate'] == True].copy()

    # Remove the slowest 5% of laps (pit exits, SC laps)
    p95 = clean['LapTimeSeconds'].quantile(0.95)
    clean = clean[clean['LapTimeSeconds'] <= p95]

    # Get finishing order for sorting
    finishing_order = (
        laps.groupby('Driver')['Position']
        .last().dropna().sort_values().index.tolist()
    )

    if drivers is None:
        drivers = finishing_order  # all drivers

    # Filter to selected drivers, keep finishing order
    plot_drivers = [d for d in finishing_order if d in drivers]

    fig = go.Figure()

    for driver in plot_drivers:
        driver_laps = clean[clean['Driver'] == driver]['LapTimeSeconds']
        if len(driver_laps) < 3:
            continue

        info  = session.get_driver(driver)
        team  = info['TeamName']
        color = TEAM_COLORS.get(team, '#888888')

        fig.add_trace(go.Box(
            y              = driver_laps,
            name           = driver,
            marker_color   = color,
            line_color     = color,
            fillcolor      = hex_to_rgba(color, 0.25),
            opacity        = 0.85,
            boxpoints      = 'outliers',
            marker         = dict(size=3, opacity=0.5),
            hovertemplate  = (
                f'<b>{driver}</b> — {info["TeamName"]}<br>'
                'Lap time: %{y:.3f}s<extra></extra>'
            ),
        ))

    fig.update_layout(
        **DARK_LAYOUT,
        title     =dict(text='Race Pace Comparison', font=dict(size=16,
                        color='white'), x=0.02),
        xaxis_title='Driver',
        yaxis_title='Lap Time (seconds)',
        showlegend=False,
        height    =460,
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 8: Driver Rating Bar Chart ─────────────────────────
def driver_rating_bar(ratings_df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart of composite driver ratings.
    Bars colored by team. Sorted highest to lowest.
    """
    df    = ratings_df.copy().sort_values('Rating', ascending=True)
    teams = df['Team'].tolist()
    colors = [TEAM_COLORS.get(t, '#888888') for t in teams]

    fig = go.Figure(go.Bar(
        x             = df['Rating'],
        y             = df['Driver'],
        orientation   = 'h',
        marker_color  = colors,
        marker_line   = dict(color='#0f0f1a', width=0.8),
        text          = df['Rating'].apply(lambda x: f'{x:.1f}'),
        textposition  = 'outside',
        textfont      = dict(color='#ccccdd', size=11),
        customdata    = df[['Name', 'Team', 'Finish']].values,
        hovertemplate = (
            '<b>%{customdata[0]}</b><br>'
            'Team: %{customdata[1]}<br>'
            'Finished: P%{customdata[2]}<br>'
            'Rating: %{x:.1f}<extra></extra>'
        ),
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title    = dict(text='Driver Performance Rating',
                        font=dict(size=16, color='white'), x=0.02),
        xaxis_title='Rating (0–100)',
        height   = max(420, len(df) * 28 + 80),
        xaxis    = dict(range=[0, 115]),
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 9: Radar / Spider Chart per driver ─────────────────
def driver_radar_chart(ratings_df: pd.DataFrame,
                        drivers: list) -> go.Figure:
    """
    Radar (spider) chart comparing up to 4 drivers across
    all 6 performance dimensions.

    Each axis = one scoring dimension.
    A larger area = better overall performance.
    Shape of the polygon reveals strengths/weaknesses —
    e.g. large 'Pace' + small 'Consistency' = fast but erratic.
    """
    categories = ['Finish', 'Positions\nGained', 'Pace',
                  'Consistency', 'Qualifying', 'Teammate\nDelta']
    score_cols  = ['score_finish', 'score_positions_gained',
                   'score_pace',   'score_consistency',
                   'score_quali',  'score_teammate']

    COLORS = ['#e63946', '#4a90d9', '#2a9d8f', '#f4a261']

    fig = go.Figure()

    for i, driver in enumerate(drivers[:4]):   # max 4 drivers
        row = ratings_df[ratings_df['Driver'] == driver]
        if len(row) == 0:
            continue
        row    = row.iloc[0]
        values = [row[c] for c in score_cols]
        # Close the polygon by repeating first value
        values_closed     = values + [values[0]]
        categories_closed = categories + [categories[0]]

        fig.add_trace(go.Scatterpolar(
            r         = values_closed,
            theta     = categories_closed,
            fill      = 'toself',
            name      = f"{driver}  {row['Name'].split()[-1]}",
            line      = dict(color=COLORS[i], width=2),
            fillcolor = hex_to_rgba(COLORS[i], 0.15),
            opacity   = 0.9,
            hovertemplate=(
                f'<b>{driver}</b><br>'
                '%{theta}: %{r:.1f}<extra></extra>'
            ),
        ))

    fig.update_layout(
        **DARK_LAYOUT,
        title  = dict(text='Performance Radar', font=dict(size=16,
                      color='white'), x=0.02),
        polar  = dict(
            bgcolor   = '#16213e',
            radialaxis= dict(
                visible   = True,
                range     = [0, 100],
                gridcolor = '#1e1e3a',
                tickfont  = dict(color='#555577', size=9),
                tickvals  = [25, 50, 75, 100],
            ),
            angularaxis=dict(
                gridcolor = '#1e1e3a',
                tickfont  = dict(color='#aaaacc', size=11),
                linecolor = '#1e1e3a',
            ),
        ),
        height = 480,
    )
    return fig


# ── Chart 10: Score Breakdown Heatmap ────────────────────────
def score_heatmap(ratings_df: pd.DataFrame) -> go.Figure:
    """
    Heatmap: drivers (rows) × scoring dimensions (columns).
    Color = score 0-100. Makes it instantly obvious who
    excels in which dimension.
    """
    df = ratings_df.sort_values('Rating', ascending=False)

    score_cols  = ['score_finish', 'score_positions_gained',
                   'score_pace',   'score_consistency',
                   'score_quali',  'score_teammate']
    col_labels  = ['Finish', 'Pos Gained', 'Pace',
                   'Consistency', 'Qualifying', 'Teammate']

    z      = df[score_cols].values.round(1)
    y_labs = df['Driver'].tolist()

    fig = go.Figure(go.Heatmap(
        z            = z,
        x            = col_labels,
        y            = y_labs,
        colorscale   = 'RdYlGn',
        zmin         = 0,
        zmax         = 100,
        text         = z,
        texttemplate = '%{text:.0f}',
        textfont     = dict(size=10, color='white'),
        hovertemplate= (
            'Driver: %{y}<br>'
            'Metric: %{x}<br>'
            'Score: %{z:.1f}<extra></extra>'
        ),
        colorbar=dict(
            title     = dict(text='Score', font=dict(color='#ccccdd')),
            tickfont  = dict(color='#ccccdd'),
        ),
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title  = dict(text='Score Breakdown — All Drivers × All Metrics',
                      font=dict(size=16, color='white'), x=0.02),
        height = max(420, len(df) * 26 + 100),
    )
    fig.update_layout(margin=dict(l=80, r=100, t=60, b=60))
    fig.update_xaxes(side='top', tickfont=dict(color='#aaaacc', size=11))
    fig.update_yaxes(tickfont=dict(color='#aaaacc', size=11),
                     autorange='reversed')
    return fig


# ── Chart 11: Tyre Degradation Curve ─────────────────────────
def tyre_deg_chart(stint_data: pd.DataFrame,
                   predictions: dict,
                   session) -> go.Figure:
    """
    Scatter plot of actual lap times vs tyre age per compound,
    overlaid with the Random Forest predicted degradation curve.

    actual dots  = real lap times from the race
    smooth line  = RF model prediction
    The gap between them = model error
    """
    from utils.data_loader import COMPOUND_COLORS

    fig = go.Figure()

    compounds = stint_data['Compound'].unique()

    for compound in compounds:
        color  = COMPOUND_COLORS.get(compound, '#888888')
        subset = stint_data[stint_data['Compound'] == compound]

        # ── Actual lap times (scatter dots) ──────────────────
        fig.add_trace(go.Scatter(
            x          = subset['TyreLife'],
            y          = subset['LapTime'],
            mode       = 'markers',
            name       = f'{compound.capitalize()} (actual)',
            marker     = dict(color=color, size=4, opacity=0.45),
            hovertemplate=(
                f'<b>{compound.capitalize()}</b><br>'
                'Tyre age: %{x} laps<br>'
                'Lap time: %{y:.3f}s<extra></extra>'
            ),
        ))

        # ── Predicted curve (smooth line) ────────────────────
        if compound in predictions:
            pred_df = predictions[compound]
            fig.add_trace(go.Scatter(
                x          = pred_df['TyreLife'],
                y          = pred_df['PredictedTime'],
                mode       = 'lines',
                name       = f'{compound.capitalize()} (predicted)',
                line       = dict(color=color, width=2.5),
                hovertemplate=(
                    f'<b>{compound.capitalize()} — Predicted</b><br>'
                    'Tyre age: %{x} laps<br>'
                    'Predicted: %{y:.3f}s<extra></extra>'
                ),
            ))

    fig.update_layout(
        **DARK_LAYOUT,
        title      = dict(text='Tyre Degradation — Actual vs Predicted',
                          font=dict(size=16, color='white'), x=0.02),
        xaxis_title= 'Tyre Age (laps)',
        yaxis_title= 'Lap Time (seconds)',
        hovermode  = 'x unified',
        height     = 500,
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 12: Degradation Rate Bar Chart ─────────────────────
def deg_rate_chart(deg_rates: dict) -> go.Figure:
    """
    Bar chart showing linear degradation rate per compound.
    Rate = seconds lost per additional lap on the tyre.
    Higher bar = faster degradation.
    """
    from utils.data_loader import COMPOUND_COLORS

    compounds = list(deg_rates.keys())
    rates     = [deg_rates[c] for c in compounds]
    colors    = [COMPOUND_COLORS.get(c, '#888888') for c in compounds]

    fig = go.Figure(go.Bar(
        x             = compounds,
        y             = rates,
        marker_color  = colors,
        marker_line   = dict(color='#0f0f1a', width=1),
        text          = [f'+{r*1000:.0f} ms/lap' if r > 0
                         else f'{r*1000:.0f} ms/lap' for r in rates],
        textposition  = 'outside',
        textfont      = dict(color='#ccccdd', size=11),
        hovertemplate = (
            '<b>%{x}</b><br>'
            'Deg rate: %{y:.4f} s/lap<br>'
            '= %{text}<extra></extra>'
        ),
    ))

    fig.update_layout(
        **DARK_LAYOUT,
        title      = dict(text='Linear Degradation Rate per Compound',
                          font=dict(size=16, color='white'), x=0.02),
        xaxis_title= 'Compound',
        yaxis_title= 'Degradation Rate (seconds per lap)',
        height     = 380,
        showlegend = False,
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 13: Driver Stint Degradation Comparison ────────────
def driver_deg_comparison(stint_data: pd.DataFrame,
                           drivers: list,
                           compound: str,
                           session) -> go.Figure:
    """
    Compare how different drivers degrade the same compound.
    Each driver's laps on the selected compound plotted as a line.
    Steeper slope = faster degradation for that driver.
    """
    from utils.data_loader import TEAM_COLORS
    import numpy as np

    fig    = go.Figure()
    colors = ['#e63946', '#4a90d9', '#2a9d8f',
              '#f4a261', '#e9c46a', '#a8dadc']

    subset = stint_data[stint_data['Compound'] == compound.upper()]

    for i, driver in enumerate(drivers):
        dlaps = (subset[subset['Driver'] == driver]
                 .sort_values('TyreLife'))
        if len(dlaps) < 3:
            continue

        try:
            info  = session.get_driver(driver)
            label = f"{driver}  {info['LastName']}"
            team  = info['TeamName']
            color = TEAM_COLORS.get(team, colors[i % len(colors)])
        except Exception:
            label = driver
            color = colors[i % len(colors)]

        # Scatter: actual laps
        fig.add_trace(go.Scatter(
            x          = dlaps['TyreLife'],
            y          = dlaps['LapTime'],
            mode       = 'lines+markers',
            name       = label,
            line       = dict(color=color, width=1.8),
            marker     = dict(color=color, size=5),
            hovertemplate=(
                f'<b>{label}</b><br>'
                'Tyre age: %{x} laps<br>'
                'Lap time: %{y:.3f}s<extra></extra>'
            ),
        ))

    fig.update_layout(
        **DARK_LAYOUT,
        title      = dict(
            text=f'Driver Degradation Comparison — '
                 f'{compound.capitalize()} Compound',
            font=dict(size=16, color='white'), x=0.02
        ),
        xaxis_title= 'Tyre Age (laps)',
        yaxis_title= 'Lap Time (seconds)',
        hovermode  = 'x unified',
        height     = 460,
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 14: Strategy Comparison Bar ────────────────────────
def strategy_comparison_chart(strategies_df: pd.DataFrame,
                               actual: dict = None,
                               top_n: int = 15) -> go.Figure:
    """
    Horizontal bar chart of top N strategies by total race time.
    Each bar = one strategy. Gap to optimal shown as annotation.
    Actual driver strategy highlighted in a different color.
    """
    df = strategies_df.head(top_n).copy()
    df = df.sort_values('TotalTime', ascending=False)  # flip for h bar

    colors = []
    for _, row in df.iterrows():
        if actual and row.get('Strategy') == actual.get('label'):
            colors.append('#f4a261')   # orange = actual strategy
        elif row['VsOptimal'] == 0:
            colors.append('#57c785')   # green = optimal
        else:
            colors.append('#4a90d9')   # blue = alternatives

    fig = go.Figure(go.Bar(
        x             = df['TotalTime'],
        y             = df['Strategy'],
        orientation   = 'h',
        marker_color  = colors,
        marker_line   = dict(color='#0f0f1a', width=0.5),
        text          = df['VsOptimal'].apply(
            lambda x: 'OPTIMAL' if x == 0 else f'+{x:.1f}s'
        ),
        textposition  = 'outside',
        textfont      = dict(color='#ccccdd', size=10),
        hovertemplate = (
            '<b>%{y}</b><br>'
            'Total time: %{x:.1f}s<br>'
            'vs Optimal: +%{text}<extra></extra>'
        ),
    ))

    # X axis range: just around the relevant range
    x_min = df['TotalTime'].min() * 0.9995
    x_max = df['TotalTime'].max() * 1.0005

    fig.update_layout(
        **DARK_LAYOUT,
        title      = dict(text='Top Strategy Options by Total Race Time',
                          font=dict(size=16, color='white'), x=0.02),
        xaxis_title= 'Predicted Total Race Time (seconds)',
        height     = max(400, top_n * 30 + 80),
        xaxis      = dict(range=[x_min, x_max]),
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 15: Strategy Timeline ───────────────────────────────
def strategy_timeline_chart(strategies_df: pd.DataFrame,
                              actual_strategy: dict,
                              total_laps: int,
                              top_n: int = 5) -> go.Figure:
    """
    Gantt-style chart showing the top N optimal strategies
    as tyre stint timelines, vs the actual strategy used.
    Makes it visually clear where the strategies differ.
    """
    from utils.data_loader import COMPOUND_COLORS

    fig  = go.Figure()
    rows = []

    # Add actual strategy at top
    if actual_strategy:
        pits      = [0] + actual_strategy['pit_laps'] + [total_laps]
        compounds = actual_strategy['compounds']
        for i in range(len(pits) - 1):
            c     = compounds[i] if i < len(compounds) else 'UNKNOWN'
            color = COMPOUND_COLORS.get(c.upper(), '#888888')
            fig.add_trace(go.Bar(
                name          = c.capitalize(),
                orientation   = 'h',
                y             = ['✅ Actual Strategy'],
                x             = [pits[i + 1] - pits[i]],
                base          = [pits[i]],
                marker_color  = color,
                marker_line   = dict(color='#0f0f1a', width=1),
                showlegend    = False,
                hovertemplate = (
                    f'<b>Actual</b><br>'
                    f'{c.capitalize()}: laps {pits[i]}–{pits[i+1]}'
                    f'<extra></extra>'
                ),
            ))

    # Add top N optimal strategies
    top_strats = strategies_df.head(top_n)
    for rank, (_, strat) in enumerate(top_strats.iterrows(), 1):
        pit1  = strat['Pit Lap 1']
        pit2  = strat.get('Pit Lap 2')
        c1    = strat.get('C1', '')
        c2    = strat.get('C2', '')
        c3    = strat.get('C3')
        label = (f"#{rank} Optimal  "
                 f"(+{strat['VsOptimal']:.1f}s)")

        stints = [(0, pit1, c1)]
        if pit2:
            stints += [(pit1, pit2, c2), (pit2, total_laps, c3 or c2)]
        else:
            stints += [(pit1, total_laps, c2)]

        for start, end, compound in stints:
            if not compound:
                continue
            color = COMPOUND_COLORS.get(compound.upper(), '#888888')
            fig.add_trace(go.Bar(
                name          = compound.capitalize(),
                orientation   = 'h',
                y             = [label],
                x             = [end - start],
                base          = [start],
                marker_color  = color,
                marker_line   = dict(color='#0f0f1a', width=1),
                showlegend    = False,
                hovertemplate = (
                    f'<b>{label}</b><br>'
                    f'{compound.capitalize()}: '
                    f'laps {start}–{end}<extra></extra>'
                ),
            ))

    # Compound legend
    for compound, color in COMPOUND_COLORS.items():
        if compound in ['SOFT', 'MEDIUM', 'HARD',
                        'INTERMEDIATE', 'WET']:
            fig.add_trace(go.Bar(
                name         = compound.capitalize(),
                x            = [None], y=[None],
                marker_color = color,
                showlegend   = True,
            ))

    fig.update_layout(
        **DARK_LAYOUT,
        title      = dict(
            text='Strategy Timeline — Actual vs Optimal Options',
            font=dict(size=16, color='white'), x=0.02
        ),
        xaxis_title= 'Lap Number',
        barmode    = 'stack',
        height     = max(300, (top_n + 2) * 55 + 80),
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 14: Strategy Total Time Comparison ─────────────────
def strategy_comparison_chart(strategies_df, actual_time=None,
                               actual_label=None) -> go.Figure:
    """
    Bar chart of top N strategies by total predicted race time.
    Highlights optimal strategy. Optionally marks actual time.
    """
    top = strategies_df.head(20).copy()
    top['rank'] = range(1, len(top) + 1)

    # Normalise times to offset from the best strategy
    best_time = top['total_time'].min()
    top['delta'] = top['total_time'] - best_time

    colors = []
    for i, row in top.iterrows():
        if row['stops'] == 0:
            colors.append('#888888')
        elif row['stops'] == 1:
            colors.append('#2a9d8f')
        else:
            colors.append('#e9c46a')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x             = top['label'],
        y             = top['delta'],
        marker_color  = colors,
        marker_line   = dict(color='#0f0f1a', width=0.8),
        text          = top['delta'].apply(
            lambda x: 'Optimal' if x < 0.01 else f'+{x:.1f}s'
        ),
        textposition  = 'outside',
        textfont      = dict(color='#ccccdd', size=10),
        hovertemplate = (
            '<b>%{x}</b><br>'
            'Extra time vs optimal: +%{y:.2f}s<extra></extra>'
        ),
    ))

    # Mark actual driver time if provided
    if actual_time is not None and actual_label is not None:
        actual_delta = actual_time - best_time
        fig.add_hline(
            y              = actual_delta,
            line_color     = '#e63946',
            line_width     = 2,
            line_dash      = 'dash',
            annotation_text= f'Actual: {actual_label} (+{actual_delta:.1f}s)',
            annotation_font= dict(color='#e63946', size=11),
            annotation_position='top right',
        )

    fig.update_layout(
        **DARK_LAYOUT,
        title      = dict(text='Strategy Optimisation — Top 20 Strategies',
                          font=dict(size=16, color='white'), x=0.02),
        xaxis_title= 'Strategy',
        yaxis_title= 'Extra time vs optimal (seconds)',
        height     = 480,
        showlegend = False,
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(tickangle=-35, tickfont=dict(size=9),
                     gridcolor='#1e1e3a')
    fig.update_yaxes(**DARK_AXES)
    return fig


# ── Chart 15: Pit Window Heatmap ─────────────────────────────
def pit_window_heatmap(strategies_df, compound1, compound2,
                        total_laps) -> go.Figure:
    """
    Heatmap: pit lap (x) vs extra time (color) for 1-stop strategies
    with a fixed compound sequence. Shows which lap is the optimal
    pit window and how sensitive it is.

    Green = close to optimal time.
    Red = significantly slower than optimal.
    """
    import numpy as np

    one_stop = strategies_df[
        (strategies_df['stops'] == 1) &
        (strategies_df['stint1_comp'] == compound1) &
        (strategies_df['stint2_comp'] == compound2)
    ].copy()

    if len(one_stop) == 0:
        return None

    best = one_stop['total_time'].min()
    one_stop['delta'] = one_stop['total_time'] - best

    pit_laps = one_stop['pit1_lap'].astype(int).tolist()
    deltas   = one_stop['delta'].tolist()

    fig = go.Figure(go.Scatter(
        x          = pit_laps,
        y          = deltas,
        mode       = 'lines+markers',
        line       = dict(color='#2a9d8f', width=2.5),
        marker     = dict(
            color     = deltas,
            colorscale= 'RdYlGn_r',
            size      = 8,
            colorbar  = dict(
                title    = dict(text='Extra time (s)',
                                font=dict(color='#ccccdd')),
                tickfont = dict(color='#ccccdd'),
            ),
        ),
        hovertemplate=(
            'Pit on lap %{x}<br>'
            'Extra time: +%{y:.2f}s vs optimal<extra></extra>'
        ),
    ))

    # Mark optimal pit lap
    best_lap = one_stop.loc[one_stop['delta'].idxmin(), 'pit1_lap']
    fig.add_vline(
        x              = best_lap,
        line_color     = '#57c785',
        line_width     = 2,
        line_dash      = 'dash',
        annotation_text= f'Optimal: Lap {int(best_lap)}',
        annotation_font= dict(color='#57c785', size=11),
    )

    fig.update_layout(
        **DARK_LAYOUT,
        title      = dict(
            text=(f'Pit Window Sensitivity — '
                  f'{compound1.capitalize()} → {compound2.capitalize()}'),
            font=dict(size=16, color='white'), x=0.02
        ),
        xaxis_title= 'Pit Stop Lap',
        yaxis_title= 'Extra time vs optimal (s)',
        height     = 400,
    )
    fig.update_layout(margin=DARK_MARGIN)
    fig.update_xaxes(**DARK_AXES)
    fig.update_yaxes(**DARK_AXES)
    return fig
