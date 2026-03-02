import pandas as pd
import plotly.graph_objects as go

LIGHTS_OUT = pd.Timestamp('2024-05-26 13:03:11', tz='UTC')

print("Loading position data...")
df = pd.read_csv('data/monaco_2024_positions.csv')
df['date'] = pd.to_datetime(df['date'], utc=True)

print("Sampling frames for animation...")

# Sample every 5 seconds to keep animation smooth but not too heavy
df['seconds'] = (df['date'] - LIGHTS_OUT).dt.total_seconds().astype(int)
df = df[df['seconds'] >= 0]  # Race only

# Sample every second
sampled = df[df['seconds'] % 1 == 0].copy()
timestamps = sorted(sampled['seconds'].unique())

print(f"Total frames: {len(timestamps)}")

# Build track outline using VER's full race data
track = df[df['acronym'] == 'VER'][['x', 'y']].iloc[::3]

print("Building animation frames...")

frames = []
for t in timestamps[::2]:  # every 10 seconds for speed
    frame_data = sampled[sampled['seconds'] == t]
    
    frame = go.Frame(
        data=[
            # Track outline
            go.Scatter(
                x=track['x'], y=track['y'],
                mode='lines',
                line=dict(color='rgba(255,255,255,0.15)', width=8),
                hoverinfo='none',
                showlegend=False
            ),
            # Car positions
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
                hovertemplate='<b>%{text}</b><br>X: %{x}<br>Y: %{y}<extra></extra>',
                showlegend=False
            )
        ],
        name=str(t)
    )
    frames.append(frame)

# Build slider steps
steps = []
for t in timestamps[::2]:
    mins = t // 60
    secs = t % 60
    steps.append(dict(
        args=[[str(t)], dict(frame=dict(duration=200, redraw=True), mode='immediate')],
        label=f"{mins}:{secs:02d}",
        method='animate'
    ))

# Initial frame
first = sampled[sampled['seconds'] == timestamps[0]]

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
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, scaleanchor='x'),
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
                    frame=dict(duration=200, redraw=True),
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
print("You'll see all 20 cars moving around Monaco with Play/Pause and a time slider!")