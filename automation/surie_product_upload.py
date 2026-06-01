"""
Surie Product Upload Automation
Handles scanning local directory and uploading products to the new dashboard.
"""

import os
import time
import logging
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select

logger = logging.getLogger(__name__)

ROOT_DIR = Path("/home/adminmac/Desktop/newbldashboardproject/GRAPHICS CONTENT FOR SURIE POLEX REWARDS APP")

class SurieProductAutomation:
    """Automates the 'Add New Product' flow for Surie Products."""

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    def _select_dropdown_robust(self, select_el, text):
        """Select an option from a dropdown with case-insensitive and partial matching."""
        try:
            select = Select(select_el)
            options = select.options
            
            target = text.strip().lower()
            
            # 1. Try exact match (case-insensitive)
            for opt in options:
                if opt.text.strip().lower() == target:
                    select.select_by_visible_text(opt.text)
                    return True
            
            # 2. Try substring match (case-insensitive)
            for opt in options:
                opt_text = opt.text.strip().lower()
                if target in opt_text or opt_text in target:
                    select.select_by_visible_text(opt.text)
                    return True
            
            # 3. Fallback: try direct select
            select.select_by_visible_text(text)
            return True
        except Exception as e:
            logger.warning(f"    ⚠ Could not select '{text}' in dropdown: {e}")
            return False

    def navigate_to_product_management(self):
        """Navigate to App Setting -> Product Management."""
        try:
            # Selector provided by user for the 6th button (Product Management)
            selector = "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden > main > div.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3.gap-5 > button:nth-child(6) > h3"
            
            # Navigate to App Settings directly to be sure
            self.driver.get("https://app.vcqru.com/vendor/app-settings")
            time.sleep(3)
            
            btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            logger.info("✓ Navigated to Product Management")
            return True
        except Exception as e:
            logger.error(f"Navigation to product management failed: {e}")
            return False

    def get_uploaded_products(self):
        """Scrape names of already uploaded products from the table."""
        try:
            uploaded_names = set()
            logger.info("Scanning dashboard for already uploaded products...")
            
            # Wait for table to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2) # Give it a moment to render rows

            # We'll collect names from all pages if pagination exists
            while True:
                # Selector based on user provided path but generalized for all rows
                # tr:nth-child(1) -> tr
                name_selector = "table tbody tr td:nth-child(2) div div:nth-child(2) div.text-sm.font-bold"
                name_elements = self.driver.find_elements(By.CSS_SELECTOR, name_selector)
                
                for el in name_elements:
                    name = el.text.strip()
                    if name:
                        uploaded_names.add(name.lower())
                
                # Check for "Next" button in pagination
                try:
                    # Look for a next page button - usually containing an arrow or "Next"
                    next_btn = self.driver.find_elements(By.XPATH, "//button[.//span[contains(text(),'Next')] or contains(.,'Next')]")
                    if next_btn and next_btn[0].is_enabled():
                        # Check if it's the last page (disabled class or attribute)
                        if "disabled" in next_btn[0].get_attribute("class") or not next_btn[0].is_enabled():
                            break
                        self.driver.execute_script("arguments[0].click();", next_btn[0])
                        time.sleep(2)
                    else:
                        break
                except:
                    break
            
            logger.info(f"✓ Found {len(uploaded_names)} products already on dashboard.")
            return uploaded_names
        except Exception as e:
            logger.error(f"Failed to scrape uploaded products: {e}")
            return set()

    def add_product(self, product):
        """Fill and submit the 'Add New Product' form for Surie Products."""
        try:
            # 1. Click "Add New Product"
            add_btn_selector = "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden > main > div.space-y-8 > div.bg-white.dark\\:bg-card.rounded-xl.border-2.border-gray-100.dark\\:border-white\\/10.overflow-hidden > div.px-6.py-4.flex.items-center.justify-between.border-b.border-gray-100.dark\\:border-white\\/10.bg-indigo-50\\/50.dark\\:bg-indigo-500\\/5 > button"
            add_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, add_btn_selector)))
            self.driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(2)
            
            # 2. Image upload
            if product.get("image_path"):
                # Usually there's an input[type='file'] inside the modal
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                file_input.send_keys(str(product["image_path"]))
                time.sleep(2)
            
            # 3. Fill form fields
            self.wait.until(EC.presence_of_element_located((By.ID, "ProductName"))).send_keys(product["product_name"])
            
            # Category and SubCategory
            try:
                cat_el = self.driver.find_element(By.ID, "CategoryId")
                if cat_el.tag_name == "select":
                    self._select_dropdown_robust(cat_el, product["category"])
                else:
                    cat_el.send_keys(product["category"])
            except Exception as e:
                logger.warning(f"Could not set CategoryId: {e}")

            try:
                subcat_el = self.driver.find_element(By.ID, "SubCategory")
                if subcat_el.tag_name == "select":
                    self._select_dropdown_robust(subcat_el, product["subcategory"])
                else:
                    subcat_el.send_keys(product["subcategory"])
            except Exception as e:
                logger.warning(f"Could not set SubCategory: {e}")

            self.driver.find_element(By.ID, "ProductDescription").send_keys(product["description"])
            
            # 4. Set numeric fields to zero
            for field_id in ["Point", "StockQuantity", "Price"]:
                try:
                    el = self.driver.find_element(By.ID, field_id)
                    el.clear()
                    el.send_keys("0")
                except:
                    pass

            # 5. Disable "Order Acceptance" toggle (selector provided)
            try:
                toggle_selector = "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\\:bg-card.w-full.rounded-xl.shadow-2xl.dark\\:shadow-none.border.border-transparent.dark\\:border-white\\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.overflow-y-auto.flex-grow.max-h-\\[50vh\\].text-text-light.dark\\:text-text-dark > div > div.grid.grid-cols-1.sm\\:grid-cols-2.gap-4 > div:nth-child(1) > div > label > div > div"
                toggle = self.driver.find_element(By.CSS_SELECTOR, toggle_selector)
                # The user says "should always disable". Clicking it will toggle it.
                self.driver.execute_script("arguments[0].click();", toggle)
                logger.info(f"  → Toggle 'Order Acceptance' clicked")
            except Exception as e:
                logger.warning(f"Could not find or click toggle: {e}")

            # 6. Save Changes
            save_btn_selector = "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\\:bg-card.w-full.rounded-xl.shadow-2xl.dark\\:shadow-none.border.border-transparent.dark\\:border-white\\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.border-t.border-gray-50.dark\\:border-white\\/5.flex.justify-end.space-x-4.flex-shrink-0 > button.inline-flex.items-center.justify-center.transition-all.cursor-pointer.disabled\\:opacity-50.disabled\\:cursor-not-allowed.gap-2.focus\\:outline-none.font-semibold.rounded-lg.active\\:scale-\\[0\\.98\\].disabled\\:active\\:scale-100.focus\\:ring-2.focus\\:ring-offset-2.px-6.py-3\\.5.text-sm.bg-indigo-600.text-white.hover\\:bg-indigo-700.shadow-lg.shadow-indigo-200.dark\\:shadow-none.focus\\:ring-indigo-500"
            save_btn = self.driver.find_element(By.CSS_SELECTOR, save_btn_selector)
            self.driver.execute_script("arguments[0].click();", save_btn)
            time.sleep(3)
            
            logger.info(f"✓ Product added: {product['product_name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to add product {product.get('product_name')}: {e}")
            return False

