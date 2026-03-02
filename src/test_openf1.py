import requests
import pandas as pd

# Get Monaco 2024 qualifying session key first
response = requests.get(
    "https://api.openf1.org/v1/sessions",
    params={
        "year": 2024,
        "country_name": "Monaco",
        "session_type": "Race"
    }
)

session = response.json()[0]
print("Session found!")
print(f"Session Key: {session['session_key']}")
print(f"Session Name: {session['session_name']}")
print(f"Date: {session['date_start']}")