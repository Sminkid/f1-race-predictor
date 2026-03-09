import fastf1
import pandas as pd

session = fastf1.get_session(2024, 'Monaco', 'R')
session.load()

lights_out = pd.Timestamp('2024-05-26 13:03:11', tz='UTC')

# Find the GREEN flag (race start) in session status
ss = session.session_status
print(ss)

# Also check track status
ts = session.track_status
print(ts.head(10))
