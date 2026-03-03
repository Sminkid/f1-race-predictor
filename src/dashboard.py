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
MAX_SECONDS = 3900

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

interpolated = []
for driver in df['acronym'].unique():
    d = df[df['acronym'] == driver].copy().sort_values('seconds')
    if len(d) < 4:
        continue

    d_tmin = d['seconds'].min()
    d_tmax = d['seconds'].max()

    cs_x = CubicSpline(d['seconds'].values, d['x'].values)
    cs_y = CubicSpline(d['seconds'].values, d['y'].values)

    x_interp = np.full(len(t_common), np.nan)
    y_interp = np.full(len(t_common), np.nan)
    mask = (t_common >= d_tmin) & (t_common <= d_tmax)
    x_interp[mask] = cs_x(t_common[mask])
    y_interp[mask] = cs_y(t_common[mask])

    interpolated.append(pd.DataFrame({
        'frame_idx': np.arange(len(t_common)),
        'seconds': t_common,
        'x': x_interp,
        'y': y_interp,
        'acronym': driver,
        'team': d['team'].iloc[0],
        'colour': d['colour'].iloc[0],
    }))

smooth_df = pd.concat(interpolated, ignore_index=True)

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

# Pre-index frame data for O(1) lookup per tick
print("Pre-indexing frame data...")
frame_lookup = {}
for fid, grp in smooth_df.groupby('frame_idx'):
    grp_clean = grp.dropna(subset=['x', 'y'])
    frame_lookup[int(fid)] = {
        'x': grp_clean['x'].tolist(),
        'y': grp_clean['y'].tolist(),
        'text': grp_clean['acronym'].tolist(),
        'color': grp_clean['colour'].tolist(),
    }
print("Data ready!")

# ── Build Initial Figure ───────────────────────────────────────────────────────
print("Building initial figure...")

frame0 = smooth_df[smooth_df['frame_idx'] == 0].dropna(subset=['x', 'y'])

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
    x=frame0['x'].tolist(),
    y=frame0['y'].tolist(),
    mode='markers+text',
    text=frame0['acronym'].tolist(),
    textposition='top center',
    textfont=dict(color='white', size=9),
    marker=dict(
        color=frame0['colour'].tolist(),
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
app = dash.Dash(__name__)

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
    Output('frame-store', 'data', allow_duplicate=True),
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

    fd = frame_lookup.get(frame_idx, {'x': [], 'y': [], 'text': [], 'color': []})

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

    return patched_fig, timer, alerts, store


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        app.run(debug=True, use_reloader=False)
    except Exception as e:
        print(f"Error starting app: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
