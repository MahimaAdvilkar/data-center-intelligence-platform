"""
Site Scout Agent — runs gravity model + NSGA-II automatically
based on user requirements and returns a structured recommendation.
"""
import json
import os
import anthropic
from backend.core.ai_context import (
    get_gravity_scores, get_cluster_summary,
    get_top_data_centers, get_city_detail,
)

SCOUT_TOOLS = [
    {
        "name": "get_gravity_scores",
        "description": "Get ranked gravity model scores for all 13 Indian cities.",
        "input_schema": {"type": "object", "properties": {
            "top_n": {"type": "integer", "default": 13}
        }},
    },
    {
        "name": "get_city_detail",
        "description": "Get full parameter breakdown for a specific Indian city.",
        "input_schema": {"type": "object", "properties": {
            "city_name": {"type": "string"}
        }, "required": ["city_name"]},
    },
    {
        "name": "get_top_data_centers",
        "description": "Get top US data centers ranked by a metric.",
        "input_schema": {"type": "object", "properties": {
            "metric": {"type": "string", "enum": ["pue", "energy", "area", "ixp", "newest"]},
            "top_n": {"type": "integer", "default": 5},
        }, "required": ["metric"]},
    },
    {
        "name": "get_cluster_summary",
        "description": "Get summary of all 3 data center cluster tiers.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

SCOUT_SYSTEM = """You are the Site Scout Agent for the Data Center Intelligence Platform.

Your job: given a user's data center requirements, run the relevant analysis tools and produce a structured site recommendation report.

ALWAYS follow this exact process:
1. Call get_gravity_scores to get all city rankings
2. Call get_city_detail for the top 2-3 cities
3. Call get_top_data_centers with metric="pue" to benchmark efficiency
4. Call get_cluster_summary to understand what tier matches the user's needs
5. Write your final report

Your final report MUST follow this exact structure (use these exact headers):

## RECOMMENDATION SUMMARY
One sentence: the single best city and why.

## TOP 3 SITES RANKED
Rank each city with its score, key strengths, and one risk.

## WHY THIS BEATS THE ALTERNATIVES
2-3 sentences comparing the top pick against the next best option using real numbers.

## FIT WITH REQUIREMENTS
How well does the recommendation match what the user asked for (MW, renewable %, budget tier)?

## RISKS & MITIGATIONS
2 key risks and how to address them.

## NEXT STEPS
3 concrete actions the user should take.

Use real numbers from the tools throughout. Be specific and direct."""


def _run_scout_tool(name: str, inputs: dict):
    if name == "get_gravity_scores":
        return get_gravity_scores(inputs.get("top_n", 13))
    if name == "get_city_detail":
        return get_city_detail(inputs.get("city_name", ""))
    if name == "get_top_data_centers":
        return get_top_data_centers(inputs.get("metric", "pue"), inputs.get("top_n", 5))
    if name == "get_cluster_summary":
        return get_cluster_summary()
    return {"error": f"Unknown tool: {name}"}


def run_site_scout(
    region: str,
    capacity_mw: float,
    renewable_target_pct: int,
    budget_tier: str,
    priority: str,
    api_key: str,
) -> dict:
    """
    Run the Site Scout Agent end to end.
    Returns: {report: str, tools_used: list, top_city: str}
    """
    user_prompt = f"""Analyse and recommend the best data center site for this requirement:

- Region of interest: {region}
- Required capacity: {capacity_mw} MW
- Renewable energy target: {renewable_target_pct}%+
- Budget tier: {budget_tier}
- Top priority: {priority}

Run all necessary tools, then write the full site recommendation report."""

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": user_prompt}]
    tools_used = []

    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SCOUT_SYSTEM,
            tools=SCOUT_TOOLS,
            messages=messages,
        )

        if resp.stop_reason == "tool_use":
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    tools_used.append(block.name)
                    result = _run_scout_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            report = " ".join(
                b.text for b in resp.content if hasattr(b, "text")
            )
            top_city = _extract_top_city(report)
            return {
                "report": report,
                "tools_used": list(set(tools_used)),
                "top_city": top_city,
                "requirements": {
                    "region": region,
                    "capacity_mw": capacity_mw,
                    "renewable_pct": renewable_target_pct,
                    "budget_tier": budget_tier,
                    "priority": priority,
                },
            }


def _extract_top_city(report: str) -> str:
    """Best-effort extract the top recommended city from the report."""
    cities = [
        "Mumbai", "Hyderabad", "Bangalore", "Pune", "Chennai",
        "Ahmedabad", "Noida", "Gurgaon", "Kolkata", "Jaipur",
        "Chandigarh", "Bhopal", "Nagpur", "Mangalore",
    ]
    report_lower = report.lower()
    # Find the city mentioned earliest in the report
    earliest = None
    earliest_pos = len(report_lower)
    for city in cities:
        pos = report_lower.find(city.lower())
        if 0 <= pos < earliest_pos:
            earliest_pos = pos
            earliest = city
    return earliest or "See report"
