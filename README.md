# 🏎️ F1 Monaco GP 2024 — Live Race Replay

An interactive real-time replay of the 2024 Monaco Grand Prix, built with Python, Dash, and Plotly. Watch all 20 drivers navigate the iconic streets of Monte Carlo with live GPS telemetry data.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Dash](https://img.shields.io/badge/Dash-Plotly-blue?logo=plotly&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- **Live Track Map** — Real-time 2D replay of all 20 cars on the Monaco circuit using GPS telemetry
- **Race Controls** — Play, Pause, Fast Forward (3x), and Reset
- **Pit Stop Alerts** — Live notifications when drivers pit, with lap and duration info
- **Track Status** — Flag changes (Safety Car, Yellow, Red) displayed in real time
- **Lap Counter & Timer** — Follow the race progress lap by lap
- **Team Colours** — Each car rendered in official 2024 team livery colours
- **Chunked Data Loading** — Efficient memory management for 673,000+ GPS data points
- **Dockerized** — One command to build and run, no setup headaches

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **Python 3.11** | Core language |
| **Dash / Plotly** | Interactive web dashboard & data visualization |
| **FastF1** | Official F1 telemetry & session data |
| **Pandas / NumPy** | Data processing & manipulation |
| **SciPy** | Cubic spline interpolation for smooth car movement |
| **Docker** | Containerized deployment |

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
docker build -t f1-replay .
docker run -p 8050:8050 f1-replay
```

Then open **http://127.0.0.1:8050** in your browser.

### Option 2: Run Locally

```bash
# Clone the repo
git clone https://github.com/Sminkid/f1-race-predictor.git
cd f1-race-predictor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download race data
python src/setup_data.py

# Launch the dashboard
python src/dashboard.py
```

Then open **http://127.0.0.1:8050** in your browser.

---

## 📁 Project Structure

```
f1-race-predictor/
├── src/
│   ├── setup_data.py      # Downloads & processes F1 telemetry data
│   └── dashboard.py        # Dash app — track map, controls, sidebar
├── data/                    # Generated race data (created at runtime)
├── Dockerfile               # Container build instructions
├── .dockerignore            # Keeps Docker image clean
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 📊 How It Works

1. **Data Collection** — `setup_data.py` fetches GPS position data for all 20 drivers from the FastF1 API (~673,000 data points)
2. **Interpolation** — Cubic spline interpolation smooths raw GPS data to 10Hz for fluid car movement
3. **Chunked Loading** — The race is loaded in 5-minute chunks to keep memory usage low
4. **Live Rendering** — Dash callbacks update car positions every 50ms using Plotly Patch updates for performance
5. **Track Extraction** — A single clean lap from Verstappen is used to draw the circuit outline

---

## 🏁 Race Data

- **Race:** Monaco Grand Prix 2024
- **Date:** 26 May 2024
- **Laps:** 78
- **Drivers:** 20
- **Data Points:** 673,740 GPS position updates

---

## 📌 Future Improvements

- [ ] Deploy to cloud (Render / Railway) for a public URL
- [ ] Add driver selection / highlighting
- [ ] Leaderboard with live position tracking
- [ ] Speed telemetry overlay
- [ ] Support for other races / seasons

---

## 👤 Author

Built by **[@Sminkid](https://github.com/Sminkid)** — because I love F1 that much. 🏎️