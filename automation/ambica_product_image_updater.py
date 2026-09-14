import os
import sys
import time
import logging
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_automation import VendorPortalAutomation

logger = logging.getLogger(__name__)

IMAGE_DIR = Path(r"c:\Users\admin\Desktop\newbldashboardproject\bldashabordautomation\ambica cables")

# Selectors
PRODUCT_CATALOGUE_MENU = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.grid.grid-cols-1.md\:grid-cols-2.lg\:grid-cols-3.gap-5 > button:nth-child(6) > h3"
PUBLISH_BTN = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\:bg-card.w-full.rounded-xl.shadow-2xl.dark\:shadow-none.border.border-transparent.dark\:border-white\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.border-t.border-gray-50.dark\:border-white\/5.flex.justify-end.space-x-4.flex-shrink-0 > button.inline-flex.items-center.justify-center.transition-all.cursor-pointer.disabled\:opacity-50.disabled\:cursor-not-allowed.gap-2.focus\:outline-none.font-semibold.rounded-lg.active\:scale-\[0\.98\].disabled\:active\:scale-100.focus\:ring-2.focus\:ring-offset-2.px-6.py-3\.5.text-sm.bg-indigo-600.text-white.hover\:bg-indigo-700.shadow-lg.shadow-indigo-200.dark\:shadow-none.focus\:ring-indigo-500"

def clean_string_for_match(s: str) -> str:
    """Normalize string for fuzzy matching (e.g. 40/76 -> 40_76)"""
    return str(s).lower().strip().replace("/", "_").replace(" ", "").replace("-", "")

def find_image_for_identity(identity: str) -> str:
    """Attempt to find an image matching the identity (with fuzzy matching)"""
    if not identity or not str(identity).strip():
        return None
    
    if not IMAGE_DIR.exists():
        return None
        
    safe_identity = clean_string_for_match(identity)
    
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        for file in IMAGE_DIR.glob(f"*{ext}"):
            file_clean = clean_string_for_match(file.stem)
            if safe_identity in file_clean or file_clean in safe_identity:
                return str(file)
    return None

