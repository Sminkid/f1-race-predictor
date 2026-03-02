import requests
import pandas as pd

SESSION_KEY = 9523

# Get car positions for Verstappen
response = requests.get(
    "https://api.openf1.org/v1/location",
    params={
        "session_key": SESSION_KEY,
        "driver_number": 1
    }
)

data = response.json()
df = pd.DataFrame(data)

# Filter out the 0,0 positions (car in garage)
df = df[(df['x'] != 0) & (df['y'] != 0)]

# Convert date to datetime
df['date'] = pd.to_datetime(df['date'])

print(f"Total position updates after filtering: {len(df)}")
print("\nFirst 10 real positions:")
print(df[['driver_number', 'x', 'y', 'date']].head(10))

print("\nX range:", df['x'].min(), "to", df['x'].max())
print("Y range:", df['y'].min(), "to", df['y'].max())