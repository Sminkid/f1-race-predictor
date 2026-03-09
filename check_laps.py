import fastf1
import pandas as pd

session = fastf1.get_session(2024, 'Monaco', 'R')
session.load()

laps = session.laps
print(laps[['Driver', 'LapNumber', 'LapStartTime']].head(20))
print("\nColumns:", laps.columns.tolist())
