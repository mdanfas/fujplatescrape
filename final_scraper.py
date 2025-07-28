import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

URL = "https://www.emiratesauction.com/plates/fujairah/online"

print("Setting up WebDriver...")
try:
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1200")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=service, options=options)
except Exception as e:
    print(f"Error setting up WebDriver: {e}")
    exit()

print(f"Loading page: {URL}")
driver.get(URL)
time.sleep(5)

print("Scrolling page to load all items...")
last_height = driver.execute_script("return document.body.scrollHeight")

for i in range(10): 
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        print("  Reached the bottom of the page.")
        break
    last_height = new_height

print("Finding auction items...")
try:
    item_containers = driver.find_elements(By.CSS_SELECTOR, "div.list-card-container")
    
    if not item_containers:
        print("Could not find any item containers. The script failed.")
        driver.quit()
        exit()
except Exception as e:
    print(f"An error occurred while finding item containers: {e}")
    driver.quit()
    exit()
    
print(f"Found {len(item_containers)} items. Extracting data...")
scraped_data = []

for item in item_containers:
    plate_number = "N/A"
    price = "N/A"
    bids = "N/A" # New variable for bids
    try:
        # --- Extract Plate Number ---
        plate_img = item.find_element(By.CSS_SELECTOR, "img[alt='plate']")
        src = plate_img.get_attribute('src')
        if src:
            src_parts = src.split('/')
            if len(src_parts) >= 2:
                plate_number = f"{src_parts[-2]} {src_parts[-1].replace('.png', '')}"

        # --- Extract Price ---
        price_span = item.find_element(By.XPATH, ".//span[contains(@class, 'uae-symbol')]/parent::span/following-sibling::span")
        price = price_span.text.strip()

        # --- NEW: Extract Number of Bids ---
        bids_span = item.find_element(By.XPATH, ".//img[@alt='Bids ']/following-sibling::div/span[2]")
        bids = bids_span.text.strip()

    except NoSuchElementException:
        pass # If an item is missing price/bids, it will be marked "N/A"
    except Exception as e:
        print(f"An error occurred processing an item: {e}")

    if plate_number != "N/A":
        # Add the new 'bids' data to the dictionary
        scraped_data.append({"plate": plate_number, "price": price, "bids": bids})

driver.quit()

if scraped_data:
    csv_file = "fujairah_plates_data.csv"
    # Add 'bids' to the header row
    fieldnames = ["plate", "price", "bids"]

    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scraped_data)

    print("\n✅ Success!")
    print(f"Data for {len(scraped_data)} plates has been saved to '{csv_file}'")
else:
    print("\n⚠️ No data was scraped.")