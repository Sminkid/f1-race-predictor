import dash
from dash import dcc, html, Patch, Input, Output, State, ctx
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy.interpolate import CubicSpline
import time

# ── Constants ──────────────────────────────────────────────────────────────────

print("Script started")
LIGHTS_OUT = pd.Timestamp('2024-05-26 13:03:11', tz='UTC')
INTERP_RATE = 0.1
MAX_SECONDS = 8800  # full Monaco 2024 race (~145 min)

TEAM_COLOURS = {
    'Red Bull Racing': '#3671C6',
    'Mercedes':        '#27F4D2',
    'Ferrari':         '#E8002D',
    'McLaren':         '#FF8000',
    'Aston Martin':    '#229971',
    'Alpine':          '#FF87BC',
    'Williams':        '#64C4FF',
    'RB':              '#6692FF',
    'Haas F1 Team':    '#B6BABD',
    'Kick Sauber':     '#52E252',
}

PIT_STOPS = [
    {'acronym': 'BOT', 'lap': 15, 'duration': 24.2, 'seconds': 3731.140},
    {'acronym': 'STR', 'lap': 42, 'duration': 24.1, 'seconds': 5899.599},
    {'acronym': 'STR', 'lap': 48, 'duration': 28.2, 'seconds': 6405.313},
    {'acronym': 'HAM', 'lap': 51, 'duration': 24.2, 'seconds': 6564.455},
    {'acronym': 'VER', 'lap': 52, 'duration': 23.8, 'seconds': 6639.854},
    {'acronym': 'SAR', 'lap': 57, 'duration': 24.3, 'seconds': 7137.732},
    {'acronym': 'ZHO', 'lap': 70, 'duration': 24.3, 'seconds': 8178.604},
]
pit_df = pd.DataFrame(PIT_STOPS)

# ── Load Track Status Data ────────────────────────────────────────────────────
track_status_df = pd.read_csv('data/monaco_2024_track_status.csv')

FLAG_STYLES = {
    'GREEN':                {'bg': '#003300', 'color': '#00ee00', 'icon': '🟢'},
    'CLEAR':                {'bg': '#003300', 'color': '#00ee00', 'icon': '🟢'},
    'CHEQUERED':            {'bg': '#333333', 'color': '#ffffff', 'icon': '🏁'},
    'RED':                  {'bg': '#330000', 'color': '#ff3333', 'icon': '🔴'},
    'YELLOW':               {'bg': '#332200', 'color': '#ffcc00', 'icon': '🟡'},
    'DOUBLE YELLOW':        {'bg': '#332200', 'color': '#ffaa00', 'icon': '🟡'},
    'SAFETY CAR':           {'bg': '#332200', 'color': '#ffcc00', 'icon': '🚗'},
    'VIRTUAL SAFETY CAR':   {'bg': '#332d00', 'color': '#ffaa00', 'icon': '🚗'},
}

