"""
Unified multi-state data center scraping pipeline.

Fixes vs v1:
  - Deduplicate cities by URL (was processing Santa Clara 2x+)
  - Try multiple stat selectors (site structure varies by operator)
  - Accept partial data: energy alone is enough to save a record
  - Faster sleep: 1–3s between requests instead of 3–7s
  - max_per_state=20 default (completes in ~15 min per state)
  - Break out of both loops correctly once state cap is hit

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

ROOT       = Path(__file__).resolve().parent.parent
DATA_DIR   = ROOT / "backend" / "data"
OUTPUT_CSV = DATA_DIR / "dc_raw_scraped.csv"
LOG_FILE   = DATA_DIR / "pipeline_log.json"

sys.path.insert(0, str(ROOT))
from scrapers.state_reference import STATE_REFERENCE, TARGET_STATES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BASE_URL = "https://www.datacentermap.com/usa/"

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


def _sleep(lo=1, hi=3):
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
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


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


# ── Already-scraped locations (avoid duplicates across runs) ──────────────────
def _load_scraped_locations() -> set:
    if not OUTPUT_CSV.exists():
        return set()
    df = pd.read_csv(OUTPUT_CSV)
    return set(zip(df["LOCATION"].str.lower(), df["STATE"]))


# ── Step 1: Cities ─────────────────────────────────────────────────────────────
def get_cities(page, state_full: str) -> list[dict]:
    url = BASE_URL + state_full + "/"
    log.info(f"Fetching cities → {url}")
    try:
        page.goto(url, timeout=30_000)
        page.wait_for_selector("table", timeout=20_000)
        _sleep(1, 2)
    except PWTimeout:
        log.warning(f"Timeout loading {url}")
        return []

    cities, seen_hrefs = [], set()
    try:
        for row in page.query_selector_all("table tr")[1:]:
            cols = row.query_selector_all("td")
            if len(cols) < 2:
                continue
            link = cols[0].query_selector("a")
            if not link:
                continue
            href = link.get_attribute("href")
            if href in seen_hrefs:          # ← deduplicate by URL
                continue
            seen_hrefs.add(href)
            count_text = cols[1].inner_text().strip()
            count = int(re.sub(r"\D", "", count_text)) if count_text else 0
            if count == 0:
                continue
            cities.append({"name": link.inner_text().strip(), "href": href, "count": count})
    except Exception as e:
        log.warning(f"Error parsing cities: {e}")

    log.info(f"  {len(cities)} unique cities found")
    return sorted(cities, key=lambda c: c["count"], reverse=True)


# ── Step 2: Data centers per city ─────────────────────────────────────────────
def get_datacenters(page, city: dict) -> list[dict]:
    city_url = urljoin("https://www.datacentermap.com", city["href"])
    try:
        page.goto(city_url, timeout=30_000)
        page.wait_for_selector(".ui.card, .ui.centered.cards", timeout=20_000)
        _sleep(1, 2)
    except PWTimeout:
        log.warning(f"  Timeout: {city_url}")
        return []

    dcs, seen = [], set()
    try:
        for card in page.query_selector_all(".ui.card"):
            try:
                name_el = card.query_selector(".header")
                dc_name = name_el.inner_text().strip() if name_el else None
                href = card.get_attribute("href")
                if dc_name and href and href not in seen:
                    seen.add(href)
                    dcs.append({"name": dc_name, "href": href})
            except Exception:
                pass
    except Exception as e:
        log.warning(f"  Card parse error: {e}")

    return dcs


# ── Step 3: Specs per data center ─────────────────────────────────────────────
def get_specs(page, dc: dict, city_name: str, state_abbr: str) -> dict | None:
    specs_url = "https://www.datacentermap.com" + dc["href"].rstrip("/") + "/specs/"
    ref = STATE_REFERENCE[state_abbr]

    for attempt in range(2):
        try:
            page.goto(specs_url, timeout=20_000)
            _sleep(1, 2)
            break
        except PWTimeout:
            if attempt == 1:
                return None

    energy, area, year = None, None, None

    # Try selector 1: standard three-stat block
    try:
        stats = page.locator(".ui.three.statistics .ui.statistic")
        if stats.count() >= 1:
            energy = _parse_number(stats.nth(0).inner_text())
        if stats.count() >= 2:
            area = _parse_number(stats.nth(1).inner_text())
        if stats.count() >= 3:
            year = _parse_year(stats.nth(2).inner_text())
    except Exception:
        pass

    # Try selector 2: any .statistic blocks on page
    if not energy:
        try:
            for stat in page.query_selector_all(".ui.statistic"):
                label = (stat.query_selector(".label") or stat).inner_text().lower()
                value_el = stat.query_selector(".value")
                if not value_el:
                    continue
                val = value_el.inner_text().strip()
                if "mw" in label or "power" in label or "energy" in label:
                    energy = _parse_number(val)
                elif "sq" in label or "area" in label or "floor" in label:
                    area = _parse_number(val)
                elif "year" in label or "established" in label or "built" in label:
                    year = _parse_year(val)
        except Exception:
            pass

    # Try selector 3: parse page text for obvious patterns
    if not energy:
        try:
            page_text = page.inner_text("body")
            mw_match = re.search(r"(\d+\.?\d*)\s*MW", page_text, re.IGNORECASE)
            if mw_match:
                energy = float(mw_match.group(1))
            sqft_match = re.search(r"([\d,]+)\s*sq\.?\s*ft", page_text, re.IGNORECASE)
            if sqft_match:
                area = _parse_number(sqft_match.group(1))
        except Exception:
            pass

    # Need at least energy to save the record
    if not energy:
        return None

    # Parse services from spec tables
    services = {col: False for col in SERVICE_COL_MAP.values()}
    it_power = None
    try:
        for row in page.query_selector_all("tr"):
            cells = row.query_selector_all("td")
            if len(cells) < 2:
                continue
            key = cells[0].inner_text().strip()
            val = _cell_value(cells[1])
            if key in SERVICE_COL_MAP:
                services[SERVICE_COL_MAP[key]] = val == "Yes"
            if re.search(r"IT.*(load|power|equipment)", key, re.IGNORECASE):
                it_power = _parse_number(val)
    except Exception:
        pass

    if it_power is None:
        it_power = round(energy * 0.7, 2)

    return {
        "STATE":                     state_abbr,
        "CITY":                      city_name,
        "LOCATION":                  dc["name"],
        "ENERGY":                    energy,
        "AREA":                      int(area) if area else None,
        "IT EQUIPMENT POWER":        it_power,
        "State_Aggregated_PUE":      ref["pue"],
        **services,
        "YEAR_OPERATIONAL":          year,
        "State_Aggregated_IXP_Count": ref["ixp_count"],
        "SOURCE_URL":                specs_url,
        "SCRAPED_AT":                datetime.now(timezone.utc).isoformat(),
    }


# ── Main pipeline ──────────────────────────────────────────────────────────────
def run_pipeline(states: list[str] = None, max_per_state: int = 20):
    if states is None:
        states = TARGET_STATES

    already_scraped = _load_scraped_locations()
    log.info(f"Already scraped: {len(already_scraped)} locations (will skip duplicates)")

    log_data = _load_log()
    run_entry = {
        "run_id":       datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "started_at":   datetime.now(timezone.utc).isoformat(),
        "states":       states,
        "records_added": 0,
        "errors":       [],
        "state_summary": {},
    }

    total_added = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for state_abbr in states:
            if state_abbr not in STATE_REFERENCE:
                continue

            ref = STATE_REFERENCE[state_abbr]
            log.info(f"\n{'='*50}\nSTATE: {state_abbr} ({ref['state_full']})\n{'='*50}")

            state_count = 0
            cities = get_cities(page, ref["state_full"])

            for city in cities:
                if state_count >= max_per_state:
                    break

                log.info(f"  City: {city['name']} ({city['count']} DCs listed)")
                dcs = get_datacenters(page, city)
                _sleep(1, 2)

                for dc in dcs:
                    if state_count >= max_per_state:
                        break

                    loc_key = (dc["name"].lower(), state_abbr)
                    if loc_key in already_scraped:
                        log.info(f"    Skip (already scraped): {dc['name']}")
                        continue

                    try:
                        record = get_specs(page, dc, city["name"], state_abbr)
                        if record:
                            _append_row(record)
                            already_scraped.add(loc_key)
                            state_count += 1
                            total_added += 1
                            log.info(f"    [{total_added}] Saved: {dc['name']}, {city['name']}, {state_abbr}")
                        else:
                            log.info(f"    Skip (no stats): {dc['name']}")
                        _sleep(1, 3)
                    except Exception as e:
                        log.error(f"    Error on {dc['name']}: {e}")
                        run_entry["errors"].append({"dc": dc["name"], "error": str(e)})

            run_entry["state_summary"][state_abbr] = state_count
            log.info(f"  {state_abbr} done — {state_count} records")
            _sleep(2, 4)

        browser.close()

    run_entry["finished_at"]   = datetime.now(timezone.utc).isoformat()
    run_entry["records_added"] = total_added
    log_data["runs"].append(run_entry)
    _save_log(log_data)

    log.info(f"\nDone. Total records added this run: {total_added}")
    log.info(f"Output: {OUTPUT_CSV}")
    log.info(f"Log:    {LOG_FILE}")


if __name__ == "__main__":
    run_pipeline()
