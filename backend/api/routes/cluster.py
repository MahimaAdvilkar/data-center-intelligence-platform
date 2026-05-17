import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.core.config import RF_MODEL_PATH, SCALER_PATH, DC_CLUSTERED_CSV

router = APIRouter(prefix="/cluster", tags=["Cluster Prediction"])

FEATURE_COLS = [
    "ENERGY", "AREA", "IT EQUIPMENT POWER", "State_Aggregated_PUE",
    "FULL_CABINETS", "PARTIAL_CABINETS", "SHARED_RACKSPACE", "CAGES",
    "SUITES", "BUILD_TO_SUIT", "FOOTPRINTS", "REMOTE_HANDS",
    "YEAR_OPERATIONAL", "State_Aggregated_IXP_Count",
]

CLUSTER_LABELS = {
    0: "Hyperscale / High-Capacity",
    1: "Mid-Tier / Regional",
    2: "Edge / Colocation",
}


def _load_models():
    rf = joblib.load(RF_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return rf, scaler


class ClusterInput(BaseModel):
    energy_mw: float = Field(..., ge=0.1, le=500, description="Energy capacity in MW")
    area_sqft: int = Field(..., ge=1000, le=2000000, description="Facility area in sqft")
    it_power_mw: float = Field(..., ge=0.1, le=300, description="IT equipment power in MW")
    pue: float = Field(..., ge=1.0, le=4.0, description="Power Usage Effectiveness")
    year_operational: int = Field(..., ge=1980, le=2025, description="Year the facility became operational")
    ixp_count: float = Field(..., ge=0, le=20, description="Number of Internet Exchange Points")
    full_cabinets: bool = False
    partial_cabinets: bool = False
    shared_rackspace: bool = False
    cages: bool = False
    suites: bool = False
    build_to_suit: bool = False
    footprints: bool = False
    remote_hands: bool = False


@router.post("/predict")
def predict_cluster(data: ClusterInput):
    rf, scaler = _load_models()

    input_df = pd.DataFrame([{
        "ENERGY": data.energy_mw,
        "AREA": data.area_sqft,
        "IT EQUIPMENT POWER": data.it_power_mw,
        "State_Aggregated_PUE": data.pue,
        "FULL_CABINETS": int(data.full_cabinets),
        "PARTIAL_CABINETS": int(data.partial_cabinets),
        "SHARED_RACKSPACE": int(data.shared_rackspace),
        "CAGES": int(data.cages),
        "SUITES": int(data.suites),
        "BUILD_TO_SUIT": int(data.build_to_suit),
        "FOOTPRINTS": int(data.footprints),
        "REMOTE_HANDS": int(data.remote_hands),
        "YEAR_OPERATIONAL": data.year_operational,
        "State_Aggregated_IXP_Count": data.ixp_count,
    }])

    scaled = scaler.transform(input_df)
    cluster_id = int(rf.predict(scaled)[0])
    probabilities = rf.predict_proba(scaled)[0]
    confidence = round(float(probabilities[cluster_id]), 4)

    return {
        "cluster_id": cluster_id,
        "cluster_label": CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}"),
        "confidence": confidence,
        "all_probabilities": {
            CLUSTER_LABELS.get(i, f"Cluster {i}"): round(float(p), 4)
            for i, p in enumerate(probabilities)
        },
    }


@router.get("/dataset")
def get_clustered_dataset():
    df = pd.read_csv(DC_CLUSTERED_CSV)
    return df.to_dict(orient="records")


@router.get("/summary")
def cluster_summary():
    df = pd.read_csv(DC_CLUSTERED_CSV)
    summary = df.groupby("Cluster").agg(
        count=("LOCATION", "count"),
        avg_pue=("State_Aggregated_PUE", "mean"),
        avg_energy=("ENERGY", "mean"),
        avg_area=("AREA", "mean"),
    ).reset_index().round(3)
    summary["label"] = summary["Cluster"].map(CLUSTER_LABELS)
    return summary.to_dict(orient="records")
