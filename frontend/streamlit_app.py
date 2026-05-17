import sys
from pathlib import Path

# Make backend importable when running from the frontend folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import random
import plotly.express as px
import plotly.graph_objects as go
from deap import base, creator, tools, algorithms

from backend.core.config import (
    DC_CLUSTERED_CSV, DC_FINAL_CSV, GRAVITY_CSV, RF_MODEL_PATH, SCALER_PATH, DATA_DIR
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DC Intelligence Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar navigation ─────────────────────────────────────────────────────────
st.sidebar.title("Data Center Intelligence Platform")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Site Finder (Gravity Model)", "Optimizer (NSGA-II)", "Cluster Predictor", "Data Explorer", "Data Pipeline", "AI Analyst", "Site Scout Agent"],
)
st.sidebar.markdown("---")
st.sidebar.caption("Built on top of the Capstone Project | Phase 2 — AI Layer")


# ── Shared loaders ─────────────────────────────────────────────────────────────
@st.cache_data
def load_clustered():
    return pd.read_csv(DC_CLUSTERED_CSV)

@st.cache_data
def load_final():
    df = pd.read_csv(DC_FINAL_CSV)
    service_cols = ["FULL_CABINETS","PARTIAL_CABINETS","SHARED_RACKSPACE","CAGES",
                    "SUITES","BUILD_TO_SUIT","FOOTPRINTS","REMOTE_HANDS"]
    df["SERVICE_SCORE"] = df[service_cols].astype(int).sum(axis=1)
    df["FACILITY_AGE"] = 2025 - df["YEAR_OPERATIONAL"]
    return df

@st.cache_data
def load_gravity():
    return pd.read_csv(GRAVITY_CSV)

