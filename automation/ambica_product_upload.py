import os
import sys
import time
import logging
import csv
import urllib.request
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_automation import VendorPortalAutomation

logger = logging.getLogger(__name__)

# Constants
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/11t59mHI3fHS-aqdQZ9IXtKJvEQOtIi5BdYgsQNj3mUE/export?format=csv"
IMAGE_DIR = Path(r"c:\Users\admin\Desktop\newbldashboardproject\bldashabordautomation\ambica cables")

# Selectors from user request
PRODUCT_CATALOGUE_MENU = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.grid.grid-cols-1.md\:grid-cols-2.lg\:grid-cols-3.gap-5 > button:nth-child(6) > h3"
ADD_PRODUCT_BTN = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.bg-white.dark\:bg-card.rounded-xl.border-2.border-gray-100.dark\:border-white\/10.overflow-hidden.relative > div.px-6.py-4.flex.items-center.justify-between.border-b.border-gray-100.dark\:border-white\/10.bg-indigo-50\/50.dark\:bg-indigo-500\/5 > button"
IMAGE_UPLOAD_BTN = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\:bg-card.w-full.rounded-xl.shadow-2xl.dark\:shadow-none.border.border-transparent.dark\:border-white\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.overflow-y-auto.flex-grow.max-h-\[50vh\].text-text-light.dark\:text-text-dark > div > div.space-y-1\.5 > div > button"
PUBLISH_BTN = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\:bg-card.w-full.rounded-xl.shadow-2xl.dark\:shadow-none.border.border-transparent.dark\:border-white\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.border-t.border-gray-50.dark\:border-white\/5.flex.justify-end.space-x-4.flex-shrink-0 > button.inline-flex.items-center.justify-center.transition-all.cursor-pointer.disabled\:opacity-50.disabled\:cursor-not-allowed.gap-2.focus\:outline-none.font-semibold.rounded-lg.active\:scale-\[0\.98\].disabled\:active\:scale-100.focus\:ring-2.focus\:ring-offset-2.px-6.py-3\.5.text-sm.bg-indigo-600.text-white.hover\:bg-indigo-700.shadow-lg.shadow-indigo-200.dark\:shadow-none.focus\:ring-indigo-500"

# Form field IDs
FIELDS = {
    "product name": "ProductName",
    "category name": "CategoryId",
    "sub-classification": "SubCategory",
    "product narrative / description": "ProductDescription",
    "listing price (₹)": "Price",
    "offer price (₹)": "DiscountPrice",
    "unit inventory": "StockQuantity",
    "loyalty yield": "Point"
}

def find_image_for_product(product_name: str) -> str:
    """Attempt to find a matching image for the product name."""
    if not IMAGE_DIR.exists():
        logger.error(f"Image directory not found: {IMAGE_DIR}")
        return None

    # Clean product name for matching
    safe_name = str(product_name).lower().strip().replace(" ", "")

    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        # Try direct match
        for file in IMAGE_DIR.rglob(f"*{ext}"):
            folder_clean = file.parent.name.lower().replace(" ", "")
            if folder_clean in safe_name or safe_name in folder_clean:
                return str(file)

    logger.warning(f"No image found for product '{product_name}' in {IMAGE_DIR}")
    return None

