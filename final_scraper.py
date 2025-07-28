import time
import csv
import os # Needed to check if the file exists

URL = "https://www.emiratesauction.com/plates/fujairah/online"

# Define the CSV file name and headers
csv_file = "fujairah_plates_data.csv"
fieldnames = ["plate", "price", "bids"]

# --- NEW LOGIC: Read existing data from CSV if it exists ---
existing_data = {}
if os.path.exists(csv_file):
    print(f"Loading existing data from {csv_file}...")
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            existing_data[row['plate']] = row
    print(f"Loaded {len(existing_data)} records.")

# --- Selenium WebDriver Setup ---
print("Setting up WebDriver...")
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import NoSuchElementException
    
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

# --- Scrolling Logic ---
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

# --- Scraping and Updating Logic ---
print("Finding auction items to update data...")
try:
    item_containers = driver.find_elements(By.CSS_SELECTOR, "div.list-card-container")
    print(f"Found {len(item_containers)} items on the page. Updating data...")

    for item in item_containers:
        try:
            plate_img = item.find_element(By.CSS_SELECTOR, "img[alt='plate']")
            src = plate_img.get_attribute('src')
            if src:
                src_parts = src.split('/')
                plate_number = f"{src_parts[-2]} {src_parts[-1].replace('.png', '')}"

                price_span = item.find_element(By.XPATH, ".//span[contains(@class, 'uae-symbol')]/parent::span/following-sibling::span")
                price = price_span.text.strip()
                
                bids_span = item.find_element(By.XPATH, ".//img[@alt='Bids ']/following-sibling::div/span[2]")
                bids = bids_span.text.strip()
                
                # --- NEW LOGIC: Update or add the plate data to our dictionary ---
                existing_data[plate_number] = {"plate": plate_number, "price": price, "bids": bids}

        except NoSuchElementException:
            continue # Skip if an item is malformed
        except Exception as e:
            print(f"An error occurred processing an item: {e}")
            
except Exception as e:
    print(f"An error occurred while finding item containers: {e}")
finally:
    driver.quit()

# --- NEW LOGIC: Write the updated and preserved data back to the CSV ---
if existing_data:
    print(f"Saving {len(existing_data)} total records to '{csv_file}'...")
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        # Write the values from our dictionary
        writer.writerows(existing_data.values())

    print("\n✅ Success! CSV file has been updated.")
else:
    print("\n⚠️ No data was found or updated.")