def run_ambica_image_updater(email: str, password: str) -> bool:
    logger.info("=" * 60)
    logger.info("STARTING AMBICA CABLE PRODUCT IMAGE UPDATER (Option 22)")
    logger.info("=" * 60)
    
    if not IMAGE_DIR.exists():
        logger.error(f"Image directory not found: {IMAGE_DIR}")
        return False
        
    try:
        with VendorPortalAutomation(email, password, headless=False) as automation:
            driver = automation.driver
            wait = WebDriverWait(driver, 15)

            if not automation.login():
                logger.error("Login failed. Aborting.")
                return False
            time.sleep(2)

            logger.info("Navigating to Product Catalogue...")
            try:
                app_settings_url = getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings")
                driver.get(app_settings_url)
                time.sleep(3)
                menu_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PRODUCT_CATALOGUE_MENU)))
                menu_item.click()
                time.sleep(3)
            except Exception as e:
                logger.error(f"Failed to navigate to Product Catalogue: {e}")
                return False

            # Wait for table to load
            try:
                table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            except Exception:
                logger.error("Could not find product table.")
                return False
                
            # Process up to 26 products (or whatever is in the table)
            # Since rows might refresh, we'll re-fetch them on each iteration
            successful = 0
            failed = 0
            
            # Find total rows initially to know bounds
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
            total_rows = min(len(rows), 26)
            logger.info(f"Found {len(rows)} products in table. Will process up to {total_rows}.")
            
            for i in range(total_rows):
                logger.info(f"Processing row {i+1}/{total_rows}...")
                
                # Re-fetch rows because DOM might have changed after modal closes
                rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                if i >= len(rows):
                    logger.warning(f"Row {i} is out of bounds (only {len(rows)} rows). Stopping.")
                    break
                    
                row = rows[i]
                row_idx = i + 1
                
                # Extract product name using exact selector
                name_selector = rf"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.bg-white.dark\:bg-card.rounded-xl.border-2.border-gray-100.dark\:border-white\/10.overflow-hidden.relative > div:nth-child(2) > div > table > tbody > tr:nth-child({row_idx}) > td:nth-child(2) > div > div:nth-child(2) > div.text-sm.font-bold.text-gray-900.dark\:text-white.group-hover\:text-indigo-600.transition-colors.leading-tight"
                try:
                    name_elem = driver.find_element(By.CSS_SELECTOR, name_selector)
                    row_text = name_elem.text.strip()
                except Exception as e:
                    logger.error(f"Could not extract product name for row {row_idx}. Trying fallback row text.")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    row_text = " ".join([c.text for c in cells])
                    
                logger.info(f"Target product identity for row {row_idx}: {row_text}")
                
                matched_image = None
                matched_name = None
                
                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    for file in IMAGE_DIR.rglob(f"*{ext}"):
                        folder_name = file.parent.name
                        file_clean = clean_string_for_match(folder_name)
                        # We need a decent sized stem to avoid matching empty or 1-char strings
                        if len(file_clean) > 1:
                            # Clean the row text similarly for matching
                            row_clean = clean_string_for_match(row_text)
                            if file_clean in row_clean:
                                matched_image = str(file)
                                matched_name = folder_name
                                break
                    if matched_image:
                        break
                        
                if not matched_image:
                    logger.info(f"No matching image found for row {i+1}. Skipping.")
                    continue
                    
                logger.info(f"Found match: '{matched_name}' -> {matched_image}")
                
                # Click Edit button in this row using the provided exact selectors
                try:
                    # 1. Click the Action button
                    action_btn_selector = rf"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.bg-white.dark\:bg-card.rounded-xl.border-2.border-gray-100.dark\:border-white\/10.overflow-hidden.relative > div:nth-child(2) > div > table > tbody > tr:nth-child({row_idx}) > td.px-6.py-4.text-right.sticky.right-0.bg-white.dark\:bg-dark.group-hover\:bg-gray-50.dark\:group-hover\:bg-dark-900\/30.z-20.focus-within\:z-50.border-l.border-gray-100.dark\:border-gray-800.shadow-\[-12px_0_15px_-10px_rgba\(0\,0\,0\,0\.05\)\].dark\:shadow-none > div > button"
                    action_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, action_btn_selector)))
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action_btn)
                    time.sleep(1)
                    action_btn.click()
                    time.sleep(1) # wait for dropdown to appear
                    
                    # 2. Click the Edit button in the dropdown
                    edit_btn_selector = rf"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.bg-white.dark\:bg-card.rounded-xl.border-2.border-gray-100.dark\:border-white\/10.overflow-hidden.relative > div:nth-child(2) > div > table > tbody > tr:nth-child({row_idx}) > td.px-6.py-4.text-right.sticky.right-0.bg-white.dark\:bg-dark.group-hover\:bg-gray-50.dark\:group-hover\:bg-dark-900\/30.z-20.focus-within\:z-50.border-l.border-gray-100.dark\:border-gray-800.shadow-\[-12px_0_15px_-10px_rgba\(0\,0\,0\,0\.05\)\].dark\:shadow-none > div > div > div > button:nth-child(1)"
                    edit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, edit_btn_selector)))
                    edit_btn.click()
                    time.sleep(3) # wait for modal
                    
                    # Upload image
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    if file_inputs:
                        file_inputs[0].send_keys(matched_image)
                        time.sleep(2)
                    else:
                        logger.warning("No file input found to upload image.")
                        
                    # Click Update/Publish
                    publish_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PUBLISH_BTN)))
                    driver.execute_script("arguments[0].scrollIntoView();", publish_btn)
                    time.sleep(1)
                    publish_btn.click()
                    time.sleep(3)
                    
                    successful += 1
                    logger.info(f"Successfully updated row {i+1} with '{matched_name}'")
                    
                except Exception as e:
                    logger.error(f"Failed to update row {i+1}: {e}")
                    failed += 1
                    # Refresh to clear bad state
                    driver.refresh()
                    time.sleep(5)
                    try:
                        app_settings_url = getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings")
                        driver.get(app_settings_url)
                        time.sleep(3)
                        menu_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PRODUCT_CATALOGUE_MENU)))
                        menu_item.click()
                        time.sleep(3)
                    except:
                        pass
                        
            logger.info("\n" + "=" * 60)
            logger.info("AMBICA IMAGE UPDATER SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful: {successful}")
            logger.info(f"✗ Failed: {failed}")
            logger.info("=" * 60)
            return True
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
