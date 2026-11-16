"""
Option 30: GP Paints Product Catalogue Upload
==============================================
Features:
  - Uploads GP Paints products extracted from PDF catalogues:
      1. GLANZA Premium Wall Putty (40kg & 20kg packs)
      2. Elegant Sparkling White Wash Waterproof (20kg & 5kg packs)
  - Uses professional 1000x1000 product images generated in 'gp paints/product_images/'
  - Category matching with fallback for 'Wall Putty', 'White Wash', 'Paints', etc.
  - Form fields automated: ProductName, CategoryId, SubCategory, ProductDescription, Price, DiscountPrice, StockQuantity, Point
  - Reliable modal-scoped file upload bypassing hidden input limitations
  - Progress tracker (gp_paints_upload_progress.json) for seamless resume
"""
import json
import os
import sys
import time
import logging
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Add parent / automation directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_automation import VendorPortalAutomation

logger = logging.getLogger(__name__)

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
GP_DIR = ROOT_DIR / "gp paints"
DATA_FILE = GP_DIR / "gp_paints_products.json"
PROGRESS_FILE = Path(__file__).parent / "gp_paints_upload_progress.json"

# Dashboard Selectors
PRODUCT_CATALOGUE_MENU = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.grid.grid-cols-1.md\:grid-cols-2.lg\:grid-cols-3.gap-5 > button:nth-child(6) > h3"
ADD_PRODUCT_BTN = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.bg-white.dark\:bg-card.rounded-xl.border-2.border-gray-100.dark\:border-white\/10.overflow-hidden.relative > div.px-6.py-4.flex.items-center.justify-between.border-b.border-gray-100.dark\:border-white\/10.bg-indigo-50\/50.dark\:bg-indigo-500\/5 > button"
PUBLISH_BTN = r"#root > div.flex.h-screen.bg-gray-50.dark\:bg-dark-900.overflow-hidden.text-gray-900.dark\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\:bg-card.w-full.rounded-xl.shadow-2xl.dark\:shadow-none.border.border-transparent.dark\:border-white\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.border-t.border-gray-50.dark\:border-white\/5.flex.justify-end.space-x-4.flex-shrink-0 > button.inline-flex.items-center.justify-center.transition-all.cursor-pointer.disabled\:opacity-50.disabled\:cursor-not-allowed.gap-2.focus\:outline-none.font-semibold.rounded-lg.active\:scale-\[0\.98\].disabled\:active\:scale-100.focus\:ring-2.focus\:ring-offset-2.px-6.py-3\.5.text-sm.bg-indigo-600.text-white.hover\:bg-indigo-700.shadow-lg.shadow-indigo-200.dark\:shadow-none.focus\:ring-indigo-500"

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

def load_progress() -> set:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("uploaded", []))
        except Exception:
            return set()
    return set()

def save_progress(uploaded_set: set):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"uploaded": list(uploaded_set)}, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save progress: {e}")

