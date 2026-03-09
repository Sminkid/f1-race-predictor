import requests
import pandas as pd
import fastf1
import time
import os

# ── Config ──────────────────────────────────────────────
SESSION_KEY = 9523
LIGHTS_OUT = pd.Timestamp('2024-05-26 13:03:11', tz='UTC')

# Real F1 2024 team colours
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

# All 20 drivers with their team
DRIVERS = {
    1: ('VER', 'Red Bull Racing'),
    2: ('SAR', 'Williams'),
    3: ('RIC', 'RB'),
    4: ('NOR', 'McLaren'),
    10: ('GAS', 'Alpine'),
    11: ('PER', 'Red Bull Racing'),
    14: ('ALO', 'Aston Martin'),
    16: ('LEC', 'Ferrari'),
    18: ('STR', 'Aston Martin'),
    20: ('MAG', 'Haas F1 Team'),
    22: ('TSU', 'RB'),
    23: ('ALB', 'Williams'),
    24: ('ZHO', 'Kick Sauber'),
    27: ('HUL', 'Haas F1 Team'),
    31: ('OCO', 'Alpine'),
    44: ('HAM', 'Mercedes'),
    55: ('SAI', 'Ferrari'),
    63: ('RUS', 'Mercedes'),
    77: ('BOT', 'Kick Sauber'),
    81: ('PIA', 'McLaren'),
}

# ── Step 1: Download GPS positions ──────────────────────
def download_positions():
    print("Step 1: Downloading GPS positions...")
    # YOUR CODE HERE — paste the logic from build_replay.py
    # save to data/monaco_2024_positions.csv

    print("Fetching position data for all 20 drivers...")
    print("This will take 2-3 minutes, grabbing a lot of data!\n")

    all_positions = []

    for car_number, (acronym, team) in DRIVERS.items():
        print(f"  Loading {acronym}...")
        
        response = requests.get(
            "https://api.openf1.org/v1/location",
            params={
                "session_key": SESSION_KEY,
                "driver_number": car_number
            }
        )
        
        df = pd.DataFrame(response.json())
        
        if len(df) == 0:
            print(f"  No data for {acronym}, skipping")
            continue
        
        # Filter zeros and add driver info
        df = df[(df['x'] != 0) & (df['y'] != 0)].copy()
        df['date'] = pd.to_datetime(df['date'])
        df['acronym'] = acronym
        df['team'] = team
        df['colour'] = TEAM_COLOURS.get(team, '#FFFFFF')
        df['car_number'] = car_number
        
        # Only keep race data from lights out
        df = df[df['date'] >= LIGHTS_OUT]
        
        all_positions.append(df)
        
        # Small delay to be nice to the API
        time.sleep(0.5)

    # Combine all drivers into one dataframe
    print("\nCombining all data...")
    full_df = pd.concat(all_positions, ignore_index=True)
    full_df = full_df.sort_values('date').reset_index(drop=True)

    print(f"Total position updates loaded: {len(full_df):,}")
    print(f"Drivers loaded: {full_df['acronym'].nunique()}")

    # Save to CSV so we don't have to re-download every time!
    full_df.to_csv('data/monaco_2024_positions.csv', index=False)

# ── Step 2: Generate laps CSV ───────────────────────────
def generate_laps(session):
    print("Step 2: Generating lap data...")
    # YOUR CODE HERE — paste the logic from generate_laps.py
    # save to data/monaco_2024_laps.csv
    lights_out_td = session.laps['LapStartTime'].min()
    laps = session.laps[session.laps['Driver'] == 'LEC'][['LapNumber', 'LapStartTime']].copy()
    laps['seconds'] = (laps['LapStartTime'] - lights_out_td).dt.total_seconds()
    laps = laps[laps['seconds'] >= 0].sort_values('seconds')
    laps[['LapNumber', 'seconds']].to_csv('data/monaco_2024_laps.csv', index=False)

# ── Step 3: Generate track status CSV ───────────────────
def generate_track_status(session):
        print("Step 3: Generating track status...")
        # YOUR CODE HERE — paste the logic from generate_track_status.py
        # save to data/monaco_2024_track_status.csv

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

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    
    download_positions()
    
    print("\nLoading FastF1 session (cached after first run)...")
    session = fastf1.get_session(2024, 'Monaco', 'R')
    session.load()
    
    generate_laps(session)
    generate_track_status(session)
    
    print("\n✅ All data ready. Run: python src/dashboard.py")