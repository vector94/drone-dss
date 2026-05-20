# DroneDSS — SAR Drone Selection Decision Support System

A Decision Support System for selecting the optimal drone for Search and Rescue (SAR) operations. Built for BTH course DV2573, Group 2, Spring 2026.

## What it does

Given a mission scenario (emergency type, weather, altitude, area, distance, budget), the system:
1. Filters drones using expert IF-THEN rules (wind resistance, altitude ceiling, range, payload, budget)
2. Scores remaining drones using a weighted decision matrix
3. Recommends the best drone and estimates deployment cost

## Setup

**Requirements:** Python 3.9+

1. Clone the repository:
   ```bash
   git clone https://github.com/vector94/DroneDSS.git
   cd DroneDSS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   cd src
   python3 -m streamlit run app.py
   ```

4. Open your browser at `http://localhost:8501`

## Project structure

```
DroneDSS/
├── src/
│   ├── app.py       # Streamlit UI
│   ├── engine.py    # Rule filtering + weighted scoring logic
│   └── drones.py    # Drone database
└── requirements.txt
```

## Course

**DV2573 — Decision Support Systems**  
Blekinge Institute of Technology (BTH) · Spring 2026 · Group 2
