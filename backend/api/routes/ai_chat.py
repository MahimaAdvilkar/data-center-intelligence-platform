import os
import json
import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.site_scout import run_site_scout
from backend.core.ai_context import (
    get_gravity_scores, get_cluster_summary,
    get_dataset_overview, get_top_data_centers, get_city_detail,
)

router = APIRouter(prefix="/ai", tags=["AI Chat"])

TOOLS = [
    {
        "name": "get_gravity_scores",
        "description": "Get ranked scores for 13 Indian cities using the gravity model. "
                       "Use this when the user asks about site selection in India, "
                       "which city is best, or comparisons between Indian cities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "How many top cities to return (default 13)", "default": 13}
            },
        },
    },
    {
        "name": "get_cluster_summary",
        "description": "Get summary statistics for each data center cluster (Hyperscale, Mid-Tier, Edge). "
                       "Use this when the user asks about cluster characteristics, what each tier means, "
                       "or how data centers are categorised.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_dataset_overview",
        "description": "Get high-level statistics about the full US data center dataset. "
                       "Use this when the user asks about the dataset, how many data centers, "
                       "which states are covered, or data sources.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_top_data_centers",
        "description": "Get the top data centers ranked by a specific metric. "
                       "Use this when the user asks which data centers are most efficient, "
                       "largest, newest, or most connected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": ["pue", "energy", "area", "ixp", "newest"],
                    "description": "Metric to rank by: pue (efficiency), energy (power capacity), "
                                   "area (size), ixp (connectivity), newest (year built)",
                },
                "top_n": {"type": "integer", "description": "Number of results (default 10)", "default": 10},
            },
            "required": ["metric"],
        },
    },
    {
        "name": "get_city_detail",
        "description": "Get detailed parameter breakdown for a specific Indian city. "
                       "Use this when the user asks about a specific city like Hyderabad or Bangalore.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city_name": {"type": "string", "description": "Name of the Indian city"}
            },
            "required": ["city_name"],
        },
    },
]

SYSTEM_PROMPT = """You are an expert data center infrastructure analyst for the Data Center Intelligence Platform.

You have access to real data about:
- 203 US data centers across 15 states (FL, VA, NY, ID, WA, CA, TX, GA, NC, OH, IL, AZ, NJ, OR, CO)
- 13 Indian cities scored for data center expansion using a gravity model
- 3 data center tiers identified via K-Means clustering (Hyperscale, Mid-Tier, Edge/Colocation)
- A Random Forest classifier with 95% accuracy for predicting data center tier

When answering questions:
1. Always call the relevant tool FIRST to get live data before responding
2. Ground every claim in the actual numbers from the data
3. Be specific — cite city names, scores, MW values, PUE numbers
4. Be honest about data limitations (e.g. Edge cluster has few samples)
5. Keep answers concise but insightful — you're talking to a business or data analyst

Context on key metrics:
- PUE (Power Usage Effectiveness): 1.0 = perfect, 1.5 = good, 2.0+ = inefficient
- IXP Count: Internet Exchange Points in the state — higher means better network connectivity
- Gravity Score: 0 to 1, higher is better for data center siting
- Clusters: 0=Hyperscale (large scale), 1=Mid-Tier (regional enterprise), 2=Edge (small, local)

The project is a capstone that has been scaled into a production AI platform.
The US expansion plan focused on existing colocation markets.
The India gravity model represents the business expansion plan into emerging markets.
"""


def _run_tool(name: str, inputs: dict):
    if name == "get_gravity_scores":
        return get_gravity_scores(inputs.get("top_n", 13))
    elif name == "get_cluster_summary":
        return get_cluster_summary()
    elif name == "get_dataset_overview":
        return get_dataset_overview()
    elif name == "get_top_data_centers":
        return get_top_data_centers(inputs.get("metric", "pue"), inputs.get("top_n", 10))
    elif name == "get_city_detail":
        return get_city_detail(inputs.get("city_name", ""))
    return {"error": f"Unknown tool: {name}"}


class ChatRequest(BaseModel):
    message: str
    history: list = []
    api_key: str = ""


class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]


class ScoutRequest(BaseModel):
    region: str
    capacity_mw: float
    renewable_target_pct: int
    budget_tier: str
    priority: str
    api_key: str = ""


@router.post("/scout")
def scout(req: ScoutRequest):
    api_key = req.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="No Anthropic API key provided.")
    try:
        result = run_site_scout(
            region=req.region,
            capacity_mw=req.capacity_mw,
            renewable_target_pct=req.renewable_target_pct,
            budget_tier=req.budget_tier,
            priority=req.priority,
            api_key=api_key,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    api_key = req.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY environment variable not set."
        )

    client = anthropic.Anthropic(api_key=api_key)

    messages = list(req.history) + [{"role": "user", "content": req.message}]
    tools_used = []

    # Agentic loop — Claude calls tools until it has enough to respond
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_used.append(block.name)
                    result = _run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            final_text = " ".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            return ChatResponse(response=final_text, tools_used=tools_used)
