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


class OptimizationRequest(BaseModel):
    # Fields the React frontend sends
    capacity_mw: float = 50
    max_pue: float = 1.5
    min_area_sqft: int = 50_000
    generations: int = 50
    # Legacy fields kept for compatibility
    population_size: int = 50
    seed: int = 42


@router.post("/run")
def run_nsga2(req: OptimizationRequest):
    n_gen = max(1, min(req.generations, 200))
    n_pop = max(10, min(req.population_size, 200))

    df = _load_df()

    # Filter to user constraints
    filtered = df[
        (df["ENERGY"] >= req.capacity_mw * 0.5) &
        (df["State_Aggregated_PUE"] <= req.max_pue) &
        (df["AREA"] >= req.min_area_sqft)
    ]
    if len(filtered) < 5:
        filtered = df  # fall back to full dataset if constraints too tight

    pareto_front = _run_nsga2(filtered, n_pop, n_gen, req.seed)

    # Build pareto_front in the shape the React Optimizer page expects
    points = []
    seen = set()
    for ind in pareto_front:
        selected = filtered[[bool(x) for x in ind]]
        valid = selected[selected.apply(_is_valid, axis=1)]
        if valid.empty:
            continue
        key = (round(float(valid["State_Aggregated_PUE"].mean()), 3),
               round(float(valid["ENERGY"].mean()), 1))
        if key in seen:
            continue
        seen.add(key)
        points.append({
            "pue":       round(float(valid["State_Aggregated_PUE"].mean()), 3),
            "energy_mw": round(float(valid["ENERGY"].mean()), 1),
            "area_sqft": int(valid["AREA"].mean()),
        })

    if not points:
        raise HTTPException(status_code=500, detail="No valid Pareto solutions found.")

    # Best solution = lowest PUE in the front
    best = min(points, key=lambda x: x["pue"])

    return {
        "pareto_front": points,
        "best_solution": best,
        "generations": n_gen,
    }


@router.get("/data-centers")
def list_data_centers():
    df = _load_df()
    cols = ["LOCATION", "CITY", "STATE", "State_Aggregated_PUE",
            "State_Aggregated_IXP_Count", "SERVICE_AVAILABILITY_SCORE", "FACILITY_AGE"]
    return df[cols].rename(columns={
        "LOCATION": "location", "CITY": "city", "STATE": "state",
        "State_Aggregated_PUE": "pue", "State_Aggregated_IXP_Count": "ixp_count",
        "SERVICE_AVAILABILITY_SCORE": "service_score", "FACILITY_AGE": "facility_age",
    }).to_dict(orient="records")
