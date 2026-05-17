from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import time
import random
from urllib.parse import urljoin

def main():
    with sync_playwright() as p:
        # Launch Chromium in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Base URL and target state path
        base_url = "https://www.datacentermap.com/usa/"
        state_path = "california"
        full_url = urljoin(base_url, state_path+"/")
        
        print("Opening "+state_path +" page...")
        page.goto(full_url)
        
        # Wait for the cities table to load using an appropriate selector
        try:
            page.wait_for_selector(".ui.sortable.striped.very.basic.very.compact.table", timeout=30000)
        except PlaywrightTimeoutError:
            print("Timed out waiting for the cities table to load.")
            browser.close()
            return
        
        # Extract cities from the table
        cities = []
        try:
            table = page.query_selector(".ui.sortable.striped.very.basic.very.compact.table")
            rows = table.query_selector_all("tr")
            for row in rows[1:]:  # Skip header row
                cols = row.query_selector_all("td")
                if len(cols) < 2:
                    continue
                city_link = cols[0].query_selector("a")
                if city_link is None:
                    continue
                city_name = city_link.inner_text().strip()
                city_href = city_link.get_attribute("href")
                city_count = cols[1].inner_text().strip()
                
                cities.append({
                    "City": city_name,
                    "Count": city_count,
                    "URL": city_href  # Note: This is a relative URL.
                })
        except Exception as e:
            print(f"Error extracting cities: {e}")
        
        # Save cities data to Excel
        if cities:
            df_cities = pd.DataFrame(cities)
            cities_file = state_path+"_cities.xlsx"
            df_cities.to_excel(cities_file, index=False)
            print(f"Saved cities data to '{cities_file}'.")
        else:
            print("No cities found.")
        
        # Extract datacenter details from each city's page
        datacenters = []
        for city in cities:
            city_name = city["City"]
            city_relative_url = city["URL"]
            # Convert the relative URL to an absolute URL:
            city_url = urljoin(base_url, city_relative_url)
            print(f"\nProcessing city: {city_name} ({city_url})")
            try:
                page.goto(city_url)
                time.sleep(random.uniform(2, 4))
                page.wait_for_selector(".ui.centered.cards", timeout=30000)
                cards_container = page.query_selector(".ui.centered.cards")
                cards = cards_container.query_selector_all(".ui.card")
                
                print(f"  Found {len(cards)} datacenters for {city_name}.")
                for card in cards:
                    try:
                        header = card.query_selector(".header")
                        description = card.query_selector(".description")
                        dc_name = header.inner_text().strip() if header else "N/A"
                        dc_desc = description.inner_text().strip() if description else "N/A"
                        dc_href = card.get_attribute("href") or "N/A"
                        print(f"    {dc_name} - {dc_desc} ({dc_href})")
                        datacenters.append({
                            "City": city_name,
                            "Datacenter Name": dc_name,
                            "Location": dc_desc,
                            "Detail URL": dc_href
                        })
                    except Exception as inner_e:
                        print(f"  Error extracting datacenter details: {inner_e}")
            except PlaywrightTimeoutError:
                print(f"  Timeout while loading {city_url}. Skipping this city.")
            except Exception as e:
                print(f"  Error processing {city_url}: {e}")
        
        # Save datacenter details to Excel
        if datacenters:
            df_datacenters = pd.DataFrame(datacenters)
            datacenters_file = state_path+"_datacenters_details.xlsx"
            df_datacenters.to_excel(datacenters_file, index=False)
            print(f"Saved datacenter details to '{datacenters_file}'.")
        else:
            print("No datacenter details found.")
        
        browser.close()
        print("Playwright session closed.")

if __name__ == "__main__":
    main()
