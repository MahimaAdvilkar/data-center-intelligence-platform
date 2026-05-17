"""
Merges newly scraped data (dc_raw_scraped.csv) with the existing
cleaned dataset (dc_cleaned.csv), deduplicates, handles nulls,
and writes the updated dc_cleaned.csv.

Run AFTER scrape_pipeline.py:
  python scrapers/merge_and_clean.py
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA_DIR = ROOT / "backend" / "data"

EXISTING = DATA_DIR / "dc_cleaned.csv"
SCRAPED  = DATA_DIR / "dc_raw_scraped.csv"
OUTPUT   = DATA_DIR / "dc_cleaned.csv"

BOOL_COLS = [
    "FULL_CABINETS","PARTIAL_CABINETS","SHARED_RACKSPACE","CAGES",
    "SUITES","BUILD_TO_SUIT","FOOTPRINTS","REMOTE_HANDS",
]

SCHEMA_COLS = [
    "STATE","CITY","LOCATION","ENERGY","AREA","IT EQUIPMENT POWER",
    "State_Aggregated_PUE",
    *BOOL_COLS,
    "YEAR_OPERATIONAL","State_Aggregated_IXP_Count",
]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # Normalise booleans
    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().map(
                {"true": True, "false": False, "yes": True, "no": False,
                 "1": True, "0": False}
            ).fillna(False)

    # Drop rows missing critical fields
    df = df.dropna(subset=["ENERGY", "AREA"])

    # Fill IT power with 70% of energy if missing
    mask = df["IT EQUIPMENT POWER"].isna()
    df.loc[mask, "IT EQUIPMENT POWER"] = (df.loc[mask, "ENERGY"] * 0.7).round(2)

    # Fill year with median if missing
    if df["YEAR_OPERATIONAL"].isna().any():
        median_year = int(df["YEAR_OPERATIONAL"].median())
        df["YEAR_OPERATIONAL"] = df["YEAR_OPERATIONAL"].fillna(median_year).astype(int)

    df["ENERGY"] = df["ENERGY"].round(2)
    df["AREA"] = df["AREA"].astype(int)

    return df


def main():
    if not SCRAPED.exists():
        print(f"No scraped data found at {SCRAPED}. Run scrape_pipeline.py first.")
        return

    df_new = pd.read_csv(SCRAPED)
    print(f"Scraped records: {len(df_new)}")

    if EXISTING.exists():
        df_old = pd.read_csv(EXISTING)
        print(f"Existing records: {len(df_old)}")
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new.copy()

    # Keep only schema columns that exist
    keep = [c for c in SCHEMA_COLS if c in df_combined.columns]
    df_combined = df_combined[keep]

    df_combined = clean(df_combined)

    # Deduplicate by location name + state
    before = len(df_combined)
    df_combined = df_combined.drop_duplicates(subset=["LOCATION", "STATE"], keep="first")
    after = len(df_combined)
    print(f"Removed {before - after} duplicates")

    df_combined = df_combined.reset_index(drop=True)
    df_combined.to_csv(OUTPUT, index=False)
    print(f"Saved {len(df_combined)} records to {OUTPUT}")
    print(f"States covered: {sorted(df_combined['STATE'].unique())}")


if __name__ == "__main__":
    main()
