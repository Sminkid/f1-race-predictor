import requests
import pandas as pd

SESSION_KEY = 9523

response = requests.get(
    "https://api.openf1.org/v1/pit",
    params={"session_key": SESSION_KEY}
)

pits = pd.DataFrame(response.json())

# Filter out pre-race garage stops
real_pits = pits[pits['pit_duration'] < 100].copy()

# Add driver names
DRIVERS = {
     1: 'VER',  2: 'SAR',  3: 'RIC',  4: 'NOR',
    10: 'GAS', 11: 'PER', 14: 'ALO', 16: 'LEC',
    18: 'STR', 20: 'MAG', 22: 'TSU', 23: 'ALB',
    24: 'ZHO', 27: 'HUL', 31: 'OCO', 44: 'HAM',
    55: 'SAI', 63: 'RUS', 77: 'BOT', 81: 'PIA'
}

real_pits['acronym'] = real_pits['driver_number'].map(DRIVERS)
real_pits['date'] = pd.to_datetime(real_pits['date'], utc=True)

print(f"Total real pit stops: {len(real_pits)}")
print("\nAll real pit stops:")
print(real_pits[['acronym', 'lap_number', 'pit_duration', 'date']].to_string())

LIGHTS_OUT = pd.Timestamp('2024-05-26 13:03:11', tz='UTC')
real_pits['seconds_into_race'] = (real_pits['date'] - LIGHTS_OUT).dt.total_seconds()

print("\nPit stops with race timing:")
print(real_pits[['acronym', 'lap_number', 'pit_duration', 'seconds_into_race']].to_string())