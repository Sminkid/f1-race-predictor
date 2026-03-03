import dash
from dash import dcc, html, Input, Output, State
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

# Find lap boundaries (large jumps = crossing start/finish line)
lap_boundaries = ver_data[ver_data['movement'] > 1000].index.tolist()
print(f"Found {len(lap_boundaries)} lap boundaries")

# Use lap 2 for a clean representative lap
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

# BOT pitted at 3731 seconds
# Get his path around that time to capture pit lane
pit_window = bot_data[
    (bot_data['seconds'] >= 3600) &  # 2 mins before pit
    (bot_data['seconds'] <= 3800)    # 1 min after pit
]

pit_x = pit_window['x'].values
pit_y = pit_window['y'].values
print(f"Pit lane points: {len(pit_x)}")

# Pre-index frame data for O(1) lookup per tick (avoids full-dataframe scan)
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

# Build Plotly animation frames — 1 frame per second of race time.
# Plotly.js interpolates marker positions between frames entirely in the browser,
# so animation is smooth regardless of server round-trip latency.
FRAME_STEP = 10  # every 10 source frames = 1 second of race time (INTERP_RATE=0.1)
print("Building animation frames...")
anim_frames = []
for i in range(0, len(t_common), FRAME_STEP):
    fd = frame_lookup.get(i, {'x': [], 'y': [], 'text': [], 'color': []})
    anim_frames.append(go.Frame(
        data=[go.Scatter(
            x=fd['x'],
            y=fd['y'],
            text=fd['text'],
            marker=dict(color=fd['color']),
        )],
        traces=[2],
        name=str(i),
    ))
print(f"Built {len(anim_frames)} animation frames.")
print("Data ready!")

# ── Build Initial Figure ───────────────────────────────────────────────────────
print("Building initial figure...")

# Frame 0 car positions
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

# Trace 2: car markers (this is what Patch updates each frame)
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
    uirevision='track',  # preserves layout state across Patch updates
)

# Attach pre-computed frames so Plotly.js can animate client-side
initial_fig.frames = anim_frames

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
                            figure=initial_fig,  # make sure this is there
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
        dcc.Store(id='anim-store', data={
            'playing': False, 'speed': 1,
            'started_at_ms': 0, 'start_race_s': 0, 'current_race_s': 0
        }),
        # Fast interval just for the race timer display (client-side, no server hit)
        dcc.Interval(id='timer-interval', interval=250, n_intervals=0),
        # Slow interval for pit-stop alerts (server-side, 2s is fine)
        dcc.Interval(id='pit-interval', interval=2000, n_intervals=0),
    ]
)

# ── Callbacks ──────────────────────────────────────────────────────────────────

