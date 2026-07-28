# 🏎️ F1 Post-Race Analytics Platform

An interactive Formula 1 analytics dashboard built with Python and Streamlit.
Fetches real telemetry and timing data via the FastF1 library and visualizes
it through a suite of interactive Plotly charts.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit&logoColor=white)
![FastF1](https://img.shields.io/badge/FastF1-3.3+-orange)
![Plotly](https://img.shields.io/badge/Plotly-5.22+-purple?logo=plotly&logoColor=white)

---

## 📸 Features

### 🏁 Race Overview
- Lap time comparison across all drivers with team colors
- Position changes bump chart — see every overtake lap by lap
- Fastest lap table with gap to leader
- Positions gained/lost per driver

### 🔴 Tyre Strategy
- Visual stint timeline for every driver ordered by finishing position
- Filter by driver or compound
- Detailed stint breakdown table with lap counts
- Strategy summary statistics

### ⚡ Driver Comparison
- Head-to-head telemetry on fastest laps — Speed, Throttle, Brake
- Laps aligned by distance so any corner can be compared directly
- Sector time breakdown
- Works for both Qualifying and Race sessions

### 🗺️ Circuit Map
- GPS-based circuit layout from real telemetry coordinates
- Color the racing line by Speed, Throttle, or Brake
- Overlay a second driver's line for direct comparison

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Dashboard | Streamlit |
| Charts | Plotly |
| F1 Data | FastF1 + Jolpica-F1 API |
| Data processing | Pandas, NumPy |

---

## 🚀 Run locally

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/f1-analytics.git
cd f1-analytics
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

> **First load:** FastF1 downloads race data from F1's servers (~30 seconds).
> Subsequent loads are instant from the local `cache/` folder.

---

## 📁 Project structure

```
f1-analytics/
│
├── app.py                       ← Entry point, sidebar, home page
├── requirements.txt
├── .gitignore
│
├── pages/
│   ├── 01_race_overview.py      ← Lap times + position changes
│   ├── 02_tyre_strategy.py      ← Tyre stint visualization
│   ├── 03_driver_comparison.py  ← Head-to-head telemetry
│   └── 04_circuit_map.py        ← GPS racing line map
│
└── utils/
    ├── data_loader.py            ← FastF1 data fetching + derive functions
    └── chart_helpers.py          ← Reusable Plotly chart functions
```

---

## 📊 Data source

All data is sourced from:
- **[FastF1](https://github.com/theOehrly/Fast-F1)** — Python library for F1 telemetry, lap times, and tyre data (2018–present)
- **[Jolpica-F1 API](https://github.com/jolpica/jolpica-f1)** — Successor to the Ergast API, historical F1 results back to 1950

Data is available approximately 1 hour after each race session ends.

---

## 🗺️ Roadmap

- [x] Phase 1 — Static charts (matplotlib)
- [x] Phase 2 — Interactive Streamlit dashboard
- [ ] Gap to leader & race pace chart
- [ ] Driver performance rating system
- [ ] Tyre degradation ML predictor
- [ ] Pit stop strategy optimizer
- [ ] AI race narrator (LLM integration)

---

## 👤 Author

Built by **[Your Name]**
- GitHub: [@your_username](https://github.com/your_username)
- LinkedIn: [your-linkedin](https://linkedin.com/in/your-linkedin)

---

## 📄 License

MIT License — free to use and modify.
