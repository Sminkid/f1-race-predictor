from scipy.interpolate import CubicSpline
import pandas as pd
import numpy as np
import plotly.graph_objects as go

LIGHTS_OUT = pd.Timestamp('2024-05-26 13:03:11', tz='UTC')
INTERP_RATE = 0.05
MAX_SECONDS = 600

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

print("Interpolating with cubic spline...")
t_common = np.arange(0, MAX_SECONDS + INTERP_RATE, INTERP_RATE)
n_frames = len(t_common)

interpolated = []
for driver in df['acronym'].unique():
    d = df[df['acronym'] == driver].copy().sort_values('seconds')
    
    if len(d) < 4:
        continue

    d_tmin = d['seconds'].min()
    d_tmax = d['seconds'].max()

    # Cubic spline for smooth curves through corners
    cs_x = CubicSpline(d['seconds'].values, d['x'].values)
    cs_y = CubicSpline(d['seconds'].values, d['y'].values)

    x_interp = np.full(len(t_common), np.nan)
    y_interp = np.full(len(t_common), np.nan)

    mask = (t_common >= d_tmin) & (t_common <= d_tmax)
    x_interp[mask] = cs_x(t_common[mask])
    y_interp[mask] = cs_y(t_common[mask])

    interp_df = pd.DataFrame({
        'frame_idx': np.arange(n_frames),
        'seconds': t_common,
        'x': x_interp,
        'y': y_interp,
        'acronym': driver,
        'team': d['team'].iloc[0],
        'colour': d['colour'].iloc[0],
        'car_number': d['car_number'].iloc[0]
    })
    interpolated.append(interp_df)

smooth_df = pd.concat(interpolated, ignore_index=True)
print(f"Smooth data points: {len(smooth_df):,}")

frame_indices = list(range(n_frames))
idx_to_seconds = dict(enumerate(t_common))
print(f"Total animation frames: {n_frames}")

track = df[df['acronym'] == 'VER'][['x', 'y']].iloc[::3]

print("Building animation frames...")
frames = []
for i in frame_indices:
    frame_data = smooth_df[smooth_df['frame_idx'] == i].dropna(subset=['x', 'y'])
    
    frames.append(go.Frame(
        data=[
            go.Scatter(
                x=track['x'], y=track['y'],
                mode='lines',
                line=dict(color='rgba(255,255,255,0.15)', width=8),
                hoverinfo='none',
                showlegend=False
            ),
            go.Scatter(
                x=frame_data['x'],
                y=frame_data['y'],
                mode='markers+text',
                marker=dict(
                    size=14,
                    color=frame_data['colour'].tolist(),
                    line=dict(color='white', width=1)
                ),
                text=frame_data['acronym'].tolist(),
                textposition='top center',
                textfont=dict(color='white', size=9),
                hovertemplate='<b>%{text}</b><extra></extra>',
                showlegend=False
            )
        ],
        name=str(i)
    ))

steps = []
for i in frame_indices:
    t = idx_to_seconds[i]
    if round(t) % 30 == 0 and abs(t - round(t)) < INTERP_RATE / 2:
        mins = int(t) // 60
        secs = int(t) % 60
        label = f"{mins}:{secs:02d}"
    else:
        label = ""
    steps.append(dict(
        args=[[str(i)], dict(
            frame=dict(duration=50, redraw=True),
            mode='immediate'
        )],
        label=label,
        method='animate'
    ))

first = smooth_df[smooth_df['frame_idx'] == 0].dropna(subset=['x', 'y'])

fig = go.Figure(
    data=[
        go.Scatter(
            x=track['x'], y=track['y'],
            mode='lines',
            line=dict(color='rgba(255,255,255,0.15)', width=8),
            hoverinfo='none',
            showlegend=False
        ),
        go.Scatter(
            x=first['x'], y=first['y'],
            mode='markers+text',
            marker=dict(
                size=14,
                color=first['colour'].tolist(),
                line=dict(color='white', width=1)
            ),
            text=first['acronym'].tolist(),
            textposition='top center',
            textfont=dict(color='white', size=9),
            showlegend=False
        )
    ],
    frames=frames
)

fig.update_layout(
    title=dict(
        text='🏎️ Monaco GP 2024 — Race Replay',
        font=dict(color='white', size=20),
        x=0.5
    ),
    paper_bgcolor='#1a1a1a',
    plot_bgcolor='#1a1a1a',
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True, range=[-9000, 4000]),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True, scaleanchor='x', range=[-11000, 2000]),
    updatemenus=[dict(
        type='buttons',
        showactive=False,
        y=0.02,
        x=0.5,
        xanchor='center',
        buttons=[
            dict(
                label='▶ Play',
                method='animate',
                args=[None, dict(
                    frame=dict(duration=50, redraw=True),
                    fromcurrent=True,
                    mode='immediate'
                )]
            ),
            dict(
                label='⏸ Pause',
                method='animate',
                args=[[None], dict(
                    frame=dict(duration=0, redraw=False),
                    mode='immediate'
                )]
            ),
            dict(
                label='⏩ Fast',
                method='animate',
                args=[None, dict(
                    frame=dict(duration=16, redraw=True),
                    fromcurrent=True,
                    mode='immediate'
                )]
            ),
            dict(
                label='⏩⏩ Turbo',
                method='animate',
                args=[None, dict(
                    frame=dict(duration=5, redraw=True),
                    fromcurrent=True,
                    mode='immediate'
                )]
            )
        ]
    )],
    sliders=[dict(
        steps=steps,
        x=0.05,
        y=0.0,
        len=0.9,
        currentvalue=dict(
            prefix='Race Time: ',
            font=dict(color='white'),
            visible=True
        ),
        font=dict(color='white')
    )],
    height=750,
    margin=dict(l=20, r=20, t=60, b=100)
)

print("Saving replay...")
fig.write_html('data/monaco_replay.html')
print("\n✅ Done! Open data/monaco_replay.html in your browser!")