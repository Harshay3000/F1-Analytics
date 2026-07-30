# 🏎️ F1 Post-Race Analytics Platform

An interactive Formula 1 analytics dashboard built with Python and Streamlit.
Pulls real telemetry, timing, and tyre data via the FastF1 library and presents
it through a suite of interactive Plotly charts — plus a Machine Learning layer
and an AI-powered race narrator.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit&logoColor=white)
![FastF1](https://img.shields.io/badge/FastF1-3.3+-orange)
![Plotly](https://img.shields.io/badge/Plotly-5.22+-purple)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-F7931E?logo=scikitlearn&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_AI-LLaMA_3-green)

---

## 📸 Pages & Features

### 🏠 Home
- Season, Grand Prix, and session selector
- Race summary stats — total laps, pit stops, fastest lap
- Full finishing order table

### 🏁 Race Overview
- Lap time comparison — all drivers, team colors, interactive legend
- Position changes bump chart — every overtake visible lap by lap
- Fastest lap table with gap to leader
- Positions gained/lost per driver

### 🔴 Tyre Strategy
- Horizontal stint timeline for every driver ordered by finishing position
- Filter by driver or compound
- Detailed stint breakdown table with lap counts and tyre age
- Strategy summary statistics

### ⚡ Driver Comparison
- Head-to-head telemetry — Speed, Throttle, Brake on the same axis
- Laps aligned by distance so any corner can be compared directly
- Sector time breakdown table
- Works for Qualifying and Race sessions

### 🗺️ Circuit Map
- GPS-based circuit layout drawn from real telemetry X/Y coordinates
- Color the racing line by Speed, Throttle, or Brake
- Overlay a second driver for direct line comparison

### 📉 Gap to Leader & Race Pace
- Classic F1 broadcast gap chart — cumulative time gap to leader per lap
- Pit stops visible as spikes; closing the gap shows as downward slope
- Race pace box plot — median, consistency, and outliers per driver
- Final gap to winner table

### 🏆 Driver Performance Rating
- Composite 0–100 rating built from 6 signals:
  Finishing position, Positions gained, Race pace, Consistency, Qualifying, Teammate delta
- Interactive weight sliders — change how much each signal contributes
- Ranked bar chart, radar/spider comparison chart, score heatmap
- CSV download of full ratings table

### 📈 Tyre Degradation Predictor *(ML)*
- Random Forest regression model trained on real race lap data
- Predicts lap time at any tyre age for any compound
- Degradation rate (seconds/lap) per compound via linear regression
- Live prediction tool — enter compound + tyre age → predicted lap time
- Per-driver degradation comparison — shows tyre management differences
- Model evaluation: cross-validated MAE and R² score

### 🔧 Pit Stop Strategy Optimizer *(ML)*
- Brute-force strategy simulator using the degradation model as input
- Evaluates all 1-stop and 2-stop strategies across every pit lap and compound combo
- Finds the optimal pit window and compound sequence
- Pit window sensitivity chart — shows how flexible the window is
- Compares actual driver strategy vs model-optimal with time delta

### 🤖 AI Race Narrator *(LLM)*
- Extracts structured race facts and sends them to an LLM via Groq API
- Four narrative modes: Race Report, Strategy Analysis, Driver of the Day, Custom Question
- Three tone options: Journalist, Technical, Enthusiast
- Streams output word by word in real time
- Model selector: LLaMA 3.3 70B, LLaMA 3.1 8B, Mixtral 8x7B, Gemma2 9B
- Download narrative as a text file

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Dashboard | Streamlit |
| Charts | Plotly |
| F1 Data | FastF1 + Jolpica-F1 API |
| Data processing | Pandas, NumPy |
| Machine Learning | scikit-learn (Random Forest, Linear Regression) |
| AI Narrator | Groq API (LLaMA 3 / Mixtral) |

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

### 4. Add your Groq API key *(for AI Narrator page)*
Create a file at `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "gsk_your-key-here"
```
Get a free key at [console.groq.com](https://console.groq.com)

> The rest of the app works without an API key.
> The AI Narrator page will prompt you to enter one if not configured.

### 5. Run the app
```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

> **First load:** FastF1 downloads race data from F1's servers (~30 seconds per session).
> After the first load, data is cached locally in the `cache/` folder and loads instantly.

---

## 📁 Project structure

```
f1-analytics/
│
├── app.py                        ← Entry point, sidebar, home page
├── requirements.txt
├── .gitignore
│
├── pages/
│   ├── 01_race_overview.py       ← Lap times + position changes
│   ├── 02_tyre_strategy.py       ← Tyre stint visualization
│   ├── 03_driver_comparison.py   ← Head-to-head telemetry
│   ├── 04_circuit_map.py         ← GPS racing line map
│   ├── 05_gap_and_pace.py        ← Gap to leader + race pace
│   ├── 06_driver_rating.py       ← Composite performance rating
│   ├── 07_tyre_degradation.py    ← ML tyre degradation predictor
│   ├── 08_pit_strategy.py        ← ML pit stop optimizer
│   └── 09_ai_narrator.py         ← AI race narrative generator
│
├── utils/
│   ├── data_loader.py            ← FastF1 fetching, ML models, derive functions
│   └── chart_helpers.py          ← Reusable Plotly chart functions
│
└── .streamlit/
    └── secrets.toml              ← API keys (not uploaded to GitHub)
```

---

## 📊 Data sources

- **[FastF1](https://github.com/theOehrly/Fast-F1)** — Python library for F1 telemetry, lap times, and tyre data (2018–present)
- **[Jolpica-F1 API](https://github.com/jolpica/jolpica-f1)** — Successor to the Ergast API, historical F1 results back to 1950

Race data is available approximately 1 hour after each session ends.

---

## 🤖 ML Models

### Tyre Degradation — Random Forest Regressor
- **Target:** Lap time in seconds
- **Features:** Tyre age (laps), compound encoding, fuel load proxy (lap number)
- **Training data:** All clean, accurate laps from the selected race
- **Evaluation:** 5-fold cross-validated MAE (reported in milliseconds)
- **Also outputs:** Linear degradation rate per compound (seconds/lap) for interpretability

### Pit Stop Optimizer — Brute Force + RF
- Uses the trained degradation model to predict total race time for every possible strategy
- Pre-computes all lap time predictions in a single batch call (vectorized) for speed
- Evaluates all 1-stop and 2-stop combinations across every pit lap and compound sequence
- Returns strategies ranked by predicted total race time

---

## ☁️ Deploy to Streamlit Cloud (free)

1. Push this repo to GitHub (make sure `cache/` and `.streamlit/secrets.toml` are in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account → New app → select this repo
4. Main file path: `app.py`
5. Go to **App settings → Secrets** and add:
```toml
GROQ_API_KEY = "gsk_your-key-here"
```
6. Click **Deploy** — public URL in ~3-5 minutes

> Note: Streamlit Cloud doesn't persist the `cache/` folder between deploys,
> so the first load of each race will take ~30 seconds. This is expected behaviour.

---

## 👤 Author

Built by **Harshay Chouhan**
- GitHub: [@Harshay3000](https://github.com/Harshay3000)

---

## 📄 License

MIT License — free to use, modify, and share.
