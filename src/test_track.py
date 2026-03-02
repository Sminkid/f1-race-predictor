import requests
import pandas as pd
import matplotlib.pyplot as plt

SESSION_KEY = 9523

response = requests.get(
    "https://api.openf1.org/v1/location",
    params={"session_key": SESSION_KEY, "driver_number": 1}
)

df = pd.DataFrame(response.json())
df = df[(df['x'] != 0) & (df['y'] != 0)]
df['date'] = pd.to_datetime(df['date'])

# Exact lights out time we found from the data
lights_out = pd.Timestamp('2024-05-26 13:03:11', tz='UTC')
df_race = df[df['date'] >= lights_out]

# Plot
fig, ax = plt.subplots(figsize=(12, 10))

# Full track outline in grey
ax.plot(df['x'], df['y'], color='grey', linewidth=1, alpha=0.3, label='Full track')

# Race only in white
ax.plot(df_race['x'], df_race['y'], color='white', linewidth=1, alpha=0.6, label='Race laps')

# Grid position / race start
ax.scatter(-7626, -7093, color='lime', s=300, zorder=5, label='🚦 Lights Out')

ax.set_facecolor('black')
fig.patch.set_facecolor('black')
ax.tick_params(colors='white')
ax.set_title('Monaco 2024 - Verstappen Race Start', color='white', fontsize=14)
ax.legend(facecolor='black', labelcolor='white')
ax.set_aspect('equal')

plt.tight_layout()
plt.savefig('data/monaco_track.png', dpi=150, facecolor='black')
print("Done! Lights out at x:-7626, y:-7093 at 13:03:11 UTC")