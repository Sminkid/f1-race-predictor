import fastf1
import pandas as pd

# Enable cache
fastf1.Cache.enable_cache('data/cache')

# Load 2024 Bahrain GP
session = fastf1.get_session(2024, 'Bahrain', 'R')
session.load()

# Get lap data
laps = session.laps
print(laps[['Driver', 'LapTime', 'Compound', 'LapNumber']].head(20))