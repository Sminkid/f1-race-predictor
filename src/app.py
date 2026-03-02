import streamlit as st
import fastf1
import fastf1.plotting
import pandas as pd
import matplotlib.pyplot as plt

# Enable cache
fastf1.Cache.enable_cache('data/cache')

# Page config
st.set_page_config(page_title="F1 Race Dashboard", page_icon="🏎️", layout="wide")

# Title
st.title("🏎️ F1 Race Dashboard")
st.markdown("Explore real Formula 1 race data!")

# Sidebar - let user pick a race
st.sidebar.header("Select a Race")
year = st.sidebar.selectbox("Year", [2025, 2024, 2023, 2022])
race = st.sidebar.selectbox("Race", [
    # Early Season
    "Australia", "China", "Japan", "Bahrain", "Saudi Arabia",
    # Europe
    "Monaco", "Spain", "Canada", "Austria", "Silverstone",
    "Belgium", "Hungary", "Netherlands", "Monza",
    # Americas & Asia
    "Miami", "United States", "Las Vegas",
    "Mexico City", "São Paulo",
    # Middle East & End
    "Azerbaijan", "Singapore", "Qatar", "Abu Dhabi"
])

# Load button
if st.sidebar.button("Load Race Data"):
    with st.spinner("Loading race data... this may take a moment ⏳"):
        
        # Load session
        session = fastf1.get_session(year, race, 'R')
        session.load()
        laps = session.laps

        # --- Section 1: Fastest Laps ---
        st.subheader("⚡ Fastest Lap Per Driver")
        fastest = laps.groupby('Driver')['LapTime'].min().dropna()
        fastest_seconds = fastest.dt.total_seconds().sort_values()
        
        fig1, ax1 = plt.subplots(figsize=(12, 5))
        ax1.barh(fastest_seconds.index, fastest_seconds.values, color='red')
        ax1.set_xlabel("Lap Time (seconds)")
        ax1.set_title(f"Fastest Lap Per Driver - {race} {year}")
        ax1.invert_yaxis()
        st.pyplot(fig1)

        # --- Section 2: Lap Time Over Race ---
        st.subheader("📈 Lap Times Over the Race")
        drivers = laps['Driver'].unique()[:5]  # Top 5 drivers to keep it clean
        
        fig2, ax2 = plt.subplots(figsize=(12, 5))
        for driver in drivers:
            driver_laps = laps[laps['Driver'] == driver][['LapNumber', 'LapTime']].dropna()
            driver_laps['LapTime_sec'] = driver_laps['LapTime'].dt.total_seconds()
            ax2.plot(driver_laps['LapNumber'], driver_laps['LapTime_sec'], label=driver)
        
        ax2.set_xlabel("Lap Number")
        ax2.set_ylabel("Lap Time (seconds)")
        ax2.set_title(f"Lap Times During Race - {race} {year}")
        ax2.legend()
        st.pyplot(fig2)

        # --- Section 3: Tyre Strategy ---
        st.subheader("🏁 Tyre Strategy")
        strategy = laps[['Driver', 'Compound', 'LapNumber']].dropna()
        
        fig3, ax3 = plt.subplots(figsize=(12, 6))
        compounds = strategy['Compound'].unique()
        colours = {'SOFT': 'red', 'MEDIUM': 'yellow', 'HARD': 'white', 'INTER': 'green', 'WET': 'blue'}
        
        for driver in strategy['Driver'].unique():
            d = strategy[strategy['Driver'] == driver]
            for compound in d['Compound'].unique():
                c = d[d['Compound'] == compound]
                ax3.scatter(c['LapNumber'], [driver]*len(c), 
                          color=colours.get(compound, 'grey'), s=50, label=compound)
        
        ax3.set_xlabel("Lap Number")
        ax3.set_title(f"Tyre Strategy - {race} {year}")
        ax3.set_facecolor('black')
        fig3.patch.set_facecolor('black')
        ax3.tick_params(colors='white')
        ax3.xaxis.label.set_color('white')
        ax3.title.set_color('white')
        st.pyplot(fig3)

        # --- Section 4: Raw Data ---
        st.subheader("📊 Raw Lap Data")
        st.dataframe(laps[['Driver', 'LapNumber', 'LapTime', 'Compound', 'PitInTime']].head(50))