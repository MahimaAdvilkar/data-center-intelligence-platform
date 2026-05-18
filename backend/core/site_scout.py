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

Your job: analyse the user's data center requirements, call the relevant tools, and produce a structured professional recommendation report.

TOOL SELECTION RULES — follow these strictly:

If the region contains "US" or is a US region (e.g. East Coast, West Coast, South, Midwest, Southwest, National):
  1. Call get_cluster_summary — understand what tier fits the user's capacity
  2. Call get_top_data_centers with metric="pue" — identify the most efficient existing facilities
  3. Call get_top_data_centers with metric="energy" — identify highest-capacity sites
  4. Write your report focused on US markets, states, and data center operators

If the region is an India region (e.g. South India, Pan-India, North India, etc.):
  1. Call get_gravity_scores — rank Indian cities
  2. Call get_city_detail for the top 2-3 cities
  3. Call get_cluster_summary — match the user's tier requirements
  4. Write your report focused on Indian cities and gravity model scores

OUTPUT FORMAT RULES — these are mandatory:
- Write in plain professional prose. No emojis whatsoever.
- Do not use asterisks (* or **) for emphasis. Use plain text.
- Numbers must come from the tool results — never invent figures.
- Use these exact section headers (## prefix, uppercase):

## RECOMMENDATION SUMMARY
## TOP 3 SITES RANKED
## WHY THIS BEATS THE ALTERNATIVES
## FIT WITH REQUIREMENTS
## RISKS AND MITIGATIONS
## NEXT STEPS

Each section should be concise and data-driven. Cite specific scores, MW values, PUE figures, and state names from the tool results."""


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
    """Best-effort extract the top recommended city or state from the report."""
    locations = [
        # Indian cities
        "Mumbai", "Hyderabad", "Bangalore", "Pune", "Chennai",
        "Ahmedabad", "Noida", "Gurgaon", "Kolkata", "Jaipur",
        "Chandigarh", "Bhopal", "Nagpur", "Mangalore",
        # US states / markets
        "Virginia", "Northern Virginia", "Dallas", "Chicago",
        "Seattle", "San Jose", "Silicon Valley", "Phoenix",
        "Atlanta", "New York", "New Jersey", "Portland",
        "Denver", "Columbus", "Charlotte",
    ]
    report_lower = report.lower()
    earliest = None
    earliest_pos = len(report_lower)
    for loc in locations:
        pos = report_lower.find(loc.lower())
        if 0 <= pos < earliest_pos:
            earliest_pos = pos
            earliest = loc
    return earliest or "See report"
