import random
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from deap import base, creator, tools, algorithms
from backend.core.config import DC_FINAL_CSV

router = APIRouter(prefix="/optimization", tags=["NSGA-II Optimization"])

SERVICE_COLS = [
    "FULL_CABINETS", "PARTIAL_CABINETS", "SHARED_RACKSPACE", "CAGES",
    "SUITES", "BUILD_TO_SUIT", "FOOTPRINTS", "REMOTE_HANDS",
]

# DEAP requires global creator setup — guard against duplicate registration
if not hasattr(creator, "FitnessMulti"):
    creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0, -1.0, -1.0))
if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMulti)


def _load_df() -> pd.DataFrame:
    df = pd.read_csv(DC_FINAL_CSV)
    df["SERVICE_AVAILABILITY_SCORE"] = df[SERVICE_COLS].astype(int).sum(axis=1)
    df["FACILITY_AGE"] = 2025 - df["YEAR_OPERATIONAL"]
    return df


def _is_valid(row) -> bool:
    return (
        row["IT EQUIPMENT POWER"] >= 1
        and row["AREA"] >= 10000
        and row["SERVICE_AVAILABILITY_SCORE"] >= 4
    )


def _run_nsga2(df: pd.DataFrame, n_pop: int, n_gen: int, seed: int):
    random.seed(seed)
    N = len(df)

    toolbox = base.Toolbox()
    toolbox.register("attr_bool", random.randint, 0, 1)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_bool, N)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    def evaluate(ind):
        selected = df[[bool(x) for x in ind]]
        valid = selected[selected.apply(_is_valid, axis=1)]
        if valid.empty:
            return (99999.0,) * 4
        return (
            valid["State_Aggregated_PUE"].sum(),
            -valid["State_Aggregated_IXP_Count"].sum(),
            -valid["SERVICE_AVAILABILITY_SCORE"].sum(),
            valid["FACILITY_AGE"].mean(),
        )

    toolbox.register("evaluate", evaluate)
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutFlipBit, indpb=0.05)
    toolbox.register("select", tools.selNSGA2)

    pop = toolbox.population(n=n_pop)
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)
    for _ in range(n_gen):
        offspring = algorithms.varAnd(pop, toolbox, cxpb=0.7, mutpb=0.2)
        for ind in offspring:
            ind.fitness.values = toolbox.evaluate(ind)
        pop = toolbox.select(pop + offspring, k=n_pop)

    return tools.sortNondominated(pop, len(pop), first_front_only=True)[0]


def _normalize(series: pd.Series) -> pd.Series:
    rng = series.max() - series.min()
    return (series - series.min()) / rng if rng != 0 else pd.Series([0.5] * len(series))


class OptimizationRequest(BaseModel):
    n_generations: int = 50
    population_size: int = 50
    seed: int = 42
    weights: Optional[dict] = None


@router.post("/run")
def run_nsga2(req: OptimizationRequest):
    if req.n_generations < 1 or req.n_generations > 200:
        raise HTTPException(status_code=400, detail="n_generations must be between 1 and 200.")
    if req.population_size < 10 or req.population_size > 200:
        raise HTTPException(status_code=400, detail="population_size must be between 10 and 200.")

    w = req.weights or {"PUE": 0.4, "IXP Count": 0.3, "Service Score": 0.2, "Facility Age": 0.1}

    df = _load_df()
    pareto_front = _run_nsga2(df, req.population_size, req.n_generations, req.seed)

    rows = []
    for i, ind in enumerate(pareto_front):
        selected = df[[bool(x) for x in ind]]
        for _, row in selected.iterrows():
            rows.append({
                "solution": i + 1,
                "location": row["LOCATION"],
                "city": row["CITY"],
                "state": row["STATE"],
                "pue": round(float(row["State_Aggregated_PUE"]), 3),
                "ixp_count": int(row["State_Aggregated_IXP_Count"]),
                "service_score": int(row["SERVICE_AVAILABILITY_SCORE"]),
                "facility_age": int(row["FACILITY_AGE"]),
            })

    if not rows:
        raise HTTPException(status_code=500, detail="No valid Pareto solutions found.")

    result_df = pd.DataFrame(rows)
    result_df["pue_norm"] = _normalize(result_df["pue"])
    result_df["ixp_norm"] = _normalize(result_df["ixp_count"])
    result_df["service_norm"] = _normalize(result_df["service_score"])
    result_df["age_norm"] = _normalize(result_df["facility_age"])

    result_df["weighted_score"] = (
        -result_df["pue_norm"] * w.get("PUE", 0.4)
        + result_df["ixp_norm"] * w.get("IXP Count", 0.3)
        + result_df["service_norm"] * w.get("Service Score", 0.2)
        - result_df["age_norm"] * w.get("Facility Age", 0.1)
    )

    result_df = result_df.sort_values("weighted_score", ascending=False).reset_index(drop=True)
    result_df["rank"] = result_df.index + 1

    output_cols = ["rank", "location", "city", "state", "pue", "ixp_count", "service_score", "facility_age", "weighted_score"]
    return {
        "pareto_solutions": len(pareto_front),
        "total_data_centers": len(result_df),
        "results": result_df[output_cols].round(4).to_dict(orient="records"),
    }


@router.get("/data-centers")
def list_data_centers():
    df = _load_df()
    cols = ["LOCATION", "CITY", "STATE", "State_Aggregated_PUE", "State_Aggregated_IXP_Count", "SERVICE_AVAILABILITY_SCORE", "FACILITY_AGE"]
    return df[cols].rename(columns={
        "LOCATION": "location", "CITY": "city", "STATE": "state",
        "State_Aggregated_PUE": "pue", "State_Aggregated_IXP_Count": "ixp_count",
        "SERVICE_AVAILABILITY_SCORE": "service_score", "FACILITY_AGE": "facility_age",
    }).to_dict(orient="records")
