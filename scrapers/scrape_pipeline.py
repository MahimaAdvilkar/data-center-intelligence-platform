"""
Unified multi-state data center scraping pipeline.

What it does:
  1. For each target US state, fetches the list of cities with data centers
  2. For each city, fetches the list of data centers
  3. For each data center, fetches detailed specs (power, area, services, etc.)
  4. Cleans and normalises the data into the project's standard CSV schema
  5. Appends results to backend/data/dc_raw_scraped.csv incrementally
  6. Writes a run log to backend/data/pipeline_log.json

Run: python scrapers/scrape_pipeline.py
"""

import sys
import json
import time
import random
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "backend" / "data"
OUTPUT_CSV = DATA_DIR / "dc_raw_scraped.csv"
LOG_FILE   = DATA_DIR / "pipeline_log.json"

sys.path.insert(0, str(ROOT))
from scrapers.state_reference import STATE_REFERENCE, TARGET_STATES

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BASE_URL = "https://www.datacentermap.com/usa/"

# ── Service fields expected in the dataset ─────────────────────────────────────
SERVICE_FIELDS = [
    "Full Cabinets", "Partial Cabinets", "Shared Rackspace",
    "Cages", "Suites", "Build to Suit", "Footprints", "Remote Hands",
]
SERVICE_COL_MAP = {
    "Full Cabinets":    "FULL_CABINETS",
    "Partial Cabinets": "PARTIAL_CABINETS",
    "Shared Rackspace": "SHARED_RACKSPACE",
    "Cages":            "CAGES",
    "Suites":           "SUITES",
    "Build to Suit":    "BUILD_TO_SUIT",
    "Footprints":       "FOOTPRINTS",
    "Remote Hands":     "REMOTE_HANDS",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _sleep(lo=2, hi=5):
    time.sleep(random.uniform(lo, hi))


def _cell_value(cell) -> str:
    try:
        cls = cell.locator("i").first.get_attribute("class") or ""
        if "checkmark" in cls:
            return "Yes"
        if "close" in cls:
            return "No"
    except Exception:
        pass
    return cell.inner_text().strip()


def _parse_number(text: str):
    """Extract first numeric value from a string like '12.5 MW' → 12.5"""
    if not text:
        return None
    m = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
    return float(m.group()) if m else None


def _parse_year(text: str):
    m = re.search(r"(19|20)\d{2}", str(text))
    return int(m.group()) if m else None


def _load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {"runs": []}


def _save_log(log_data: dict):
    LOG_FILE.write_text(json.dumps(log_data, indent=2))


def _append_row(row: dict):
    df = pd.DataFrame([row])
    if OUTPUT_CSV.exists():
        df.to_csv(OUTPUT_CSV, mode="a", header=False, index=False)
    else:
        df.to_csv(OUTPUT_CSV, index=False)


# ── Step 1: Get cities for a state ─────────────────────────────────────────────
def get_cities(page, state_full: str) -> list[dict]:
    url = BASE_URL + state_full + "/"
    log.info(f"Fetching cities for {state_full}: {url}")
    try:
        page.goto(url, timeout=30_000)
        page.wait_for_selector("table", timeout=20_000)
        _sleep(1, 2)
    except PWTimeout:
        log.warning(f"Timeout loading {url}")
        return []

    cities = []
    try:
        rows = page.query_selector_all("table tr")
        for row in rows[1:]:
            cols = row.query_selector_all("td")
            if len(cols) < 2:
                continue
            link = cols[0].query_selector("a")
            if not link:
                continue
            count_text = cols[1].inner_text().strip()
            count = int(re.sub(r"\D", "", count_text)) if count_text else 0
            if count == 0:
                continue
            cities.append({
                "name": link.inner_text().strip(),
                "href": link.get_attribute("href"),
                "count": count,
            })
    except Exception as e:
        log.warning(f"Error parsing cities table: {e}")

    log.info(f"  Found {len(cities)} cities with data centers")
    return cities


# ── Step 2: Get datacenter list for a city ─────────────────────────────────────
def get_datacenters(page, city: dict) -> list[dict]:
    city_url = urljoin("https://www.datacentermap.com", city["href"])
    log.info(f"  City: {city['name']} ({city_url})")
    try:
        page.goto(city_url, timeout=30_000)
        page.wait_for_selector(".ui.card, .ui.centered.cards", timeout=20_000)
        _sleep(2, 4)
    except PWTimeout:
        log.warning(f"  Timeout loading city page: {city_url}")
        return []

    dcs = []
    try:
        cards = page.query_selector_all(".ui.card")
        for card in cards:
            try:
                name_el = card.query_selector(".header")
                dc_name = name_el.inner_text().strip() if name_el else None
                href = card.get_attribute("href")
                if dc_name and href:
                    dcs.append({"name": dc_name, "href": href})
            except Exception:
                pass
    except Exception as e:
        log.warning(f"  Error parsing datacenter cards: {e}")

    log.info(f"  Found {len(dcs)} data centers")
    return dcs


# ── Step 3: Get specs for one datacenter ──────────────────────────────────────
def get_specs(page, dc: dict, city_name: str, state_abbr: str) -> dict | None:
    specs_url = "https://www.datacentermap.com" + dc["href"].rstrip("/") + "/specs/"
    ref = STATE_REFERENCE[state_abbr]

    for attempt in range(3):
        try:
            page.goto(specs_url, timeout=25_000)
            _sleep(2, 5)
            break
        except PWTimeout:
            log.warning(f"    Timeout attempt {attempt+1} for {specs_url}")
            if attempt == 2:
                return None

    energy, area, year = None, None, None
    try:
        stats = page.locator(".ui.three.statistics .ui.statistic")
        if stats.count() >= 1:
            energy_text = stats.nth(0).inner_text()
            energy = _parse_number(energy_text)
        if stats.count() >= 2:
            area_text = stats.nth(1).inner_text()
            area = _parse_number(area_text)
        if stats.count() >= 3:
            year_text = stats.nth(2).inner_text()
            year = _parse_year(year_text)
    except Exception as e:
        log.warning(f"    Stats error: {e}")

    if not energy and not area:
        log.info(f"    Skipping {dc['name']} — no key stats found")
        return None

    services = {col: False for col in SERVICE_COL_MAP.values()}
    it_power = None

    try:
        sections = page.locator(".ui.stackable.grid .eight.wide.column")
        for i in range(sections.count()):
            section = sections.nth(i)
            try:
                header = section.locator(".ui.horizontal.divider").inner_text().strip().upper()
            except Exception:
                continue

            rows = section.locator("tr")
            for j in range(rows.count()):
                try:
                    cells = rows.nth(j).locator("td")
                    if cells.count() < 2:
                        continue
                    key = cells.nth(0).inner_text().strip()
                    val = _cell_value(cells.nth(1))

                    # Services
                    if key in SERVICE_COL_MAP:
                        services[SERVICE_COL_MAP[key]] = val == "Yes"

                    # IT power (sometimes listed as "IT Load" or "IT Equipment Power")
                    if "IT" in key.upper() and ("LOAD" in key.upper() or "POWER" in key.upper() or "EQUIPMENT" in key.upper()):
                        it_power = _parse_number(val)
                except Exception:
                    pass
    except Exception as e:
        log.warning(f"    Specs section error: {e}")

    if it_power is None and energy:
        it_power = round(energy * 0.7, 2)

    record = {
        "STATE": state_abbr,
        "CITY": city_name,
        "LOCATION": dc["name"],
        "ENERGY": energy,
        "AREA": int(area) if area else None,
        "IT EQUIPMENT POWER": it_power,
        "State_Aggregated_PUE": ref["pue"],
        **services,
        "YEAR_OPERATIONAL": year,
        "State_Aggregated_IXP_Count": ref["ixp_count"],
        "SOURCE_URL": specs_url,
        "SCRAPED_AT": datetime.now(timezone.utc).isoformat(),
    }
    return record


# ── Main pipeline ──────────────────────────────────────────────────────────────
def run_pipeline(states: list[str] = None, max_per_state: int = 60):
    if states is None:
        states = TARGET_STATES

    log_data = _load_log()
    run_entry = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "states": states,
        "records_added": 0,
        "errors": [],
        "state_summary": {},
    }

    total_added = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for state_abbr in states:
            if state_abbr not in STATE_REFERENCE:
                log.warning(f"No reference data for {state_abbr}, skipping")
                continue

            ref = STATE_REFERENCE[state_abbr]
            state_full = ref["state_full"]
            log.info(f"\n{'='*50}")
            log.info(f"STATE: {state_abbr} ({state_full})")
            log.info(f"{'='*50}")

            state_count = 0
            cities = get_cities(page, state_full)

            # Sort cities by count descending — biggest markets first
            cities = sorted(cities, key=lambda c: c["count"], reverse=True)

            for city in cities:
                if state_count >= max_per_state:
                    log.info(f"  Reached max {max_per_state} for {state_abbr}")
                    break

                dcs = get_datacenters(page, city)
                _sleep(1, 3)

                for dc in dcs:
                    if state_count >= max_per_state:
                        break
                    try:
                        record = get_specs(page, dc, city["name"], state_abbr)
                        if record:
                            _append_row(record)
                            state_count += 1
                            total_added += 1
                            log.info(f"    [{state_count}] Saved: {dc['name']}, {city['name']}, {state_abbr}")
                        _sleep(3, 7)
                    except Exception as e:
                        log.error(f"    Error on {dc['name']}: {e}")
                        run_entry["errors"].append({"dc": dc["name"], "error": str(e)})

            run_entry["state_summary"][state_abbr] = state_count
            log.info(f"  {state_abbr} done — {state_count} records added")
            _sleep(3, 6)

        browser.close()

    run_entry["finished_at"] = datetime.now(timezone.utc).isoformat()
    run_entry["records_added"] = total_added
    log_data["runs"].append(run_entry)
    _save_log(log_data)

    log.info(f"\nPipeline complete. Total records added: {total_added}")
    log.info(f"Output: {OUTPUT_CSV}")
    log.info(f"Log:    {LOG_FILE}")


if __name__ == "__main__":
    run_pipeline()
