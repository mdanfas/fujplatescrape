import time
import csv
import os
import re
from datetime import datetime, timedelta

# --- Configuration ---
URL = "https://www.emiratesauction.com/plates/fujairah/online"
CSV_FILE = "fujairah_plates_data.csv"
FIELDNAMES = ["plate", "price", "bids", "time_left", "end_date"]

# --- Helper Function to Parse "Time Left" ---
def parse_time_left(time_str):
    """Parses a string like '4d : 3h : 4m' into a timedelta object."""
    days, hours, minutes = 0, 0, 0
    if 'd' in time_str:
        days_match = re.search(r'(\d+)\s*d', time_str)
        if days_match:
            days = int(days_match.group(1))
    if 'h' in time_str:
        hours_match = re.search(r'(\d+)\s*h', time_str)
        if hours_match:
            hours = int(hours_match.group(1))
    if 'm' in time_str:
        minutes_match = re.search(r'(\d+)\s*m', time_str)
        if minutes_match:
            minutes = int(minutes_match.group(1))
    return timedelta(days=days, hours=hours, minutes=minutes)

# --- Main Script Logic ---

# 1. Read existing data from CSV
existing_data = {}
if os.path.exists(CSV_FILE):
    print(f"Loading existing data from {CSV_FILE}...")
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            existing_data[row['plate']] = row
    print(f"Loaded {len(existing_data)} records.")

# 2. Setup Selenium
print("Setting up WebDriver...")
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1200")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=service, options=options)
except Exception as e:
    print(f"Error setting up WebDriver: {e}")
    exit()

# 3. Scrape the live data
any_plate_under_30_mins = False
all_plates_under_24_hours = True # Assume true until a plate proves otherwise
found_plates_count = 0

try:
    print(f"Loading page: {URL}")
    driver.get(URL)
    # Wait for the first item to be visible
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.list-card-container"))
    )

    # Scrolling is no longer needed as we wait for elements to load
    print("Finding auction items...")
    item_containers = driver.find_elements(By.CSS_SELECTOR, "div.list-card-container")
    found_plates_count = len(item_containers)

    if not item_containers:
        print("No item containers found on the page.")
    else:
        print(f"Found {found_plates_count} items. Processing...")
        for item in item_containers:
            try:
                plate_img = item.find_element(By.CSS_SELECTOR, "img[alt='plate']")
                src = plate_img.get_attribute('src')
                plate_number = "N/A"
                if src:
                    src_parts = src.split('/')
                    if len(src_parts) >= 2:
                        plate_number = f"{src_parts[-2]} {src_parts[-1].replace('.png', '')}"

                price_span = item.find_element(By.XPATH, ".//span[contains(@class, 'uae-symbol')]/parent::span/following-sibling::span")
                price = price_span.text.strip()
                
                bids_span = item.find_element(By.XPATH, ".//img[@alt='Bids ']/following-sibling::div/span[2]")
                bids = bids_span.text.strip()

                end_date_span = item.find_element(By.XPATH, ".//img[@alt='End Date ']/following-sibling::div/span[2]")
                end_date = end_date_span.text.strip()

                time_left_span = item.find_element(By.XPATH, ".//img[@alt='Time Left ']/following-sibling::div/span[2]")
                time_left_str = time_left_span.text.strip()
                
                # Check auction times for workflow triggers
                time_remaining = parse_time_left(time_left_str)
                if time_remaining > timedelta(days=1):
                    all_plates_under_24_hours = False
                if time_remaining < timedelta(minutes=30):
                    any_plate_under_30_mins = True

                # Update data
                existing_data[plate_number] = {
                    "plate": plate_number, 
                    "price": price, 
                    "bids": bids,
                    "time_left": time_left_str,
                    "end_date": end_date
                }
            except NoSuchElementException:
                continue # Skip malformed items
                
finally:
    driver.quit()

# 4. Save updated data back to CSV
if existing_data:
    print(f"Saving {len(existing_data)} total records to '{CSV_FILE}'...")
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(existing_data.values())
    print("Save complete.")
else:
    print("No data to save.")

# 5. Create trigger files for GitHub Actions
if all_plates_under_24_hours and found_plates_count > 0:
    print("TRIGGER: All plates are under 24 hours. Creating trigger_hourly.txt")
    with open("trigger_hourly.txt", "w") as f:
        f.write("true")

if any_plate_under_30_mins and found_plates_count > 0:
    print("TRIGGER: A plate is under 30 mins. Creating trigger_3_minutes.txt")
    with open("trigger_3_minutes.txt", "w") as f:
        f.write("true")

if found_plates_count == 0:
    print("TRIGGER: No plates found. Creating trigger_stop.txt")
    with open("trigger_stop.txt", "w") as f:
        f.write("true")

print("\n✅ Script finished.")
