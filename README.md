# f1-race-predictor
Cos I love f1 that much

# 🏎️ F1 Race Replay Dashboard

A race replay dashboard built with real F1 GPS data from OpenF1 and FastF1.

## What It Does
- Animates all 20 cars around the circuit using real GPS data
- Smooth cubic spline interpolation between position updates
- Team colours for each car
- Play, Pause, Fast Forward and Turbo speed controls

## Setup (Mac & Windows)

### 1. Clone the repo
git clone https://github.com/Sminkid/f1-race-predictor.git
cd f1-race-predictor

### 2. Create virtual environment
# Mac
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate

### 3. Install dependencies
pip install -r requirements.txt

### 4. Download race data
python src/build_replay.py

### 5. Build the replay
python src/animate_replay.py

### 6. Open the replay
# Mac
open data/monaco_replay.html

# Windows
start data\monaco_replay.html

## Project Structure
f1-race-predictor/
├── src/
│   ├── app.py              # Streamlit dashboard
│   ├── build_replay.py     # Downloads GPS data for all drivers
│   ├── animate_replay.py   # Builds the animated replay
│   ├── get_data.py         # FastF1 data fetching
│   └── test_*.py           # Test scripts
├── data/                   # Generated data (not in GitHub)
│   ├── cache/              # FastF1 cache
│   └── monaco_2024_positions.csv
├── requirements.txt
└── README.md

## Notes
- data/ folder is not pushed to GitHub (too large)
- Run build_replay.py first to download data before animating
- Tested on Mac and Windows