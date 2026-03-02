import requests
import pandas as pd
import plotly.graph_objects as go
import time

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
print("\nSaved to data/monaco_2024_positions.csv!")
print("You won't need to download this again.")