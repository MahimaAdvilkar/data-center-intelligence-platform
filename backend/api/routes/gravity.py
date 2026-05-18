import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.config import GRAVITY_CSV

router = APIRouter(prefix="/gravity", tags=["Gravity Model"])

COST_PARAMS = ["Water", "Energy", "Workforce", "LandCost"]
BENEFIT_PARAMS = ["Renewable", "LandAvail", "Network", "Climate"]

DEFAULT_WEIGHTS = {
    "Water": 0.05,
    "Energy": 0.20,
    "Workforce": 0.05,
    "LandCost": 0.15,
    "Renewable": 0.10,
    "LandAvail": 0.05,
    "Network": 0.20,
    "Climate": 0.10,
}


def _load_and_score(weights: dict) -> pd.DataFrame:
    df = pd.read_csv(GRAVITY_CSV)
    for param, weight in weights.items():
        if param not in df.columns:
            continue
        min_val, max_val = df[param].min(), df[param].max()
        if max_val == min_val:
            df[param + "_norm"] = 0.0
        elif param in COST_PARAMS:
            df[param + "_norm"] = (max_val - df[param]) / (max_val - min_val)
        else:
            df[param + "_norm"] = (df[param] - min_val) / (max_val - min_val)

    df["Score"] = sum(df[p + "_norm"] * w for p, w in weights.items() if p + "_norm" in df.columns)
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)
    df["Rank"] = df.index + 1
    return df


class WeightsInput(BaseModel):
    Water: float = 0.05
    Energy: float = 0.20
    Workforce: float = 0.05
    LandCost: float = 0.15
    Renewable: float = 0.10
    LandAvail: float = 0.05
    Network: float = 0.20
    Climate: float = 0.10


@router.get("/cities")
def list_cities():
    df = pd.read_csv(GRAVITY_CSV)
    return {"cities": df["City"].tolist()}


@router.get("/scores")
def get_all_scores(top_n: int = 13):
    df = _load_and_score(DEFAULT_WEIGHTS)
    scores = [
        {"city": row["City"], "score": round(float(row["Score"]), 4), "rank": int(row["Rank"])}
        for _, row in df.head(top_n).iterrows()
    ]
    return {"scores": scores}


@router.get("/scores/{city_name}")
def get_city_score(city_name: str):
    df = _load_and_score(DEFAULT_WEIGHTS)
    row = df[df["City"].str.lower() == city_name.lower()]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"City '{city_name}' not found.")
    r = row.iloc[0]
    return {
        "city": r["City"],
        "rank": int(r["Rank"]),
        "score": round(float(r["Score"]), 4),
        "parameters": {
            p: round(float(r[p + "_norm"]), 4)
            for p in DEFAULT_WEIGHTS
            if p + "_norm" in r.index
        },
    }


@router.post("/scores/custom")
def get_scores_with_custom_weights(weights: WeightsInput):
    total = sum(weights.model_dump().values())
    if abs(total - 1.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Weights must sum to 1.0, got {total:.3f}")
    df = _load_and_score(weights.model_dump())
    scores = [
        {"city": row["City"], "score": round(float(row["Score"]), 4), "rank": int(row["Rank"])}
        for _, row in df.iterrows()
    ]
    return {"scores": scores}