def fetch_product_data() -> list:
    """Fetch product data from Google Sheets."""
    try:
        logger.info(f"Fetching data from {GOOGLE_SHEET_URL}")
        req = urllib.request.Request(GOOGLE_SHEET_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            lines = [line.decode('utf-8') for line in response.readlines()]
            reader = csv.DictReader(lines)
            
            # Standardize column names to lower case and strip whitespace
            # Create a new list of dicts with cleaned keys
            cleaned_data = []
            for row in reader:
                cleaned_row = {str(k).strip().lower(): str(v).strip() for k, v in row.items()}
                cleaned_data.append(cleaned_row)
                
            logger.info(f"Successfully fetched {len(cleaned_data)} rows.")
            return cleaned_data
    except Exception as e:
        logger.error(f"Failed to fetch Google Sheet data: {e}")
        return None

def run_ambica_product_upload(email: str, password: str) -> bool:
    """Main execution function for Ambica Cable product catalogue upload."""
    logger.info("=" * 60)
    logger.info("STARTING AMBICA CABLE PRODUCT CATALOGUE UPLOAD (Option 21)")
    logger.info("=" * 60)

    # 1. Fetch data
    data = fetch_product_data()
    if not data:
        logger.error("No data available to process.")
        return False

    # Check required columns on the first row
    if len(data) > 0:
        required_cols = list(FIELDS.keys())
        available_cols = list(data[0].keys())
        missing_cols = [c for c in required_cols if c not in available_cols]
        if missing_cols:
            logger.error(f"Missing required columns in Google Sheet: {missing_cols}")
            logger.info(f"Available columns: {available_cols}")
            return False

    try:
        with VendorPortalAutomation(email, password, headless=False) as automation:
            driver = automation.driver
            wait = WebDriverWait(driver, 15)

            # 2. Login
            if not automation.login():
                logger.error("Login failed. Aborting.")
                return False
            time.sleep(2)

            # 3. Navigate to App Settings -> Product Catalogue
            logger.info("Navigating to Product Catalogue...")
            
            # Click App Settings in side menu (assuming VendorPortalAutomation has a method or we can find it)
            # We'll use the provided CSS selector for the Product Catalogue menu item directly, assuming it's visible or on the dashboard
            try:
                # First ensure we are on the main dashboard where App Settings might be, or navigate to App Settings
                app_settings_url = getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings")
                driver.get(app_settings_url)
                time.sleep(3)
                
                menu_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PRODUCT_CATALOGUE_MENU)))
                menu_item.click()
                time.sleep(2)
            except Exception as e:
                logger.error(f"Failed to click Product Catalogue menu item: {e}")
                # Try finding by text as fallback
                try:
                    xpath = "//h3[contains(text(), 'Product Catalogue') or contains(text(), 'Product Catalog')]"
                    menu_item = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    menu_item.click()
                    time.sleep(2)
                except Exception as e2:
                    logger.error(f"Fallback navigation failed: {e2}")
                    return False

            successful = 0
            failed = 0

            # 4. Process each product
            for index, row in enumerate(data):
                product_name = str(row.get('product name', '')).strip()
                if not product_name or product_name.lower() == 'nan' or product_name == 'None':
                    continue

                logger.info(f"\nProcessing Product [{index+1}/{len(data)}]: {product_name}")

                try:
                    # Click Add New Product
                    add_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ADD_PRODUCT_BTN)))
                    driver.execute_script("arguments[0].scrollIntoView();", add_btn)
                    time.sleep(1)
                    add_btn.click()
                    time.sleep(2)

                    # Handle Image Upload
                    image_path = find_image_for_product(product_name)
                    if image_path:
                        logger.info(f"Uploading image: {image_path}")
                        try:
                            # Instead of clicking the button and dealing with OS dialog, try to find the hidden input[type='file']
                            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                            if file_inputs:
                                file_inputs[0].send_keys(image_path)
                                time.sleep(2)
                            else:
                                logger.warning("No file input found for image upload.")
                        except Exception as e:
                            logger.error(f"Error during image upload: {e}")
                    else:
                        logger.warning(f"Skipping image upload for {product_name}")

                    # Fill fields
                    for field_key, input_id in FIELDS.items():
                        val = str(row.get(field_key, '')).strip()
                        if val.lower() == 'nan' or val == 'None':
                            val = ""
                            
                        # If it's CategoryName, it's a dropdown based on user instructions
                        if field_key == "category name":
                            try:
                                select_elem = wait.until(EC.presence_of_element_located((By.ID, input_id)))
                                select = Select(select_elem)
                                
                                # Try matching by visible text
                                matched = False
                                for option in select.options:
                                    if option.text.strip().lower() == val.lower():
                                        select.select_by_visible_text(option.text)
                                        matched = True
                                        break
                                
                                if not matched:
                                    logger.warning(f"Category '{val}' not found in dropdown for '{product_name}'. Selecting first option if available.")
                                    if len(select.options) > 1: # Index 0 might be placeholder
                                        select.select_by_index(1)
                                        
                            except Exception as e:
                                logger.error(f"Error selecting category '{val}': {e}")
                                # Try clicking div based dropdown if standard Select fails
                                try:
                                    dropdown = driver.find_element(By.ID, input_id)
                                    dropdown.click()
                                    time.sleep(1)
                                    option_xpath = f"//div[contains(text(), '{val}')] | //li[contains(text(), '{val}')]"
                                    option = driver.find_element(By.XPATH, option_xpath)
                                    option.click()
                                except Exception as inner_e:
                                    logger.error(f"Custom dropdown selection also failed: {inner_e}")
                        else:
                            # Standard text input
                            try:
                                input_elem = wait.until(EC.presence_of_element_located((By.ID, input_id)))
                                driver.execute_script("arguments[0].scrollIntoView();", input_elem)
                                input_elem.clear()
                                input_elem.send_keys(val)
                            except Exception as e:
                                logger.error(f"Error filling {field_key} ({input_id}): {e}")

                    # Click Publish
                    logger.info("Clicking Publish button...")
                    publish_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PUBLISH_BTN)))
                    driver.execute_script("arguments[0].scrollIntoView();", publish_btn)
                    time.sleep(1)
                    publish_btn.click()
                    time.sleep(3) # Wait for save

                    successful += 1
                    logger.info(f"Successfully processed: {product_name}")

                    # The popup might close automatically or we might need to close it / wait for dashboard to return
                    # Assuming it returns to product list
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Failed to process product '{product_name}': {e}")
                    failed += 1
                    # Attempt to refresh or close modal to recover state for next product
                    try:
                        driver.refresh()
                        time.sleep(5)
                        # Re-navigate if necessary
                        menu_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PRODUCT_CATALOGUE_MENU)))
                        menu_item.click()
                        time.sleep(2)
                    except:
                        pass

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("AMBICA PRODUCT UPLOAD SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful: {successful}")
            logger.info(f"✗ Failed: {failed}")
            logger.info(f"Total processed: {len(data)}")
            logger.info("=" * 60)

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error during Ambica product upload: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
