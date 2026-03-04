# f1-race-predictor
Cos I love f1 that much

# 🏎️ F1 Race Replay Dashboard

A race replay dashboard built with real F1 GPS data from OpenF1 and FastF1.

## What It Does
- Animates all 20 cars around the circuit using real GPS data
- Smooth cubic spline interpolation between position updates
- Team colours for each car
- Live lap counter (e.g. Lap 12 / 78)
- Track status flags (Green, Yellow, Red, Safety Car, etc.) with history
- Pit stop alerts as they happen
- Play, Pause, Fast Forward controls

## Setup (Mac & Windows)

### 1. Clone the repo
```bash
git clone https://github.com/Sminkid/f1-race-predictor.git
cd f1-race-predictor
```

### 2. Create virtual environment
```bash
# Mac
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download race position data
```bash
python src/get_data.py
```

### 5. Generate supporting data files
These files are not in the repo (too large) and must be generated locally.

**Lap data:**
```bash
cat > generate_laps.py << 'EOF'
import fastf1
import pandas as pd

session = fastf1.get_session(2024, 'Monaco', 'R')
session.load()

lights_out_td = session.laps['LapStartTime'].min()
laps = session.laps[session.laps['Driver'] == 'LEC'][['LapNumber', 'LapStartTime']].copy()
laps['seconds'] = (laps['LapStartTime'] - lights_out_td).dt.total_seconds()
laps = laps[laps['seconds'] >= 0].sort_values('seconds')
laps[['LapNumber', 'seconds']].to_csv('data/monaco_2024_laps.csv', index=False)
print("Done!")
EOF
python generate_laps.py
```

**Track status data:**
```bash
cat > generate_track_status.py << 'EOF'
import fastf1
import pandas as pd

session = fastf1.get_session(2024, 'Monaco', 'R')
session.load()

laps_df = pd.read_csv('data/monaco_2024_laps.csv')
lights_out_td = session.laps['LapStartTime'].min()

ts = session.track_status.copy()
ts['seconds'] = (ts['Time'] - lights_out_td).dt.total_seconds()
ts = ts[ts['seconds'] >= 0]
ts['flag'] = ts['Status'].map({
    '1': 'GREEN', '2': 'YELLOW', '3': 'DOUBLE YELLOW',
    '4': 'SAFETY CAR', '5': 'RED', '6': 'VIRTUAL SAFETY CAR', '7': 'CHEQUERED',
})

def get_lap(seconds):
    past = laps_df[laps_df['seconds'] <= seconds]
    return 1 if len(past) == 0 else int(past.iloc[-1]['LapNumber'])

ts['lap_number'] = ts['seconds'].apply(get_lap)
ts[['seconds', 'flag', 'lap_number']].to_csv('data/monaco_2024_track_status.csv', index=False)
print("Done!")
EOF
python generate_track_status.py
```

### 6. Run the dashboard
```bash
python src/dashboard.py
```
Then open your browser and go to: `http://127.0.0.1:8050`

## Controls
| Button | Action |
|--------|--------|
| ▶ Play | Start replay at normal speed |
| ⏸ Pause | Pause replay |
| ⏩ Fast | 3x speed |
| ↺ Reset | Return to start |

## Project Structure
```
f1-race-predictor/
├── src/
│   ├── dashboard.py        # Main Dash replay app
│   ├── get_data.py         # Downloads GPS position data
│   ├── build_replay.py     # Builds static HTML replay
│   ├── animate_replay.py   # Animates the static replay
│   └── test_*.py           # Test scripts
├── data/                   # Generated data (not in GitHub)
│   ├── monaco_2024_positions.csv
│   ├── monaco_2024_laps.csv
│   └── monaco_2024_track_status.csv
├── requirements.txt
└── README.md
```

## Notes
- The `data/` folder is not pushed to GitHub (too large) — generate it locally using the steps above
- Always run from the project root (`f1-race-predictor/`) so file paths resolve correctly
- FastF1 caches session data after the first download, so subsequent runs are much faster
- Tested on Mac