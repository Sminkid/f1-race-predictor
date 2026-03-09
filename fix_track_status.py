import pandas as pd

laps_df = pd.read_csv('data/monaco_2024_laps.csv')
ts = pd.read_csv('data/monaco_2024_track_status.csv')

def get_lap(seconds):
    past = laps_df[laps_df['seconds'] <= seconds]
    if len(past) == 0:
        return 1
    return int(past.iloc[-1]['LapNumber'])

ts['lap_number'] = ts['seconds'].apply(get_lap)
ts.to_csv('data/monaco_2024_track_status.csv', index=False)
print(ts[['seconds', 'flag', 'lap_number']].head(15))
print("Done!")