def run_gp_paints_product_upload(email: str, password: str) -> bool:
    logger.info("=" * 60)
    logger.info("STARTING GP PAINTS PRODUCT CATALOGUE UPLOAD (Option 30)")
    logger.info("=" * 60)

    if not DATA_FILE.exists():
        logger.error(f"GP Paints data file not found: {DATA_FILE}")
        return False

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    uploaded_done = load_progress()
    logger.info(f"Loaded {len(products)} GP Paints products. Already uploaded: {len(uploaded_done)}")

    try:
        with VendorPortalAutomation(email, password, headless=False) as automation:
            driver = automation.driver
            wait = WebDriverWait(driver, 15)

            # Login
            if not automation.login():
                logger.error("Login failed. Aborting.")
                return False
            time.sleep(2)

            # Navigate to Product Catalogue
            logger.info("Navigating to Product Catalogue...")
            app_settings_url = getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings")
            driver.get(app_settings_url)
            time.sleep(3)

            try:
                menu_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PRODUCT_CATALOGUE_MENU)))
                menu_item.click()
                time.sleep(2)
            except Exception:
                try:
                    xpath = "//h3[contains(text(), 'Product Catalogue') or contains(text(), 'Product Catalog')]"
                    menu_item = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    menu_item.click()
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Failed to navigate to Product Catalogue: {e}")
                    return False

            successful = 0
            failed = 0

            for index, row in enumerate(products):
                product_name = row.get("product name", "").strip()
                if not product_name or product_name in uploaded_done:
                    logger.info(f"Skipping already uploaded product: {product_name}")
                    continue

                logger.info(f"\nProcessing GP Product [{index+1}/{len(products)}]: {product_name}")

                try:
                    # Click Add New Product
                    add_btn = None
                    try:
                        add_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ADD_PRODUCT_BTN)))
                    except Exception:
                        btn_xpath = "//button[contains(., 'Add New Product') or contains(., 'Add Product')]"
                        add_btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))

                    driver.execute_script("arguments[0].scrollIntoView();", add_btn)
                    time.sleep(1)
                    add_btn.click()
                    time.sleep(2)

                    # 1. Upload Image
                    img_path = row.get("image_path", "")
                    if img_path and os.path.exists(img_path):
                        abs_img_path = str(Path(img_path).resolve())
                        logger.info(f"  Uploading image: {Path(abs_img_path).name}")
                        try:
                            file_input = None
                            modal_els = driver.find_elements(By.CSS_SELECTOR, "div.fixed.inset-0")
                            if modal_els:
                                modal_inputs = modal_els[-1].find_elements(By.CSS_SELECTOR, "input[type='file']")
                                if modal_inputs:
                                    file_input = modal_inputs[-1]

                            if not file_input:
                                space_y_inputs = driver.find_elements(By.CSS_SELECTOR, "div.space-y-1\\.5 input[type='file'], div.space-y-1.5 input[type='file']")
                                if space_y_inputs:
                                    file_input = space_y_inputs[-1]

                            if not file_input:
                                all_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                                for fi in all_inputs:
                                    fi_id = fi.get_attribute("id") or ""
                                    if "chatbot" not in fi_id.lower():
                                        file_input = fi
                                        break
                                if not file_input and all_inputs:
                                    file_input = all_inputs[0]

                            if file_input:
                                try:
                                    driver.execute_script("""
                                        arguments[0].style.cssText = 'display:block !important; visibility:visible !important;'
                                            + 'opacity:1 !important; width:100px !important; height:30px !important;'
                                            + 'position:fixed !important; top:0 !important; left:0 !important; z-index:999999;';
                                    """, file_input)
                                except Exception:
                                    pass

                                try:
                                    driver.execute_script("arguments[0].value = '';", file_input)
                                except Exception:
                                    pass

                                file_input.send_keys(abs_img_path)

                                try:
                                    driver.execute_script("""
                                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                    """, file_input)
                                except Exception:
                                    pass

                                time.sleep(2)
                                logger.info(f"  ✓ Image input set: {Path(abs_img_path).name}")
                            else:
                                logger.warning("  No file input element found for image upload.")
                        except Exception as img_err:
                            logger.error(f"  Error uploading image: {img_err}")
                    else:
                        logger.warning(f"  Image file does not exist: {img_path}")

                    # 2. Fill Form Fields
                    for field_key, input_id in FIELDS.items():
                        val = str(row.get(field_key, "")).strip()

                        if field_key == "category name":
                            try:
                                select_elem = wait.until(EC.presence_of_element_located((By.ID, input_id)))
                                select = Select(select_elem)
                                matched = False
                                for option in select.options:
                                    opt_text = option.text.strip().lower()
                                    if val.lower() == opt_text or val.lower() in opt_text or opt_text in val.lower():
                                        select.select_by_visible_text(option.text)
                                        matched = True
                                        logger.info(f"  Selected category: {option.text}")
                                        break
                                if not matched:
                                    logger.warning(f"  Category '{val}' not found in dropdown. Selecting first available.")
                                    if len(select.options) > 1:
                                        select.select_by_index(1)
                            except Exception as cat_err:
                                logger.error(f"  Error selecting category: {cat_err}")
                        else:
                            try:
                                input_elem = wait.until(EC.presence_of_element_located((By.ID, input_id)))
                                driver.execute_script("arguments[0].scrollIntoView();", input_elem)
                                input_elem.clear()
                                input_elem.send_keys(val)
                            except Exception as f_err:
                                logger.error(f"  Error filling {field_key} ({input_id}): {f_err}")

                    # 3. Click Publish
                    logger.info("  Publishing product...")
                    publish_btn = None
                    try:
                        publish_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PUBLISH_BTN)))
                    except Exception:
                        p_xpath = "//button[contains(., 'Publish') or contains(., 'Save')]"
                        publish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, p_xpath)))

                    driver.execute_script("arguments[0].scrollIntoView();", publish_btn)
                    time.sleep(1)
                    publish_btn.click()
                    time.sleep(3)

                    # Mark done & save progress
                    uploaded_done.add(product_name)
                    save_progress(uploaded_done)
                    successful += 1
                    logger.info(f"  ✓ Success: {product_name}")

                except Exception as p_err:
                    logger.error(f"  ✗ Failed product '{product_name}': {p_err}")
                    failed += 1
                    try:
                        driver.refresh()
                        time.sleep(4)
                        app_settings_url = getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings")
                        driver.get(app_settings_url)
                        time.sleep(2)
                        menu_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PRODUCT_CATALOGUE_MENU)))
                        menu_item.click()
                        time.sleep(2)
                    except Exception:
                        pass

            logger.info("=" * 60)
            logger.info(f"GP PAINTS CATALOGUE UPLOAD SUMMARY")
            logger.info(f"  Total Processed In This Run : {successful}")
            logger.info(f"  Failed                      : {failed}")
            logger.info(f"  Total In Progress Tracker   : {len(uploaded_done)} / {len(products)}")
            logger.info("=" * 60)
            return True

    except Exception as fatal_e:
        logger.error(f"Fatal error during GP Paints product upload: {fatal_e}", exc_info=True)
        return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    email = os.getenv("VENDOR_EMAIL", "")
    password = os.getenv("VENDOR_PASSWORD", "")
    if email and password:
        run_gp_paints_product_upload(email, password)
    else:
        logger.error("VENDOR_EMAIL and VENDOR_PASSWORD must be provided.")

