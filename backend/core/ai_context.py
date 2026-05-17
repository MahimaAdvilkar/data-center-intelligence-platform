"""
Data context functions used as Claude tool implementations.
Each function returns a structured dict that Claude can reason over.
"""
import pandas as pd
from backend.core.config import DC_CLUSTERED_CSV, GRAVITY_CSV, DC_CLEANED_CSV

COST_PARAMS    = ["Water", "Energy", "Workforce", "LandCost"]
BENEFIT_PARAMS = ["Renewable", "LandAvail", "Network", "Climate"]

DEFAULT_WEIGHTS = {
    "Water": 0.05, "Energy": 0.20, "Workforce": 0.05, "LandCost": 0.15,
    "Renewable": 0.10, "LandAvail": 0.05, "Network": 0.20, "Climate": 0.10,
}

CLUSTER_LABELS = {
    0: "Hyperscale / High-Capacity",
    1: "Mid-Tier / Regional",
    2: "Edge / Colocation",
}


def get_gravity_scores(top_n: int = 13) -> dict:
    """Return ranked city scores from the gravity model."""
    df = pd.read_csv(GRAVITY_CSV)
    for param, weight in DEFAULT_WEIGHTS.items():
        mn, mx = df[param].min(), df[param].max()
        if mx == mn:
            df[param + "_norm"] = 0.0
        elif param in COST_PARAMS:
            df[param + "_norm"] = (mx - df[param]) / (mx - mn)
        else:
            df[param + "_norm"] = (df[param] - mn) / (mx - mn)
    df["Score"] = sum(df[p + "_norm"] * w for p, w in DEFAULT_WEIGHTS.items())
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)
    df["Rank"] = df.index + 1

    results = []
    for _, row in df.head(top_n).iterrows():
        results.append({
            "rank":      int(row["Rank"]),
            "city":      row["City"],
            "score":     round(float(row["Score"]), 4),
            "energy_cost_inr_kwh":    row["Energy"],
            "network_index":          row["Network"],
            "renewable_pct":          row["Renewable"],
            "land_cost_inr_sqft":     row["LandCost"],
            "climate_resilience":     row["Climate"],
            "workforce_cost_inr_pa":  row["Workforce"],
        })
    return {"rankings": results, "weights_used": DEFAULT_WEIGHTS}


def get_cluster_summary() -> dict:
    """Return summary statistics for each data center cluster."""
    df = pd.read_csv(DC_CLUSTERED_CSV)
    bool_cols = ["FULL_CABINETS","PARTIAL_CABINETS","SHARED_RACKSPACE","CAGES",
                 "SUITES","BUILD_TO_SUIT","FOOTPRINTS","REMOTE_HANDS"]
    for col in bool_cols:
        df[col] = df[col].astype(str).str.lower().map(
            {"true": 1, "false": 0, "yes": 1, "no": 0, "1": 1, "0": 0}
        ).fillna(0)

    summary = []
    for cluster_id in sorted(df["Cluster"].unique()):
        sub = df[df["Cluster"] == cluster_id]
        summary.append({
            "cluster_id":    int(cluster_id),
            "label":         CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}"),
            "count":         len(sub),
            "avg_energy_mw": round(sub["ENERGY"].mean(), 2),
            "avg_area_sqft": int(sub["AREA"].mean()),
            "avg_pue":       round(sub["State_Aggregated_PUE"].mean(), 3),
            "avg_ixp_count": round(sub["State_Aggregated_IXP_Count"].mean(), 1),
            "avg_year_built": int(sub["YEAR_OPERATIONAL"].mean()),
            "top_states":    sub["STATE"].value_counts().head(3).index.tolist(),
            "service_score_avg": round(
                sub[bool_cols].sum(axis=1).mean(), 1
            ),
        })
    return {
        "clusters": summary,
        "total_records": len(df),
        "states_covered": sorted(df["STATE"].unique().tolist()),
        "model_accuracy": "95% on held-out test set (203 records, 3-class RF classifier)",
    }


def get_dataset_overview() -> dict:
    """Return high-level dataset statistics."""
    df = pd.read_csv(DC_CLEANED_CSV)
    return {
        "total_data_centers": len(df),
        "states_covered":     sorted(df["STATE"].unique().tolist()),
        "state_count":        df["STATE"].nunique(),
        "avg_energy_mw":      round(df["ENERGY"].mean(), 2),
        "max_energy_mw":      round(df["ENERGY"].max(), 2),
        "avg_area_sqft":      int(df["AREA"].mean()),
        "year_range":         f"{int(df['YEAR_OPERATIONAL'].min())}–{int(df['YEAR_OPERATIONAL'].max())}",
        "data_sources":       [
            "datacentermap.com (web scraper — Playwright)",
            "Operator benchmark specs (Equinix, CyrusOne, DataBank, etc. annual reports)",
            "Lawrence Berkeley National Lab 2024 — PUE estimates",
            "PeeringDB — IXP counts",
        ],
    }


def get_top_data_centers(metric: str = "pue", top_n: int = 10) -> dict:
    """Return top data centers by a given metric."""
    df = pd.read_csv(DC_CLUSTERED_CSV)
    valid_metrics = {
        "pue":      ("State_Aggregated_PUE", True),   # ascending = better
        "energy":   ("ENERGY", False),
        "area":     ("AREA", False),
        "ixp":      ("State_Aggregated_IXP_Count", False),
        "newest":   ("YEAR_OPERATIONAL", False),
    }
    if metric not in valid_metrics:
        return {"error": f"Unknown metric '{metric}'. Valid: {list(valid_metrics)}"}

    col, ascending = valid_metrics[metric]
    top = df.nsmallest(top_n, col) if ascending else df.nlargest(top_n, col)

    return {
        "metric": metric,
        "results": top[["LOCATION","CITY","STATE","ENERGY","AREA",
                        "State_Aggregated_PUE","State_Aggregated_IXP_Count",
                        "YEAR_OPERATIONAL","Cluster"]].rename(columns={
            "State_Aggregated_PUE": "pue",
            "State_Aggregated_IXP_Count": "ixp_count",
            "YEAR_OPERATIONAL": "year",
        }).to_dict(orient="records"),
    }


def get_city_detail(city_name: str) -> dict:
    """Return full parameter breakdown for a specific Indian city."""
    df = pd.read_csv(GRAVITY_CSV)
    row = df[df["City"].str.lower() == city_name.lower()]
    if row.empty:
        return {"error": f"City '{city_name}' not found. Available: {df['City'].tolist()}"}
    r = row.iloc[0]
    return {
        "city":              r["City"],
        "energy_cost":       f"₹{r['Energy']}/kWh",
        "water_cost":        f"₹{r['Water']}/1000L",
        "workforce_salary":  f"₹{int(r['Workforce']):,}/year",
        "renewable_pct":     f"{r['Renewable']}%",
        "land_cost":         f"₹{r['LandCost']}/sqft",
        "land_availability": f"{r['LandAvail']}/10",
        "network_index":     f"{r['Network']}/10",
        "climate_resilience":f"{r['Climate']}/10",
        "sources":           r.get("Sources", "See project documentation"),
    }
