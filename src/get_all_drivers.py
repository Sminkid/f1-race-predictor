import requests
import pandas as pd
import time

SESSION_KEY = 9523

# First get all drivers in this session
response = requests.get(
    "https://api.openf1.org/v1/drivers",
    params={"session_key": SESSION_KEY}
)

drivers = response.json()
print(f"Found {len(drivers)} drivers\n")

for d in drivers:
    print(f"Car {d['driver_number']:>2} | {d['name_acronym']} | {d['team_name']}")