# Control buttons → call Plotly.animate in the browser + update anim-store
# No server round-trip means no jitter: animation runs entirely in Plotly.js
app.clientside_callback(
    """
    function(play, pause, fast, reset, store) {
        const triggered = dash_clientside.callback_context.triggered;
        if (!triggered || triggered.length === 0) return dash_clientside.no_update;
        if (!store) store = {playing: false, speed: 1, started_at_ms: 0, start_race_s: 0, current_race_s: 0};
        const btn = triggered[0].prop_id.split('.')[0];
        const MAX_RACE_S = """ + str(MAX_SECONDS) + """;

        // Dash wraps dcc.Graph in a container div — the actual Plotly plot
        // is the inner element with class 'js-plotly-plot'
        const graphDiv = document.getElementById('track-map').getElementsByClassName('js-plotly-plot')[0];
        if (!graphDiv) return dash_clientside.no_update;

        if (btn === 'play-btn') {
            Plotly.animate(graphDiv, null, {
                mode: 'immediate',
                fromcurrent: true,
                transition: {duration: 950, easing: 'linear'},
                frame: {duration: 1000, redraw: false}
            });
            return {
                playing: true, speed: 1,
                started_at_ms: Date.now(),
                start_race_s: store.current_race_s || 0,
                current_race_s: store.current_race_s || 0
            };

        } else if (btn === 'fast-btn') {
            Plotly.animate(graphDiv, null, {
                mode: 'immediate',
                fromcurrent: true,
                transition: {duration: 280, easing: 'linear'},
                frame: {duration: 300, redraw: false}
            });
            return {
                playing: true, speed: 10,
                started_at_ms: Date.now(),
                start_race_s: store.current_race_s || 0,
                current_race_s: store.current_race_s || 0
            };

        } else if (btn === 'pause-btn') {
            Plotly.animate(graphDiv, [], {mode: 'immediate'});
            const elapsed = store.started_at_ms > 0
                ? (Date.now() - store.started_at_ms) / 1000
                : 0;
            const race_s = Math.min(
                (store.start_race_s || 0) + elapsed * (store.speed || 1),
                MAX_RACE_S
            );
            return {...store, playing: false, current_race_s: race_s};

        } else if (btn === 'reset-btn') {
            Plotly.animate(graphDiv, ['0'], {
                mode: 'immediate',
                transition: {duration: 0},
                frame: {duration: 0, redraw: true}
            });
            return {playing: false, speed: 1, started_at_ms: 0,
                    start_race_s: 0, current_race_s: 0};
        }
        return dash_clientside.no_update;
    }
    """,
    Output('anim-store', 'data'),
    Input('play-btn', 'n_clicks'),
    Input('pause-btn', 'n_clicks'),
    Input('fast-btn', 'n_clicks'),
    Input('reset-btn', 'n_clicks'),
    State('anim-store', 'data'),
    prevent_initial_call=True,
)

# Race timer — runs entirely in the browser every 250 ms, zero server cost
app.clientside_callback(
    """
    function(n, store) {
        if (!store) return '\u23f1 00:00';
        let race_s;
        if (store.playing && store.started_at_ms > 0) {
            const elapsed = (Date.now() - store.started_at_ms) / 1000;
            race_s = Math.min(
                (store.start_race_s || 0) + elapsed * (store.speed || 1),
                """ + str(MAX_SECONDS) + """
            );
        } else {
            race_s = store.current_race_s || 0;
        }
        const mins = String(Math.floor(race_s / 60)).padStart(2, '0');
        const secs = String(Math.floor(race_s % 60)).padStart(2, '0');
        return '\u23f1 ' + mins + ':' + secs;
    }
    """,
    Output('race-timer', 'children'),
    Input('timer-interval', 'n_intervals'),
    State('anim-store', 'data'),
)

# Pit stop alerts — server-side but only fires every 2 s, which is fine
@app.callback(
    Output('pit-alerts', 'children'),
    Input('pit-interval', 'n_intervals'),
    State('anim-store', 'data'),
)
def update_pit_alerts(n, store):
    if not store:
        return html.Div("No active pit stops", style={'color': '#666'})
    if store.get('playing') and store.get('started_at_ms', 0) > 0:
        elapsed = time.time() - store['started_at_ms'] / 1000
        current_time = min(
            store['start_race_s'] + elapsed * store.get('speed', 1),
            MAX_SECONDS
        )
    else:
        current_time = store.get('current_race_s', 0)

    active_pits = pit_df[
        (pit_df['seconds'] <= current_time) &
        (pit_df['seconds'] >= current_time - 30)
    ]
    if len(active_pits) > 0:
        return [
            html.Div(
                f"\U0001f527 {row['acronym']} \u2014 Lap {row['lap']} \u2014 {row['duration']}s",
                style={'marginBottom': '8px', 'padding': '6px',
                       'backgroundColor': '#3a3a00', 'borderRadius': '4px'}
            )
            for _, row in active_pits.iterrows()
        ]
    return html.Div("No active pit stops", style={'color': '#666'})


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        app.run(debug=True, use_reloader=False)
    except Exception as e:
        print(f"Error starting app: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")