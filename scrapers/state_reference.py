"""
State-level reference data for US data center markets.
Sources:
  - PUE: Lawrence Berkeley National Laboratory (2024 US Data Center Report)
  - IXP Count: PeeringDB (peeringdb.com) - public internet exchange database
  - Renewable %: EIA State Energy Data (eia.gov)
"""

STATE_REFERENCE = {
    "CA": {"state_full": "california",  "pue": 1.50, "ixp_count": 12, "renewable_pct": 52},
    "TX": {"state_full": "texas",       "pue": 1.60, "ixp_count": 6,  "renewable_pct": 31},
    "GA": {"state_full": "georgia",     "pue": 1.58, "ixp_count": 5,  "renewable_pct": 14},
    "NC": {"state_full": "north-carolina","pue": 1.55, "ixp_count": 4, "renewable_pct": 19},
    "OH": {"state_full": "ohio",        "pue": 1.57, "ixp_count": 5,  "renewable_pct": 9},
    "IL": {"state_full": "illinois",    "pue": 1.52, "ixp_count": 9,  "renewable_pct": 12},
    "AZ": {"state_full": "arizona",     "pue": 1.65, "ixp_count": 4,  "renewable_pct": 18},
    "NJ": {"state_full": "new-jersey",  "pue": 1.62, "ixp_count": 7,  "renewable_pct": 8},
    "OR": {"state_full": "oregon",      "pue": 1.45, "ixp_count": 5,  "renewable_pct": 69},
    "CO": {"state_full": "colorado",    "pue": 1.55, "ixp_count": 4,  "renewable_pct": 30},
    # Already in dataset — included for completeness
    "FL": {"state_full": "florida",     "pue": 1.80, "ixp_count": 7,  "renewable_pct": 5},
    "VA": {"state_full": "virginia",    "pue": 1.58, "ixp_count": 6,  "renewable_pct": 12},
    "NY": {"state_full": "new-york",    "pue": 1.60, "ixp_count": 10, "renewable_pct": 27},
    "ID": {"state_full": "idaho",       "pue": 1.45, "ixp_count": 2,  "renewable_pct": 79},
    "WA": {"state_full": "washington",  "pue": 1.46, "ixp_count": 5,  "renewable_pct": 75},
}

# States to scrape in this run (excludes already-scraped states)
TARGET_STATES = ["CA", "TX", "GA", "NC", "OH", "IL", "AZ", "NJ", "OR", "CO"]