def scan_surie_products():
    """Scan the local directory and return a list of product data dictionaries."""
    products = []
    if not ROOT_DIR.exists():
        logger.error(f"Root directory not found: {ROOT_DIR}")
        return products

    for category_dir in ROOT_DIR.iterdir():
        if category_dir.is_dir():
            category_name = category_dir.name
            for image_file in category_dir.iterdir():
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    # Skip system files like Thumbs.db
                    if image_file.name.startswith('.'):
                        continue
                        
                    product_name = image_file.stem
                    products.append({
                        "product_name": product_name,
                        "category": category_name,
                        "subcategory": category_name,
                        "description": product_name,
                        "image_path": image_file.absolute(),
                    })
    return products

def run_surie_product_upload(email, password):
    """Main execution flow for Surie Product Upload."""
    from dashboard_automation import VendorPortalAutomation
    
    products = scan_surie_products()
    if not products:
        print("✗ No products found in the directory.")
        return False
    
    print(f"→ Found {len(products)} products to upload.")
    
    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                return False
            
            uploader = SurieProductAutomation(auto.driver)
            if not uploader.navigate_to_product_management():
                return False
            
            # Deduplicate: Check what's already uploaded
            uploaded_names = uploader.get_uploaded_products()
            to_upload = [p for p in products if p["product_name"].lower() not in uploaded_names]
            
            if not to_upload:
                print("✓ All products are already uploaded.")
                return True
                
            print(f"→ {len(to_upload)} products remaining to be uploaded (skipped {len(products) - len(to_upload)} already on dashboard).")
            
            success_count = 0
            for p in to_upload:
                if uploader.add_product(p):
                    success_count += 1
                time.sleep(1)
            
            print(f"\n✓ Upload complete. New success: {success_count}/{len(to_upload)}")
            return success_count == len(to_upload)
    except Exception as e:
        logger.error(f"Surie Product Upload failed: {e}")
        return False
