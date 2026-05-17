from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import time
import random
from urllib.parse import urljoin
import os

# ------------------------------
# Helper function: Get cell value
# ------------------------------
def get_cell_value(cell):
    """
    Checks if the cell contains an <i> element with a checkmark or close icon.
    Returns 'Yes' for checkmark, 'No' for close, or the cell's text otherwise.
    """
    try:
        i_element = cell.locator("i")
        classes = i_element.get_attribute("class")
        if "checkmark" in classes:
            return "Yes"
        elif "close" in classes:
            return "No"
    except:
        pass
    return cell.inner_text().strip()

# ------------------------------
# Main scraping function
# ------------------------------
def scrape_datacenters():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        state_name = "california"
        input_file = state_name + "_datacenters_details.xlsx"
        df = pd.read_excel(input_file)
        
        output_file = state_name + "_datacenters_specs.xlsx"
        
        for index, row in df.iterrows():
            datacenter_name = row["Datacenter Name"]
            specs_url = row["Detail URL"].rstrip("/") + "/specs/"
            print(f"Processing: {datacenter_name} -> {specs_url}")
            
            # Retry mechanism
            max_attempts = 3
            attempt = 0
            while attempt < max_attempts:
                try:
                    base_url = "https://www.datacentermap.com"
                    specs_url = urljoin(base_url, specs_url)
                    print(f"Attempt {attempt+1} for {specs_url}")
                    page.goto(specs_url, timeout=5000)  # 30 sec timeout
                    time.sleep(random.uniform(3, 6))
                    break
                except PlaywrightTimeoutError:
                    print(f"Attempt {attempt+1} failed for {specs_url}")
                    attempt += 1
                    time.sleep(3)
            else:
                print(f"Skipping {specs_url} after {max_attempts} failed attempts.")
                continue
            
            # Extract key statistics
            energy, area, established = None, None, None
            try:
                stats = page.locator(".ui.three.statistics .ui.statistic")
                if stats.count() >= 3:
                    energy = stats.nth(0).locator(".label").inner_text().strip()
                    area = stats.nth(1).locator(".label").inner_text().strip()
                    established = stats.nth(2).locator(".label").inner_text().strip()
                # Skip if any key data is missing
                if not energy or not area:
                    print(f"Skipping {specs_url} due to missing key statistics.")
                    continue
            except:
                print(f"Error extracting key statistics for {specs_url}")
                continue
            
            # Extract category-wise specifications
            categories = {}
            try:
                sections = page.locator(".ui.stackable.grid .eight.wide.column")
                for i in range(sections.count()):
                    section = sections.nth(i)
                    header_elem = section.locator(".ui.horizontal.divider")
                    category = header_elem.inner_text().strip()
                    rows = section.locator("tr")
                    category_data = {}
                    for j in range(rows.count()):
                        row = rows.nth(j)
                        cells = row.locator("td")
                        if cells.count() == 2:
                            key = cells.nth(0).inner_text().strip()
                            value = get_cell_value(cells.nth(1))
                            category_data[key] = value
                    if category:
                        categories[category] = category_data
            except:
                print(f"Error extracting category data for {specs_url}")
            
            # Store extracted data and append to file
            data = {
                "Datacenter Name": datacenter_name,
                "Energy": energy,
                "Area": area,
                "Established": established,
                **{cat: str(data) for cat, data in categories.items()}  # Convert dict to string
            }
            
            df_new = pd.DataFrame([data])
            if not os.path.exists(output_file):
                df_new.to_excel(output_file, index=False)
            else:
                with pd.ExcelWriter(output_file, mode='a', if_sheet_exists='overlay') as writer:
                    df_new.to_excel(writer, index=False, header=False, startrow=writer.sheets['Sheet1'].max_row)
            
            time.sleep(random.uniform(8, 9)) 
        
        browser.close()
        print(f"Scraping complete. Data saved to: {output_file}")

# Run the scraper
scrape_datacenters()