# ── Load & Process Data ────────────────────────────────────────────────────────
print("Loading position data...")
df = pd.read_csv('data/monaco_2024_positions.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)
df['seconds'] = (df['date'] - LIGHTS_OUT).dt.total_seconds()
df = df[df['seconds'] >= 0]

print("Cleaning GPS glitches...")
cleaned = []
for driver in df['acronym'].unique():
    d = df[df['acronym'] == driver].copy().sort_values('seconds')
    d['movement'] = d['x'].diff().abs() + d['y'].diff().abs()
    d = d[d['movement'] < 500].copy()
    cleaned.append(d)
df = pd.concat(cleaned, ignore_index=True)

print("Interpolating positions...")
t_common = np.arange(0, MAX_SECONDS + INTERP_RATE, INTERP_RATE)
n_frames = len(t_common)

# Build per-driver arrays during the spline pass, then stack into matrices.
# This replaces the slow groupby frame_lookup (was 30 s) with a single
# np.column_stack call — startup is now <1 s.
driver_names  = []
driver_colors = []
x_cols = []
y_cols = []

for driver in df['acronym'].unique():
    d = df[df['acronym'] == driver].copy().sort_values('seconds')
    if len(d) < 4:
        continue

    cs_x = CubicSpline(d['seconds'].values, d['x'].values)
    cs_y = CubicSpline(d['seconds'].values, d['y'].values)

    x_interp = np.full(n_frames, np.nan)
    y_interp = np.full(n_frames, np.nan)
    mask = (t_common >= d['seconds'].min()) & (t_common <= d['seconds'].max())
    x_interp[mask] = cs_x(t_common[mask])
    y_interp[mask] = cs_y(t_common[mask])

    driver_names.append(driver)
    driver_colors.append(d['colour'].iloc[0])
    x_cols.append(x_interp)
    y_cols.append(y_interp)

# X_mat / Y_mat shape: (n_frames, n_drivers)
# Row i contains all driver positions at frame i — O(1) slice per tick
X_mat = np.column_stack(x_cols)   # shape (n_frames, n_drivers)
Y_mat = np.column_stack(y_cols)
driver_colors_arr = np.array(driver_colors)
driver_names_arr  = np.array(driver_names)

print(f"Position matrices built: {X_mat.shape}  ({X_mat.nbytes / 1e6:.1f} MB)")
print("Data ready!")

# Get one clean lap for track outline
print("Extracting single clean lap for track outline...")
ver_data = df[df['acronym'] == 'VER'].copy().sort_values('seconds')
ver_data['movement'] = ver_data['x'].diff().abs() + ver_data['y'].diff().abs()

lap_boundaries = ver_data[ver_data['movement'] > 1000].index.tolist()
print(f"Found {len(lap_boundaries)} lap boundaries")

if len(lap_boundaries) >= 2:
    lap_start = lap_boundaries[0]
    lap_end = lap_boundaries[1]
    single_lap = ver_data.loc[lap_start:lap_end]
else:
    single_lap = ver_data.iloc[:1000]

track_x = single_lap['x'].values
track_y = single_lap['y'].values
print(f"Single lap extracted: {len(track_x)} points")

# Extract pit lane from BOT's pit stop lap
print("Extracting pit lane path...")
bot_data = df[df['acronym'] == 'BOT'].copy().sort_values('seconds')
bot_data['movement'] = bot_data['x'].diff().abs() + bot_data['y'].diff().abs()

pit_window = bot_data[
    (bot_data['seconds'] >= 3600) &
    (bot_data['seconds'] <= 3800)
]

pit_x = pit_window['x'].values
pit_y = pit_window['y'].values
print(f"Pit lane points: {len(pit_x)}")
print("Data ready!")

# ── Build Initial Figure ───────────────────────────────────────────────────────
print("Building initial figure...")

# Frame 0: visible drivers (not NaN)
_mask0 = ~np.isnan(X_mat[0])
f0_x      = X_mat[0][_mask0].tolist()
f0_y      = Y_mat[0][_mask0].tolist()
f0_names  = driver_names_arr[_mask0].tolist()
f0_colors = driver_colors_arr[_mask0].tolist()

initial_fig = go.Figure()

# Trace 0: track outline
initial_fig.add_trace(go.Scatter(
    x=track_x.tolist(), y=track_y.tolist(),
    mode='lines',
    line=dict(color='#555555', width=8),
    name='Track',
    hoverinfo='skip',
))

# Trace 1: pit lane
initial_fig.add_trace(go.Scatter(
    x=pit_x.tolist(), y=pit_y.tolist(),
    mode='lines',
    line=dict(color='#888888', width=4, dash='dot'),
    name='Pit Lane',
    hoverinfo='skip',
))

# Trace 2: car markers (Patch updates only this trace each frame)
initial_fig.add_trace(go.Scatter(
    x=f0_x,
    y=f0_y,
    mode='markers+text',
    text=f0_names,
    textposition='top center',
    textfont=dict(color='white', size=9),
    marker=dict(
        color=f0_colors,
        size=12,
        line=dict(color='white', width=1),
    ),
    name='Cars',
    hoverinfo='text',
))

# Compute fixed axis ranges from track + pit data with padding
all_x = np.concatenate([track_x, pit_x])
all_y = np.concatenate([track_y, pit_y])
x_pad = (all_x.max() - all_x.min()) * 0.05
y_pad = (all_y.max() - all_y.min()) * 0.05
x_range = [all_x.min() - x_pad, all_x.max() + x_pad]
y_range = [all_y.min() - y_pad, all_y.max() + y_pad]

initial_fig.update_layout(
    paper_bgcolor='#1a1a1a',
    plot_bgcolor='#1a1a1a',
    xaxis=dict(
        visible=False,
        range=x_range,
        fixedrange=True,
        scaleanchor='y',
        scaleratio=1,
    ),
    yaxis=dict(
        visible=False,
        range=y_range,
        fixedrange=True,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False,
    uirevision='track',
)

print("Initial figure built.")

# ── App Layout ─────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div(
    style={'backgroundColor': '#1a1a1a', 'height': '100vh', 'fontFamily': 'Arial'},
    children=[

        # Header
        html.Div(
            style={'textAlign': 'center', 'padding': '10px'},
            children=[
                html.H1("Monaco GP 2024 — Live Replay",
                        style={'color': 'white', 'margin': '0', 'fontSize': '24px'})
            ]
        ),

        # Main content - track map + sidebar
        html.Div(
            style={'display': 'flex', 'height': '80vh'},
            children=[

                # Track map
                html.Div(
                    style={'flex': '3'},
                    children=[
                        dcc.Graph(
                            id='track-map',
                            figure=initial_fig,
                            style={'height': '100%'},
                            config={'displayModeBar': False}
                        )
                    ]
                ),

                # Sidebar
                html.Div(
                    style={
                        'flex': '1',
                        'backgroundColor': '#2a2a2a',
                        'padding': '15px',
                        'overflowY': 'auto'
                    },
                    children=[
                        html.H3("Race Info",
                                style={'color': 'white', 'marginTop': '0'}),
                        html.Div(id='race-timer',
                                 style={'color': '#ff0000', 'fontSize': '24px',
                                        'fontWeight': 'bold', 'marginBottom': '15px'}),
                        html.H4("Pit Stops",
                                style={'color': 'white'}),
                        html.Div(id='pit-alerts',
                                 style={'color': 'orange', 'fontSize': '13px'}),
                        html.H4("Track Status",
                                style={'color': 'white', 'marginTop': '20px'}),
                        html.Div(id='track-status',
                                 style={'fontSize': '13px'}),
                    ]
                )
            ]
        ),

        # Controls
        html.Div(
            style={'textAlign': 'center', 'padding': '10px'},
            children=[
                html.Button('▶ Play', id='play-btn',
                            style={'margin': '5px', 'padding': '8px 20px',
                                   'backgroundColor': '#ff0000', 'color': 'white',
                                   'border': 'none', 'borderRadius': '5px',
                                   'cursor': 'pointer', 'fontSize': '14px'}),
                html.Button('⏸ Pause', id='pause-btn',
                            style={'margin': '5px', 'padding': '8px 20px',
                                   'backgroundColor': '#444', 'color': 'white',
                                   'border': 'none', 'borderRadius': '5px',
                                   'cursor': 'pointer', 'fontSize': '14px'}),
                html.Button('⏩ Fast', id='fast-btn',
                            style={'margin': '5px', 'padding': '8px 20px',
                                   'backgroundColor': '#444', 'color': 'white',
                                   'border': 'none', 'borderRadius': '5px',
                                   'cursor': 'pointer', 'fontSize': '14px'}),
                html.Button('↺ Reset', id='reset-btn',
                            style={'margin': '5px', 'padding': '8px 20px',
                                   'backgroundColor': '#444', 'color': 'white',
                                   'border': 'none', 'borderRadius': '5px',
                                   'cursor': 'pointer', 'fontSize': '14px'}),
            ]
        ),

        # Scrubber slider
        html.Div(
            style={'padding': '0 30px 10px 30px'},
            children=[
                dcc.Slider(
                    id='time-slider',
                    min=0,
                    max=MAX_SECONDS,
                    step=1,
                    value=0,
                    marks={
                        int(s): {
                            'label': f"{int(s)//3600:01d}:{(int(s)%3600)//60:02d}",
                            'style': {'color': '#aaa', 'fontSize': '11px'}
                        }
                        for s in range(0, MAX_SECONDS + 1, 900)  # mark every 15 mins
                    },
                    tooltip={'placement': 'bottom', 'always_visible': False},
                    updatemode='mouseup',
                    included=True,
                    className='race-slider',
                    disabled=False,
                )
            ]
        ),

        # Hidden state storage
        dcc.Store(id='frame-store', data={
            'frame': 0, 'playing': False, 'speed': 1,
            'start_time': 0, 'start_frame': 0
        }),
        dcc.Interval(id='interval', interval=50, n_intervals=0, disabled=True),
    ]
)

# ── Callbacks ──────────────────────────────────────────────────────────────────

@app.callback(
    Output('frame-store', 'data'),
    Output('interval', 'disabled'),
    Input('play-btn', 'n_clicks'),
    Input('pause-btn', 'n_clicks'),
    Input('fast-btn', 'n_clicks'),
    Input('reset-btn', 'n_clicks'),
    State('frame-store', 'data'),
    prevent_initial_call=True
)
def handle_controls(play, pause, fast, reset, store):
    triggered = ctx.triggered_id
    if triggered == 'play-btn':
        store['start_time'] = time.time()
        store['start_frame'] = store['frame']
        store['playing'] = True
        store['speed'] = 1
        return store, False
    elif triggered == 'pause-btn':
        if store['playing']:
            elapsed = time.time() - store['start_time']
            store['frame'] = min(
                store['start_frame'] + elapsed * (1 / INTERP_RATE) * store['speed'],
                len(t_common) - 1
            )
        store['playing'] = False
        return store, True
    elif triggered == 'fast-btn':
        store['start_time'] = time.time()
        store['start_frame'] = store['frame']
        store['playing'] = True
        store['speed'] = 3
        return store, False
    elif triggered == 'reset-btn':
        store['frame'] = 0
        store['start_frame'] = 0
        store['playing'] = False
        return store, True
    return store, True


@app.callback(
    Output('track-map', 'figure'),
    Output('race-timer', 'children'),
    Output('pit-alerts', 'children'),
    Output('track-status', 'children'),
    Output('frame-store', 'data', allow_duplicate=True),
    Output('time-slider', 'value', allow_duplicate=True),
    Input('interval', 'n_intervals'),
    State('frame-store', 'data'),
    prevent_initial_call=True
)
def tick(n, store):
    if store['playing']:
        elapsed = time.time() - store['start_time']
        store['frame'] = min(
            store['start_frame'] + elapsed * (1 / INTERP_RATE) * store['speed'],
            len(t_common) - 1
        )

    frame_idx = int(store['frame'])
    current_time = t_common[frame_idx]

    # O(1) numpy slice — no dict lookup needed
    _mask = ~np.isnan(X_mat[frame_idx])
    fd = {
        'x':     X_mat[frame_idx][_mask].tolist(),
        'y':     Y_mat[frame_idx][_mask].tolist(),
        'text':  driver_names_arr[_mask].tolist(),
        'color': driver_colors_arr[_mask].tolist(),
    }

    patched_fig = Patch()
    patched_fig['data'][2]['x'] = fd['x']
    patched_fig['data'][2]['y'] = fd['y']
    patched_fig['data'][2]['text'] = fd['text']
    patched_fig['data'][2]['marker']['color'] = fd['color']

    mins = int(current_time) // 60
    secs = int(current_time) % 60
    timer = f"⏱ {mins:02d}:{secs:02d}"

    active_pits = pit_df[
        (pit_df['seconds'] <= current_time) &
        (pit_df['seconds'] >= current_time - 30)
    ]
    if len(active_pits) > 0:
        alerts = [
            html.Div(
                f"🔧 {row['acronym']} — Lap {row['lap']} — {row['duration']}s",
                style={'marginBottom': '8px', 'padding': '6px',
                       'backgroundColor': '#3a3a00', 'borderRadius': '4px'}
            )
            for _, row in active_pits.iterrows()
        ]
    else:
        alerts = html.Div("No active pit stops", style={'color': '#666'})

    # ── Track status ──────────────────────────────────────────────────────────
    past_events = track_status_df[track_status_df['seconds'] <= current_time]
    if len(past_events) > 0:
        current_flag = past_events.iloc[-1]['flag']
        style = FLAG_STYLES.get(current_flag, {'bg': '#222', 'color': '#fff', 'icon': '❓'})

        # Current status badge
        badge = html.Div(
            f"{style['icon']} {current_flag}",
            style={
                'backgroundColor': style['bg'],
                'color': style['color'],
                'fontWeight': 'bold',
                'fontSize': '16px',
                'padding': '8px 12px',
                'borderRadius': '6px',
                'marginBottom': '10px',
                'border': f"1px solid {style['color']}",
                'textAlign': 'center',
            }
        )

        # History list (most recent first, last 8 events)
        history = [
            html.Div(
                f"Lap {int(row['lap_number'])}  {FLAG_STYLES.get(row['flag'], {'icon': '❓'})['icon']}  {row['flag']}",
                style={
                    'color': FLAG_STYLES.get(row['flag'], {'color': '#aaa'})['color'],
                    'fontSize': '12px',
                    'padding': '3px 0',
                    'borderBottom': '1px solid #333',
                }
            )
            for _, row in past_events.tail(8).iloc[::-1].iterrows()
        ]
        track_status = [badge] + history
    else:
        track_status = html.Div("No events yet", style={'color': '#666'})

    return patched_fig, timer, alerts, track_status, store, current_time


@app.callback(
    Output('frame-store', 'data', allow_duplicate=True),
    Input('time-slider', 'value'),
    State('frame-store', 'data'),
    prevent_initial_call=True
)
def handle_scrub(slider_val, store):
    """Jump to slider position; resets clock so playback continues correctly."""
    if slider_val is None:
        return store
    target_frame = min(int(slider_val / INTERP_RATE), len(t_common) - 1)
    store['frame'] = target_frame
    store['start_frame'] = target_frame
    store['start_time'] = time.time()
    return store


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        app.run(debug=True, use_reloader=False)
    except Exception as e:
        print(f"Error starting app: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