@st.cache_resource
def load_ml_models():
    rf = joblib.load(RF_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return rf, scaler


COST_PARAMS = ["Water", "Energy", "Workforce", "LandCost"]
BENEFIT_PARAMS = ["Renewable", "LandAvail", "Network", "Climate"]
CLUSTER_LABELS = {0: "Hyperscale / High-Capacity", 1: "Mid-Tier / Regional", 2: "Edge / Colocation"}


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Overview
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Data Center Intelligence Platform")
    st.markdown("An AI-powered platform for data center site selection, optimization, and classification.")
    st.markdown("---")

    df = load_clustered()
    df_final = load_final()
    df_gravity = load_gravity()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("US Data Centers", len(df))
    col2.metric("States Covered", df["STATE"].nunique())
    col3.metric("Indian Cities Scored", len(df_gravity))
    col4.metric("Clusters Identified", df["Cluster"].nunique())

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Data Centers by State")
        state_counts = df["STATE"].value_counts().reset_index()
        state_counts.columns = ["State", "Count"]
        fig = px.bar(state_counts, x="State", y="Count", color="Count",
                     color_continuous_scale="Blues", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("PCA — Cluster Visualization")
        fig2 = px.scatter(
            df, x="PCA1", y="PCA2", color=df["Cluster"].astype(str),
            hover_data=["CITY", "STATE", "ENERGY"],
            labels={"color": "Cluster"},
            color_discrete_sequence=px.colors.qualitative.Set2,
            template="plotly_white",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("Platform Capabilities")
    c1, c2, c3, c4 = st.columns(4)
    c1.info("**Site Finder**\nGravity model scores 13 Indian cities across 8 infrastructure parameters.")
    c2.info("**Optimizer**\nNSGA-II Pareto optimization across PUE, IXP, service score, and facility age.")
    c3.info("**Cluster Predictor**\nRandom Forest classifier predicts the tier of a new data center.")
    c4.info("**Data Explorer**\nBrowse, filter, and compare the full US data center dataset.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Site Finder (Gravity Model)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Site Finder (Gravity Model)":
    st.title("Site Finder — Gravity Model")
    st.markdown("Rank Indian cities for data center siting using weighted infrastructure parameters.")
    st.markdown("---")

    df = load_gravity()

    with st.expander("Customize Parameter Weights", expanded=False):
        st.markdown("Weights must sum to **1.0**. Adjust based on your priorities.")
        col1, col2 = st.columns(2)
        with col1:
            w_energy = st.slider("Energy Cost (lower = better)", 0.0, 0.5, 0.20, 0.01)
            w_network = st.slider("Network Connectivity (higher = better)", 0.0, 0.5, 0.20, 0.01)
            w_land_cost = st.slider("Land Cost (lower = better)", 0.0, 0.4, 0.15, 0.01)
            w_renewable = st.slider("Renewable Energy % (higher = better)", 0.0, 0.3, 0.10, 0.01)
        with col2:
            w_climate = st.slider("Climate Resilience (higher = better)", 0.0, 0.3, 0.10, 0.01)
            w_workforce = st.slider("Workforce Cost (lower = better)", 0.0, 0.2, 0.05, 0.01)
            w_water = st.slider("Water Cost (lower = better)", 0.0, 0.2, 0.05, 0.01)
            w_land_avail = st.slider("Land Availability (higher = better)", 0.0, 0.2, 0.05, 0.01)

        weights = {
            "Water": w_water, "Energy": w_energy, "Workforce": w_workforce,
            "LandCost": w_land_cost, "Renewable": w_renewable,
            "LandAvail": w_land_avail, "Network": w_network, "Climate": w_climate,
        }
        total = sum(weights.values())
        if abs(total - 1.0) > 0.02:
            st.warning(f"Weights sum to {total:.2f}. Please adjust to sum to 1.0.")

    if "weights" not in dir():
        weights = {
            "Water": 0.05, "Energy": 0.20, "Workforce": 0.05, "LandCost": 0.15,
            "Renewable": 0.10, "LandAvail": 0.05, "Network": 0.20, "Climate": 0.10,
        }

    # Compute scores
    scored = df.copy()
    for param, weight in weights.items():
        if param not in scored.columns:
            continue
        mn, mx = scored[param].min(), scored[param].max()
        if mx == mn:
            scored[param + "_norm"] = 0.0
        elif param in COST_PARAMS:
            scored[param + "_norm"] = (mx - scored[param]) / (mx - mn)
        else:
            scored[param + "_norm"] = (scored[param] - mn) / (mx - mn)

    scored["Score"] = sum(
        scored[p + "_norm"] * w for p, w in weights.items() if p + "_norm" in scored.columns
    )
    scored = scored.sort_values("Score", ascending=False).reset_index(drop=True)
    scored["Rank"] = scored.index + 1

    col_chart, col_table = st.columns([1.5, 1])

    with col_chart:
        st.subheader("City Attraction Scores")
        fig = px.bar(
            scored, x="Score", y="City", orientation="h",
            color="Score", color_continuous_scale="Teal",
            text=scored["Score"].round(3), template="plotly_white",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.subheader("Rankings")
        st.dataframe(
            scored[["Rank", "City", "Score"]].assign(Score=scored["Score"].round(4)),
            use_container_width=True, hide_index=True,
        )

    st.markdown("---")
    st.subheader("Radar — Top 3 Cities")
    top3 = scored.head(3)
    radar_params = list(weights.keys())
    fig_radar = go.Figure()
    for _, row in top3.iterrows():
        fig_radar.add_trace(go.Scatterpolar(
            r=[row[p + "_norm"] for p in radar_params],
            theta=radar_params, fill="toself", name=row["City"],
        ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                             template="plotly_white")
    st.plotly_chart(fig_radar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Optimizer (NSGA-II)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Optimizer (NSGA-II)":
    st.title("Multi-Objective Optimizer — NSGA-II")
    st.markdown("Find Pareto-optimal data centers balancing PUE, network density, services, and facility age.")
    st.markdown("---")

    with st.sidebar:
        st.markdown("### Optimization Settings")
        n_gen = st.slider("Generations", 10, 100, 30)
        n_pop = st.slider("Population Size", 10, 100, 30)
        seed = st.number_input("Random Seed", value=42)
        st.markdown("### Scoring Weights")
        w_pue = st.slider("PUE weight", 0.0, 1.0, 0.4, 0.05)
        w_ixp = st.slider("IXP Count weight", 0.0, 1.0, 0.3, 0.05)
        w_svc = st.slider("Service Score weight", 0.0, 1.0, 0.2, 0.05)
        w_age = st.slider("Facility Age weight", 0.0, 1.0, 0.1, 0.05)
        run_btn = st.button("Run Optimization", type="primary")

    if run_btn:
        with st.spinner("Running NSGA-II optimization..."):
            df = load_final()
            random.seed(int(seed))
            N = len(df)

            if not hasattr(creator, "FitnessMulti"):
                creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0, -1.0, -1.0))
            if not hasattr(creator, "Individual"):
                creator.create("Individual", list, fitness=creator.FitnessMulti)

            toolbox = base.Toolbox()
            toolbox.register("attr_bool", random.randint, 0, 1)
            toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_bool, N)
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)

            def is_valid(row):
                return row["IT EQUIPMENT POWER"] >= 1 and row["AREA"] >= 10000 and row["SERVICE_SCORE"] >= 4

            def evaluate(ind):
                sel = df[[bool(x) for x in ind]]
                valid = sel[sel.apply(is_valid, axis=1)]
                if valid.empty:
                    return (99999.0,) * 4
                return (
                    valid["State_Aggregated_PUE"].sum(),
                    -valid["State_Aggregated_IXP_Count"].sum(),
                    -valid["SERVICE_SCORE"].sum(),
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

            pareto = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]

            rows = []
            for i, ind in enumerate(pareto):
                sel = df[[bool(x) for x in ind]]
                for _, row in sel.iterrows():
                    rows.append({
                        "Solution": i + 1, "Location": row["LOCATION"],
                        "City": row["CITY"], "State": row["STATE"],
                        "PUE": round(float(row["State_Aggregated_PUE"]), 3),
                        "IXP Count": int(row["State_Aggregated_IXP_Count"]),
                        "Service Score": int(row["SERVICE_SCORE"]),
                        "Facility Age": int(row["FACILITY_AGE"]),
                    })

            if not rows:
                st.error("No valid Pareto solutions found. Try adjusting constraints.")
            else:
                res = pd.DataFrame(rows)

                def norm(s):
                    r = s.max() - s.min()
                    return (s - s.min()) / r if r != 0 else pd.Series([0.5] * len(s))

                res["Weighted Score"] = (
                    -norm(res["PUE"]) * w_pue
                    + norm(res["IXP Count"]) * w_ixp
                    + norm(res["Service Score"]) * w_svc
                    - norm(res["Facility Age"]) * w_age
                ).round(4)
                res = res.sort_values("Weighted Score", ascending=False).reset_index(drop=True)
                res.insert(0, "Rank", res.index + 1)

                st.success(f"Found {len(pareto)} Pareto-optimal solutions covering {len(res)} data centers.")
                st.markdown("---")

                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.subheader("Pareto Front — PUE vs IXP Count")
                    fig = px.scatter(
                        res, x="PUE", y="IXP Count", color="Weighted Score",
                        hover_data=["Location", "City", "State", "Service Score"],
                        color_continuous_scale="Viridis", size="Service Score",
                        template="plotly_white",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col_b:
                    st.subheader("Top 10 Results")
                    st.dataframe(
                        res[["Rank","Location","City","State","PUE","IXP Count","Service Score","Weighted Score"]].head(10),
                        use_container_width=True, hide_index=True,
                    )

                st.markdown("---")
                st.subheader("Full Results")
                st.dataframe(res, use_container_width=True, hide_index=True)
    else:
        st.info("Configure settings in the sidebar and click **Run Optimization** to begin.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Cluster Predictor
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Cluster Predictor":
    st.title("Cluster Predictor — Data Center Tier Classification")
    st.markdown("Define a new data center's specs and predict which cluster tier it belongs to.")
    st.markdown("---")

    col_inputs, col_result = st.columns([1, 1])

    with col_inputs:
        st.subheader("Facility Specifications")
        energy = st.slider("Energy Capacity (MW)", 1.0, 150.0, 20.0)
        area = st.slider("Facility Area (sq.ft)", 1000, 500000, 120000)
        it_power = st.slider("IT Equipment Power (MW)", 0.5, 100.0, 15.0)
        pue = st.slider("PUE (Power Usage Effectiveness)", 1.0, 4.0, 1.5, 0.1)
        year = st.slider("Year Operational", 1990, 2025, 2015)
        ixp = st.slider("Internet Exchange Points", 0.0, 20.0, 2.0, 0.5)

        st.subheader("Services Offered")
        c1, c2 = st.columns(2)
        with c1:
            full_cab = st.checkbox("Full Cabinets")
            partial_cab = st.checkbox("Partial Cabinets")
            shared_rack = st.checkbox("Shared Rackspace")
            cages = st.checkbox("Cages")
        with c2:
            suites = st.checkbox("Suites")
            bts = st.checkbox("Build To Suit")
            footprints = st.checkbox("Footprints")
            remote = st.checkbox("Remote Hands")

        predict_btn = st.button("Predict Cluster", type="primary")

    with col_result:
        if predict_btn:
            rf, scaler = load_ml_models()
            input_df = pd.DataFrame([{
                "ENERGY": energy, "AREA": area, "IT EQUIPMENT POWER": it_power,
                "State_Aggregated_PUE": pue,
                "FULL_CABINETS": int(full_cab), "PARTIAL_CABINETS": int(partial_cab),
                "SHARED_RACKSPACE": int(shared_rack), "CAGES": int(cages),
                "SUITES": int(suites), "BUILD_TO_SUIT": int(bts),
                "FOOTPRINTS": int(footprints), "REMOTE_HANDS": int(remote),
                "YEAR_OPERATIONAL": year, "State_Aggregated_IXP_Count": ixp,
            }])
            scaled = scaler.transform(input_df)
            cluster_id = int(rf.predict(scaled)[0])
            probs = rf.predict_proba(scaled)[0]
            label = CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}")
            confidence = round(float(probs[cluster_id]) * 100, 1)

            st.subheader("Prediction Result")
            st.success(f"**{label}** (Cluster {cluster_id})")
            st.metric("Confidence", f"{confidence}%")

            st.markdown("---")
            st.subheader("Probability Distribution")
            prob_df = pd.DataFrame({
                "Cluster": [CLUSTER_LABELS.get(i, f"Cluster {i}") for i in range(len(probs))],
                "Probability": [round(p * 100, 2) for p in probs],
            })
            fig = px.bar(prob_df, x="Cluster", y="Probability", color="Probability",
                         color_continuous_scale="Blues", template="plotly_white", text="Probability")
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.subheader("What This Means")
            descriptions = {
                0: "This facility is a large-scale hyperscale or high-capacity data center. Typically characterized by high energy, large area, and enterprise-grade connectivity.",
                1: "Mid-tier regional facility serving enterprise and colocation clients. Balanced across capacity, services, and cost.",
                2: "Edge or colocation-focused facility — smaller footprint, targeted service offerings, often with strong local network presence.",
            }
            st.info(descriptions.get(cluster_id, ""))
        else:
            st.info("Fill in the specifications and click **Predict Cluster** to see results.")

    st.markdown("---")
    st.subheader("Existing Cluster Distribution")
    df = load_clustered()
    cluster_summary = df.groupby("Cluster").agg(
        Count=("LOCATION", "count"),
        Avg_PUE=("State_Aggregated_PUE", "mean"),
        Avg_Energy=("ENERGY", "mean"),
        Avg_Area=("AREA", "mean"),
    ).reset_index().round(2)
    cluster_summary["Label"] = cluster_summary["Cluster"].map(CLUSTER_LABELS)
    st.dataframe(cluster_summary[["Cluster", "Label", "Count", "Avg_PUE", "Avg_Energy", "Avg_Area"]],
                 use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Data Explorer
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Data Explorer":
    st.title("Data Explorer")
    st.markdown("Browse and filter the full US data center dataset.")
    st.markdown("---")

    df = load_clustered()

    col1, col2, col3 = st.columns(3)
    with col1:
        states = st.multiselect("Filter by State", sorted(df["STATE"].unique()), default=sorted(df["STATE"].unique()))
    with col2:
        clusters = st.multiselect("Filter by Cluster", sorted(df["Cluster"].unique()), default=sorted(df["Cluster"].unique()))
    with col3:
        min_energy, max_energy = float(df["ENERGY"].min()), float(df["ENERGY"].max())
        energy_range = st.slider("Energy Range (MW)", min_energy, max_energy, (min_energy, max_energy))

    filtered = df[
        df["STATE"].isin(states) &
        df["Cluster"].isin(clusters) &
        df["ENERGY"].between(*energy_range)
    ]
    filtered["Cluster Label"] = filtered["Cluster"].map(CLUSTER_LABELS)

    st.markdown(f"**{len(filtered)} data centers** match your filters.")
    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("PUE Distribution by Cluster")
        fig = px.box(filtered, x="Cluster Label", y="State_Aggregated_PUE",
                     color="Cluster Label", template="plotly_white",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Energy vs Area")
        fig2 = px.scatter(filtered, x="ENERGY", y="AREA", color="Cluster Label",
                          hover_data=["CITY", "STATE", "LOCATION"],
                          size="State_Aggregated_IXP_Count",
                          color_discrete_sequence=px.colors.qualitative.Set2,
                          template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("Full Dataset")
    display_cols = ["STATE", "CITY", "LOCATION", "ENERGY", "AREA",
                    "State_Aggregated_PUE", "State_Aggregated_IXP_Count",
                    "YEAR_OPERATIONAL", "Cluster Label"]
    st.dataframe(filtered[display_cols].rename(columns={
        "State_Aggregated_PUE": "PUE",
        "State_Aggregated_IXP_Count": "IXP Count",
        "YEAR_OPERATIONAL": "Year",
    }), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — Data Pipeline
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Data Pipeline":
    import json

    st.title("Data Pipeline")
    st.markdown("End-to-end data lineage — where every number in this platform comes from.")
    st.markdown("---")

    # ── Data Sources ──────────────────────────────────────────────────────────
    st.subheader("Data Sources")
    sources = [
        {
            "Dataset": "US Data Centers",
            "Source": "datacentermap.com",
            "Method": "Playwright web scraper",
            "Coverage": "FL, VA, NY, ID, WA (original) + CA, TX, GA, NC, OH, IL, AZ, NJ, OR, CO (expanded)",
            "Fields": "Name, City, State, Energy (MW), Area (sqft), IT Power (MW), Services (8 types), Year Operational",
            "Last Updated": "May 2025",
        },
        {
            "Dataset": "Indian Cities — Gravity Model",
            "Source": "POSOCO, CEA, brightlio.com, State Electricity Boards",
            "Method": "Manual research + public reports",
            "Coverage": "13 major Indian cities",
            "Fields": "Water cost, Energy cost, Workforce salary, Renewable %, Land cost, Land availability, Network index, Climate index",
            "Last Updated": "April 2025",
        },
        {
            "Dataset": "State PUE Estimates",
            "Source": "Lawrence Berkeley National Laboratory (2024 US Data Center Energy Report)",
            "Method": "Published research — state-level averages",
            "Coverage": "15 US states",
            "Fields": "Power Usage Effectiveness (PUE) — industry standard energy efficiency metric",
            "Last Updated": "2024",
        },
        {
            "Dataset": "State IXP Count",
            "Source": "PeeringDB (peeringdb.com) — public internet exchange database",
            "Method": "Public API / manual lookup",
            "Coverage": "15 US states",
            "Fields": "Number of Internet Exchange Points per state",
            "Last Updated": "2025",
        },
    ]
    st.dataframe(pd.DataFrame(sources), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Data Dictionary ───────────────────────────────────────────────────────
    st.subheader("Data Dictionary — US Data Centers")
    dictionary = [
        {"Column": "STATE",                    "Type": "string", "Description": "2-letter US state abbreviation"},
        {"Column": "CITY",                     "Type": "string", "Description": "City where the data center is located"},
        {"Column": "LOCATION",                 "Type": "string", "Description": "Full facility name / address"},
        {"Column": "ENERGY",                   "Type": "float",  "Description": "Total power capacity in megawatts (MW)"},
        {"Column": "AREA",                     "Type": "int",    "Description": "Facility floor area in square feet"},
        {"Column": "IT EQUIPMENT POWER",       "Type": "float",  "Description": "Power dedicated to IT equipment (MW). If not listed, estimated as 70% of ENERGY."},
        {"Column": "State_Aggregated_PUE",     "Type": "float",  "Description": "Power Usage Effectiveness — total facility power / IT power. Lower is better. 1.0 = perfect. Source: LBNL 2024."},
        {"Column": "FULL_CABINETS",            "Type": "bool",   "Description": "Offers full dedicated server cabinet rental"},
        {"Column": "PARTIAL_CABINETS",         "Type": "bool",   "Description": "Offers partial cabinet rental"},
        {"Column": "SHARED_RACKSPACE",         "Type": "bool",   "Description": "Offers shared rack space"},
        {"Column": "CAGES",                    "Type": "bool",   "Description": "Offers private cage colocation"},
        {"Column": "SUITES",                   "Type": "bool",   "Description": "Offers private data center suites"},
        {"Column": "BUILD_TO_SUIT",            "Type": "bool",   "Description": "Offers custom build-to-suit space"},
        {"Column": "FOOTPRINTS",               "Type": "bool",   "Description": "Offers custom footprint configurations"},
        {"Column": "REMOTE_HANDS",             "Type": "bool",   "Description": "Offers remote hands / on-site technical staff"},
        {"Column": "YEAR_OPERATIONAL",         "Type": "int",    "Description": "Year the facility became operational"},
        {"Column": "State_Aggregated_IXP_Count","Type":"int",    "Description": "Number of Internet Exchange Points in the state. Source: PeeringDB."},
        {"Column": "Cluster",                  "Type": "int",    "Description": "K-Means cluster assignment (0=Hyperscale, 1=Mid-Tier, 2=Edge/Colo)"},
    ]
    st.dataframe(pd.DataFrame(dictionary), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Pipeline Architecture ─────────────────────────────────────────────────
    st.subheader("Pipeline Architecture")
    st.code("""
datacentermap.com
        │
        ▼
scrape_pipeline.py  ←  Playwright browser automation
  • Fetches city lists per state
  • Fetches data center listings per city
  • Fetches specs page per data center
  • Retries on timeout (3 attempts)
  • Rate-limited (3–7s between requests)
        │
        ▼
dc_raw_scraped.csv  ←  Incremental append (never overwrites)
        │
        ▼
merge_and_clean.py  ←  Deduplication, null handling, schema alignment
        │
        ▼
dc_cleaned.csv  ──→  EDA, clustering (K-Means + PCA)  ──→  dc_clustered.csv
                                                                    │
                                                    Random Forest training
                                                                    │
                                                    rf_model.pkl + scaler.pkl
        │
        ▼
pipeline_log.json  ←  Timestamped run record (records added, errors, state summary)
    """, language="text")

    st.markdown("---")

    # ── Live Pipeline Log ─────────────────────────────────────────────────────
    st.subheader("Scrape Run History")
    log_path = DATA_DIR / "pipeline_log.json"
    if log_path.exists():
        log_data = json.loads(log_path.read_text())
        runs = log_data.get("runs", [])
        if runs:
            summary_rows = []
            for r in runs:
                summary_rows.append({
                    "Run ID": r.get("run_id", ""),
                    "Started": r.get("started_at", "")[:19].replace("T", " "),
                    "Finished": r.get("finished_at", "")[:19].replace("T", " ") if r.get("finished_at") else "In progress",
                    "Records Added": r.get("records_added", 0),
                    "States": ", ".join(r.get("states", [])),
                    "Errors": len(r.get("errors", [])),
                })
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

            latest = runs[-1]
            if latest.get("state_summary"):
                st.markdown("**Latest run — records per state:**")
                state_df = pd.DataFrame([
                    {"State": k, "Records Added": v}
                    for k, v in latest["state_summary"].items()
                ])
                fig = px.bar(state_df, x="State", y="Records Added",
                             color="Records Added", color_continuous_scale="Teal",
                             template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No scrape runs recorded yet. Run `python scrapers/scrape_pipeline.py` to start.")
    else:
        st.info("No pipeline log found. Run `python scrapers/scrape_pipeline.py` to start the data pipeline.")

    # ── Raw Scraped Data Preview ───────────────────────────────────────────────
    scraped_path = DATA_DIR / "dc_raw_scraped.csv"
    if scraped_path.exists():
        st.markdown("---")
        st.subheader("Raw Scraped Data (latest)")
        df_raw = pd.read_csv(scraped_path)
        st.markdown(f"**{len(df_raw)} records** scraped so far across **{df_raw['STATE'].nunique()} states**.")
        st.dataframe(df_raw.tail(50), use_container_width=True, hide_index=True)
    else:
        st.markdown("---")
        st.info("No raw scraped data yet. Pipeline has not been run.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — AI Analyst
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "AI Analyst":
    import os, json, anthropic
    from backend.core.ai_context import (
        get_gravity_scores, get_cluster_summary,
        get_dataset_overview, get_top_data_centers, get_city_detail,
    )

    st.title("AI Analyst")
    st.markdown("Ask any question about data center site selection, expansion strategy, or your dataset — answered using real data from your models.")
    st.markdown("---")

    if "anthropic_api_key" not in st.session_state:
        st.session_state.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    api_key = st.session_state.anthropic_api_key

    if not api_key:
        st.markdown("### Enter your Anthropic API Key to get started")
        col_key, col_btn = st.columns([3, 1])
        with col_key:
            entered_key = st.text_input(
                "API Key",
                type="password",
                placeholder="sk-ant-api03-...",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button("Activate", type="primary", use_container_width=True):
                if entered_key.startswith("sk-"):
                    st.session_state.anthropic_api_key = entered_key
                    st.rerun()
                else:
                    st.error("Key should start with sk-ant-...")
        st.markdown("Get a free key at [console.anthropic.com](https://console.anthropic.com) → API Keys")
        st.stop()

    api_key = st.session_state.anthropic_api_key

    # Suggested questions
    st.markdown("**Try asking:**")
    suggestions = [
        "Which Indian city should I choose for a 50MW renewable-focused data center?",
        "Why does Hyderabad rank higher than Mumbai?",
        "What are the characteristics of a Hyperscale data center in our dataset?",
        "Which US data centers have the best PUE efficiency?",
        "Compare Bangalore and Pune for data center expansion.",
        "What does the Mid-Tier cluster look like on average?",
    ]
    cols = st.columns(3)
    for i, s in enumerate(suggestions):
        if cols[i % 3].button(s, key=f"suggest_{i}", use_container_width=True):
            st.session_state["ai_input"] = s

    st.markdown("---")

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tools_used"):
                st.caption(f"Tools used: {', '.join(msg['tools_used'])}")

    # Input
    user_input = st.chat_input("Ask anything about data centers, cities, clusters, or the dataset...")

    # Handle suggestion button
    if "ai_input" in st.session_state and st.session_state["ai_input"]:
        user_input = st.session_state.pop("ai_input")

    TOOLS = [
        {"name": "get_gravity_scores", "description": "Get ranked gravity model scores for 13 Indian cities.",
         "input_schema": {"type": "object", "properties": {"top_n": {"type": "integer", "default": 13}}}},
        {"name": "get_cluster_summary", "description": "Get cluster statistics for all 3 data center tiers.",
         "input_schema": {"type": "object", "properties": {}}},
        {"name": "get_dataset_overview", "description": "Get overall dataset statistics.",
         "input_schema": {"type": "object", "properties": {}}},
        {"name": "get_top_data_centers", "description": "Get top US data centers by a metric (pue, energy, area, ixp, newest).",
         "input_schema": {"type": "object", "properties": {
             "metric": {"type": "string", "enum": ["pue","energy","area","ixp","newest"]},
             "top_n": {"type": "integer", "default": 10},
         }, "required": ["metric"]}},
        {"name": "get_city_detail", "description": "Get detailed parameters for a specific Indian city.",
         "input_schema": {"type": "object", "properties": {
             "city_name": {"type": "string"}
         }, "required": ["city_name"]}},
    ]

    SYSTEM = """You are an expert data center infrastructure analyst for the Data Center Intelligence Platform.

You have access to real data via tools:
- 203 US data centers across 15 states (FL, VA, NY, CA, TX, GA, NC, OH, IL, AZ, NJ, OR, CO, ID, WA)
- 13 Indian cities scored using a gravity model (8 parameters: energy cost, network, land, renewable %, etc.)
- 3 data center tiers from K-Means clustering: Hyperscale (Cluster 0, 38 DCs), Mid-Tier (Cluster 1, 153 DCs), Edge/Colo (Cluster 2, 12 DCs)
- Random Forest classifier with 95% accuracy

STRICT RULES:
1. ALWAYS call the relevant tool first before writing anything
2. Write your answer as plain conversational text — NO markdown tables, NO bullet lists, NO headers
3. Keep answers to 3-5 sentences maximum
4. Cite specific numbers from the tool data (scores, MW, costs, ranks)
5. End with one actionable recommendation
6. Do NOT describe what you are doing — just answer the question directly"""

    def run_tool(name, inputs):
        if name == "get_gravity_scores":      return get_gravity_scores(inputs.get("top_n", 13))
        if name == "get_cluster_summary":     return get_cluster_summary()
        if name == "get_dataset_overview":    return get_dataset_overview()
        if name == "get_top_data_centers":    return get_top_data_centers(inputs.get("metric","pue"), inputs.get("top_n",10))
        if name == "get_city_detail":         return get_city_detail(inputs.get("city_name",""))
        return {"error": f"Unknown tool: {name}"}

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analysing your data..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    messages = [{"role": "user", "content": user_input}]
                    tools_used = []

                    while True:
                        resp = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=1024,
                            system=SYSTEM,
                            tools=TOOLS,
                            messages=messages,
                        )
                        if resp.stop_reason == "tool_use":
                            tool_results = []
                            for block in resp.content:
                                if block.type == "tool_use":
                                    tools_used.append(block.name)
                                    result = run_tool(block.name, block.input)
                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(result),
                                    })
                            messages.append({"role": "assistant", "content": resp.content})
                            messages.append({"role": "user", "content": tool_results})
                        else:
                            final = " ".join(b.text for b in resp.content if hasattr(b, "text"))
                            st.markdown(final)
                            if tools_used:
                                st.caption(f"Data sources queried: {', '.join(set(tools_used))}")
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": final,
                                "tools_used": list(set(tools_used)),
                            })
                            break

                except anthropic.AuthenticationError:
                    st.error("Invalid API key. Please re-enter a valid Anthropic API key.")
                    st.session_state.anthropic_api_key = ""
                    st.session_state.chat_history.pop()
                    st.rerun()
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
                    st.session_state.chat_history.pop()

    if st.session_state.chat_history:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — Site Scout Agent
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Site Scout Agent":
    import os
    from backend.core.site_scout import run_site_scout

    st.title("Site Scout Agent")
    st.markdown("Describe your data center requirements — the agent automatically runs the gravity model, analyses city parameters, benchmarks efficiency, and writes a full site recommendation report.")
    st.markdown("---")

    # API key check
    if "anthropic_api_key" not in st.session_state:
        st.session_state.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_key = st.session_state.anthropic_api_key
    if not api_key:
        st.info("Enter your Anthropic API key on the AI Analyst page first.")
        st.stop()

    # Requirements form
    st.subheader("Define Your Requirements")
    col1, col2 = st.columns(2)
    with col1:
        region = st.selectbox(
            "Target Region",
            ["India — Major Cities", "India — Tier 2 Cities", "Southeast Asia", "Middle East", "Any"],
        )
        capacity_mw = st.slider("Required Capacity (MW)", 1, 200, 50)
        renewable_target = st.slider("Minimum Renewable Energy %", 0, 100, 40)
    with col2:
        budget_tier = st.selectbox(
            "Budget Tier",
            ["Low — minimize land & energy cost", "Medium — balanced cost/quality", "Premium — best infrastructure"],
        )
        priority = st.selectbox(
            "Top Priority",
            [
                "Renewable energy / sustainability",
                "Network connectivity & low latency",
                "Lowest total cost of ownership",
                "Workforce availability & talent pool",
                "Climate resilience & risk mitigation",
            ],
        )

    st.markdown("---")
    run_btn = st.button("Run Site Scout Analysis", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("Agent running — analysing gravity model, benchmarking cities, writing report..."):
            progress = st.progress(0, text="Fetching gravity model scores...")
            try:
                import time
                progress.progress(20, text="Running city analysis...")
                result = run_site_scout(
                    region=region,
                    capacity_mw=capacity_mw,
                    renewable_target_pct=renewable_target,
                    budget_tier=budget_tier,
                    priority=priority,
                    api_key=api_key,
                )
                progress.progress(100, text="Complete!")
                time.sleep(0.3)
                progress.empty()

                # Top city highlight
                st.success(f"Top Recommended Site: **{result['top_city']}**")

                # Requirements summary
                with st.expander("Requirements submitted", expanded=False):
                    r = result["requirements"]
                    st.markdown(f"- **Region:** {r['region']}")
                    st.markdown(f"- **Capacity:** {r['capacity_mw']} MW")
                    st.markdown(f"- **Renewable target:** {r['renewable_pct']}%+")
                    st.markdown(f"- **Budget:** {r['budget_tier']}")
                    st.markdown(f"- **Priority:** {r['priority']}")

                st.markdown("---")

                # Full report
                st.subheader("Full Site Recommendation Report")
                st.markdown(result["report"])

                st.markdown("---")
                st.caption(f"Tools used by agent: {', '.join(result['tools_used'])}")

                # Save to session for download
                st.session_state["last_scout_report"] = result

            except Exception as e:
                st.error(f"Agent error: {e}")

    # Download previous report
    if "last_scout_report" in st.session_state:
        st.markdown("---")
        report_text = st.session_state["last_scout_report"]["report"]
        st.download_button(
            label="Download Report as .txt",
            data=report_text,
            file_name="site_scout_report.txt",
            mime="text/plain",
        )
