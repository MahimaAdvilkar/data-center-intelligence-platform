import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.config import RF_MODEL_PATH, SCALER_PATH, DC_CLUSTERED_CSV

router = APIRouter(prefix="/cluster", tags=["Cluster Prediction"])

FEATURE_COLS = [
    "ENERGY", "AREA", "IT EQUIPMENT POWER", "State_Aggregated_PUE",
    "FULL_CABINETS", "PARTIAL_CABINETS", "SHARED_RACKSPACE", "CAGES",
    "SUITES", "BUILD_TO_SUIT", "FOOTPRINTS", "REMOTE_HANDS",
    "YEAR_OPERATIONAL", "State_Aggregated_IXP_Count",
]

CLUSTER_LABELS = {
    0: "Hyperscale",
    1: "Mid-Tier",
    2: "Edge / Colo",
}


def _load_models():
    rf = joblib.load(RF_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return rf, scaler


class FeaturesWrapper(BaseModel):
    """Accepts {features: {ENERGY_CAPACITY_MW, PUE, TOTAL_AREA_SQFT,
    IXP_COUNT, YEAR_OPERATIONAL, SERVICE_SCORE}} from the React frontend."""
    features: dict


@router.post("/predict")
def predict_cluster(data: FeaturesWrapper):
    rf, scaler = _load_models()
    f = data.features

    energy_mw   = float(f.get("ENERGY_CAPACITY_MW", 50))
    pue         = float(f.get("PUE", 1.5))
    area_sqft   = float(f.get("TOTAL_AREA_SQFT", 100_000))
    ixp_count   = float(f.get("IXP_COUNT", 5))
    year_op     = int(f.get("YEAR_OPERATIONAL", 2015))
    svc_score   = int(f.get("SERVICE_SCORE", 4))

    # Distribute service score evenly across boolean service columns
    svc_flags = [1 if i < svc_score else 0 for i in range(8)]

    input_df = pd.DataFrame([{
        "ENERGY":                    energy_mw,
        "AREA":                      area_sqft,
        "IT EQUIPMENT POWER":        energy_mw * 0.7,
        "State_Aggregated_PUE":      pue,
        "FULL_CABINETS":             svc_flags[0],
        "PARTIAL_CABINETS":          svc_flags[1],
        "SHARED_RACKSPACE":          svc_flags[2],
        "CAGES":                     svc_flags[3],
        "SUITES":                    svc_flags[4],
        "BUILD_TO_SUIT":             svc_flags[5],
        "FOOTPRINTS":                svc_flags[6],
        "REMOTE_HANDS":              svc_flags[7],
        "YEAR_OPERATIONAL":          year_op,
        "State_Aggregated_IXP_Count": ixp_count,
    }])

    scaled = scaler.transform(input_df)
    cluster_id   = int(rf.predict(scaled)[0])
    probabilities = rf.predict_proba(scaled)[0]

    return {
        "cluster": cluster_id,
        "label": CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}"),
        "probabilities": {
            str(i): round(float(p), 4)
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
    summary = (
        df.groupby("Cluster")
        .agg(
            count=("LOCATION", "count"),
            avg_pue=("State_Aggregated_PUE", "mean"),
            avg_energy_mw=("ENERGY", "mean"),
            avg_area_sqft=("AREA", "mean"),
        )
        .reset_index()
        .round(3)
    )
    summary["label"] = summary["Cluster"].map(CLUSTER_LABELS)
    summary = summary.rename(columns={"Cluster": "cluster"})
    return {"clusters": summary.to_dict(orient="records")}
