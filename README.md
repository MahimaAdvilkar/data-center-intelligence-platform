# Data Center Intelligence Platform

An AI-powered platform for data center site selection, multi-objective optimization, and tier classification — built as a scaled-up version of a capstone research project.

## What This Is

This project extends a capstone analysis of US and Indian data center infrastructure into a production-grade intelligence platform. It combines machine learning, evolutionary optimization, and a multi-page interactive dashboard.

## Features

| Module | Description |
|---|---|
| **Gravity Model** | Ranks 13 Indian cities for data center siting using 8 weighted infrastructure parameters |
| **NSGA-II Optimizer** | Pareto-optimal multi-objective optimization across PUE, IXP connectivity, service score, and facility age |
| **Cluster Predictor** | Random Forest classifier that predicts the tier (Hyperscale / Mid-Tier / Edge) of a new data center |
| **FastAPI Backend** | REST API exposing all three models as endpoints |
| **Streamlit Dashboard** | 5-page interactive UI for exploring all models and data |

## Repository Structure

```
data-center-intelligence-platform/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   └── routes/
│   │       ├── gravity.py       # /gravity/* endpoints
│   │       ├── optimization.py  # /optimization/* endpoints
│   │       └── cluster.py       # /cluster/* endpoints
│   ├── core/
│   │   └── config.py            # Path config
│   ├── data/                    # All CSVs
│   └── models/                  # Trained pkl files
├── frontend/
│   └── streamlit_app.py         # 5-page dashboard
├── scrapers/                    # Data collection scripts
├── notebooks/                   # Reference EDA notebooks
├── requirements.txt
└── README.md
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn backend.api.main:app --reload

# Run the dashboard (in a separate terminal)
streamlit run frontend/streamlit_app.py
```

API docs available at: `http://localhost:8000/docs`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/gravity/scores` | All city scores with default weights |
| `GET` | `/gravity/scores/{city}` | Single city score + component breakdown |
| `POST` | `/gravity/scores/custom` | Custom weight scoring |
| `POST` | `/optimization/run` | Run NSGA-II optimization |
| `GET` | `/optimization/data-centers` | List all data centers |
| `POST` | `/cluster/predict` | Predict cluster for new data center |
| `GET` | `/cluster/summary` | Cluster statistics summary |

## Models

### Gravity Model
Weighted attraction scoring across 8 parameters for 13 Indian cities:
- **Cost factors** (lower = better): Water, Energy, Workforce, Land Cost
- **Benefit factors** (higher = better): Renewable %, Land Availability, Network, Climate

### NSGA-II Multi-Objective Optimizer
Evolutionary algorithm finding Pareto-optimal US data center selections:
- Minimize: PUE (energy efficiency) + Facility Age
- Maximize: IXP Count (connectivity) + Service Availability Score

### Random Forest Classifier
Trained on 39 US data centers, predicts one of three tiers:
- **Cluster 0**: Hyperscale / High-Capacity
- **Cluster 1**: Mid-Tier / Regional
- **Cluster 2**: Edge / Colocation

## Data Sources

- US data centers: [datacentermap.com](https://www.datacentermap.com)
- Indian city parameters: [brightlio.com](https://www.brightlio.com) + manual research
- States covered: FL, ID, NY, WA, VA, CA

## Roadmap

- [ ] Phase 2: AI chat layer (Claude API) for natural language Q&A
- [ ] Phase 2: Demand forecasting with time-series models
- [ ] Phase 3: Agentic workflows (Site Scout Agent, Market Monitor Agent)
- [ ] Phase 4: React + TypeScript frontend
- [ ] Phase 5: Cloud deployment (Vercel + Railway)

## Built On

Original capstone: [Data Center Infrastructure Expansion Capstone Project](https://github.com/MahimaAdvilkar/Data_Center_Infrastructure_Expansion_Capstone_Project)
