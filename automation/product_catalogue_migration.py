"""
Product Catalogue Migration Module
Handles extraction of Product Catalogue from the old dashboard (vcqru.com)
and uploading them to the new dashboard (app.vcqru.com).
"""

import logging
import time
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select

logger = logging.getLogger(__name__)

OLD_DASHBOARD_URL = "https://www.vcqru.com/login.aspx"
PRODUCT_IMAGE_DIR = Path(__file__).resolve().parent.parent / "product_catalogue"
SCREENSHOTS_DIR = Path(__file__).resolve().parent / "screenshots"

class OldDashboardProductExtractor:
    """Extracts product data from the old VCQRU dashboard."""

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)
        PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def _ss(self, label: str):
        """Take a debug screenshot."""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            p = SCREENSHOTS_DIR / f"old_prod_{label}_{ts}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def login(self, email: str, password: str) -> bool:
        """
        Open old dashboard, tick Vendor checkbox, enter credentials, submit.
        Returns True when post-login dashboard is detected.
        """
        old_email = "jackson.monteiro@akemiindia.com"
        old_password = "Akemi@123$#"
        logger.info(f"Attempting login to old dashboard with provided credentials ({old_email}) ...")
        success = self._login_attempt(old_email, old_password)
        if not success:
            logger.info(f"Provided credentials failed. Trying passed credentials ({email}) ...")
            success = self._login_attempt(email, password)
        return success

    def _login_attempt(self, email: str, password: str) -> bool:
        """Single login attempt logic."""
        try:
            logger.info(f"  → Opening: {OLD_DASHBOARD_URL}")
            self.driver.get(OLD_DASHBOARD_URL)
            time.sleep(4)

            # ── Step 1: Select "Vendor" checkbox ─────────────────────────────
            vendor_selected = False

            # Strategy A — click the label whose text contains "Vendor"
            try:
                labels = self.driver.find_elements(By.TAG_NAME, "label")
                for lbl in labels:
                    if "vendor" in lbl.text.strip().lower():
                        logger.info(f"    → Clicking Vendor label: '{lbl.text.strip()}'")
                        self.driver.execute_script("arguments[0].click();", lbl)
                        vendor_selected = True
                        break
            except Exception:
                pass

            # Strategy B — known checkbox ID
            if not vendor_selected:
                for chk_id in ("chkadmin", "chkVendor", "rdVendor"):
                    try:
                        el = self.driver.find_element(By.ID, chk_id)
                        self.driver.execute_script("arguments[0].click();", el)
                        vendor_selected = True
                        logger.info(f"    → Vendor selected via ID: {chk_id}")
                        break
                    except Exception:
                        continue

            if not vendor_selected:
                logger.warning("    ⚠ Could not find Vendor checkbox — proceeding anyway")

            time.sleep(2)  # let the page re-render vendor fields

            # ── Step 2: Fill credentials ──────────────────────────────────────
            logger.info(f"    → Filling credentials for {email} …")
            for fld_id in ("login_txt_id", "txtEmail", "txtUsername", "txtUser"):
                try:
                    fld = self.driver.find_element(By.ID, fld_id)
                    if fld.is_displayed():
                        fld.clear()
                        fld.send_keys(email)
                        logger.info(f"      Email → field #{fld_id}")
                        break
                except Exception:
                    continue

            for fld_id in ("login_txt_pass", "txtPassword", "txtPass"):
                try:
                    fld = self.driver.find_element(By.ID, fld_id)
                    if fld.is_displayed():
                        fld.clear()
                        fld.send_keys(password)
                        logger.info(f"      Password → field #{fld_id}")
                        break
                except Exception:
                    continue

            # ── Step 3: Click login button ────────────────────────────────────
            clicked = False
            for btn_id in ("btnVendor", "btnLogin", "btnSubmit", "Button1"):
                try:
                    btn = self.driver.find_element(By.ID, btn_id)
                    if btn.is_displayed():
                        try:
                            btn.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", btn)
                        logger.info(f"      Login button clicked: #{btn_id}")
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                # Fallback — submit button by type
                try:
                    btn = self.driver.find_element(
                        By.XPATH, "//input[@type='submit'] | //button[@type='submit']"
                    )
                    self.driver.execute_script("arguments[0].click();", btn)
                    logger.info("      Login submitted via fallback submit button")
                except Exception as e:
                    logger.error(f"      ✗ Could not find login button: {e}")
                    self._ss("no_login_btn")
                    return False

            # ── Step 4: Wait for post-login state ─────────────────────────────
            logger.info("    → Waiting for post-login redirect …")
            for _ in range(30):
                url = self.driver.current_url.lower()
                has_sidebar = bool(self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(normalize-space(.), 'Build Loyalty App') or "
                    "contains(normalize-space(.), 'Dashboard')]",
                ))
                has_logout = bool(self.driver.find_elements(
                    By.XPATH, "//a[contains(normalize-space(.), 'Logout')]"
                ))
                if ("login.aspx" not in url and has_logout) or (has_sidebar and has_logout):
                    logger.info(f"  ✓ Logged in. Current URL: {self.driver.current_url}")
                    print("[1/2] Login successful")
                    return True
                time.sleep(1)

            logger.error("  ✗ Login timed out — still on login page or unknown state")
            self._ss("login_timeout")
            return False

        except Exception as e:
            logger.error(f"Login exception: {e}")
            self._ss("login_exception")
            return False

    def navigate_to_product_catalogue(self):
        """Navigate to Product Catalogue with iframe and retry support."""
        self.driver.switch_to.default_content()
        time.sleep(2)
        
        # Build list of contexts to search
        all_frames = []
        for tag in ("frame", "iframe"):
            try:
                all_frames.extend(self.driver.find_elements(By.TAG_NAME, tag))
            except:
                pass
        contexts = [None] + all_frames
        
        logger.info(f"  → Searching sidebar for Loyalty App across {len(contexts)} context(s)")
        
        found = False
        for ctx in contexts:
            try:
                self.driver.switch_to.default_content()
                if ctx is not None:
                    self.driver.switch_to.frame(ctx)
                
                # Click Build Loyalty App menu
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_blapp > a")
                    if el.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", el)
                        logger.info("    ✓ Found and clicked Build Loyalty App menu")
                        time.sleep(3)
                except Exception as e:
                    logger.debug(f"Did not click #ctl00_blapp: {e}")
                    
                # Click Product Catalogue submenu
                try:
                    sub = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_Liprodcutcatalogbl > a")
                    if sub.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", sub)
                        logger.info("    ✓ Found and clicked Product Catalogue submenu")
                        time.sleep(5)
                        found = True
                        break
                except Exception as e:
                    logger.debug(f"Did not click submenu: {e}")
                    continue
            except Exception as frame_e:
                logger.debug(f"    Context navigation failed: {frame_e}")
                continue
        
        if not found:
            logger.error("✗ Navigation to Product Catalogue failed")
            self._ss("nav_product_catalogue_fail")
            return False
            
        # Click "Add Product Details" button to show table
        try:
            btn = self.wait.until(EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder1_btnaddproductdetails")))
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            logger.info("✓ Clicked Add Product Details button")
        except Exception as e:
            logger.warning(f"Could not click Add Product Details button: {e}")
            
        return True

    def _download_image(self, url, row_idx, product_name):
        """Download product image with clean naming."""
        if not url:
            return None
        
        if not url.startswith("http"):
            url = urljoin("https://www.vcqru.com/", url)
            
        try:
            # Clean product name for filename
            clean_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
            filename = f"row_{row_idx}_{clean_name}.jpg"
            local_path = PRODUCT_IMAGE_DIR / filename
            
            session = requests.Session()
            for cookie in self.driver.get_cookies():
                session.cookies.set(cookie["name"], cookie["value"])
            
            response = session.get(url, stream=True, timeout=20)
            response.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return str(local_path.absolute())
        except Exception as e:
            logger.warning(f"Image download failed for {url}: {e}")
            return None

    def extract_products(self):
        """Extract all rows from the product table."""
        products = []
        try:
            # Ensure table is visible
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#dataTable1 > tbody > tr")))
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#dataTable1 > tbody > tr")
            logger.info(f"Found {len(rows)} rows in table.")
            
            # Debug: log columns of the first row
            if rows:
                first_cells = rows[0].find_elements(By.TAG_NAME, "td")
                logger.info(f"DEBUG: First row has {len(first_cells)} cells.")
                for idx, cell in enumerate(first_cells):
                    logger.info(f"DEBUG: Cell {idx} outerHTML: {cell.get_attribute('outerHTML')}")
            
            for i, row in enumerate(rows, 1):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 10:
                    continue
                
                # Fields per row based on user request:
                # Category (2nd col -> cells[1]), Subcategory (3rd col -> cells[2]),
                # Product name (4th col -> cells[3]), Description (5th col -> cells[4]),
                # Points (7th col -> cells[6]), Price (8th col -> cells[7]),
                # Stock (9th col -> cells[8]), Image (10th col -> cells[9])
                data = {
                    "category": cells[1].text.strip(),
                    "subcategory": cells[2].text.strip(),
                    "product_name": cells[3].text.strip(),
                    "description": cells[4].text.strip(),
                    "points": cells[6].text.strip(),
                    "price": cells[7].text.strip(),
                    "stock": cells[8].text.strip(),
                }
                
                # Skip empty rows
                if not data["product_name"]:
                    continue
                
                # Image Path -> td:nth-child(10) is index 9. The relative URL path is in the cell's text directly.
                img_url = cells[9].text.strip()
                if not img_url or img_url == "-":
                    logger.info(f"Skipping {data['product_name']} because it has no image.")
                    continue
                logger.info(f"DEBUG: Row {i} ({data['product_name']}) Cell 9 text: {img_url}")
                
                downloaded_path = self._download_image(img_url, i, data["product_name"])
                if not downloaded_path:
                    logger.info(f"Skipping {data['product_name']} because the image download failed.")
                    continue
                data["image_path"] = downloaded_path
                
                products.append(data)
                logger.info(f"Extracted: {data['product_name']}")
                
            return products
        except Exception as e:
            logger.error(f"Product extraction failed: {e}")
            self._ss("extract_products_fail")
            return []

class ProductCatalogueAutomation:
    """Handles uploading products to the new dashboard."""

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    def navigate_to_product_management(self):
        """Navigate to App Setting -> Product Management."""
        try:
            # Navigate to App Settings directly to be sure
            self.driver.get("https://app.vcqru.com/vendor/app-settings")
            time.sleep(3)
            
            # Selector provided by user for the 6th button (Product Management)
            selector = "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3.gap-5 > button:nth-child(6)"
            btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            logger.info("✓ Navigated to Product Management")
            return True
        except Exception as e:
            logger.error(f"Navigation to product management failed: {e}")
            return False

    def add_product(self, product):
        """Fill and submit the 'Add New Product' form."""
        try:
            # Click "Add New Product"
            add_btn_selector = "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.bg-white.dark\\:bg-card.rounded-xl.border-2.border-gray-100.dark\\:border-white\\/10.overflow-hidden.relative > div.px-6.py-4.flex.items-center.justify-between.border-b.border-gray-100.dark\\:border-white\\/10.bg-indigo-50\\/50.dark\\:bg-indigo-500\\/5 > button"
            add_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, add_btn_selector)))
            self.driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(2)
            
            # Image upload
            if product.get("image_path"):
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                file_input.send_keys(product["image_path"])
                time.sleep(2)
            
            # Product Name
            self.driver.find_element(By.ID, "ProductName").send_keys(product["product_name"])
            
            # Category and SubCategory
            try:
                cat_select = Select(self.driver.find_element(By.ID, "CategoryId"))
                cat_select.select_by_visible_text(product["category"])
            except:
                try:
                    self.driver.find_element(By.ID, "CategoryId").send_keys(product["category"])
                except:
                    pass
                
            try:
                subcat_select = Select(self.driver.find_element(By.ID, "SubCategory"))
                subcat_select.select_by_visible_text(product["subcategory"])
            except:
                try:
                    self.driver.find_element(By.ID, "SubCategory").send_keys(product["subcategory"])
                except:
                    pass

            # Description (if empty/no description, use product name)
            desc = product.get("description", "").strip()
            if not desc:
                desc = product["product_name"]
            self.driver.find_element(By.ID, "ProductDescription").send_keys(desc)
            
            # Price
            price_field = self.driver.find_element(By.ID, "Price")
            price_field.clear()
            price_field.send_keys(product["price"])
            
            # Discount Price (same price)
            discount_field = self.driver.find_element(By.ID, "DiscountPrice")
            discount_field.clear()
            discount_field.send_keys(product["price"])
            
            # Stock
            stock_field = self.driver.find_element(By.ID, "StockQuantity")
            stock_field.clear()
            stock_field.send_keys(product["stock"])
            
            # Point
            point_field = self.driver.find_element(By.ID, "Point")
            point_field.clear()
            point_field.send_keys(product["points"])
            
            # Disable toggle: "this toggle button should be disable"
            try:
                toggle_lbl = self.driver.find_element(By.CSS_SELECTOR, "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\\:bg-card.w-full.rounded-xl.shadow-2xl.dark\\:shadow-none.border.border-transparent.dark\\:border-white\\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.overflow-y-auto.flex-grow.max-h-\\[50vh\\].text-text-light.dark\\:text-text-dark > div > div.grid.grid-cols-1.sm\\:grid-cols-2.gap-4 > div:nth-child(1) > div > label")
                # Find checkbox inside
                checkbox = None
                try: checkbox = toggle_lbl.find_element(By.TAG_NAME, "input")
                except: pass
                
                if checkbox:
                    if checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", toggle_lbl)
                        logger.info("  → Toggle was enabled, clicked to disable it")
                    else:
                        logger.info("  → Toggle was already disabled")
                else:
                    self.driver.execute_script("arguments[0].click();", toggle_lbl)
            except Exception as e:
                logger.warning(f"Could not toggle: {e}")
            
            # Publish
            publish_btn_selector = "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden.relative.z-10 > main > div.space-y-8 > div.fixed.inset-0.z-50.flex.items-center.justify-center.p-4.transition-all.duration-300.opacity-100 > div.relative.bg-white.dark\\:bg-card.w-full.rounded-xl.shadow-2xl.dark\\:shadow-none.border.border-transparent.dark\\:border-white\\/10.transition-all.duration-300.transform.flex.flex-col.max-w-4xl.scale-100.translate-y-0 > div.p-5.border-t.border-gray-50.dark\\:border-white\\/5.flex.justify-end.space-x-4.flex-shrink-0 > button.inline-flex.items-center.justify-center.transition-all.cursor-pointer.disabled\\:opacity-50.disabled\\:cursor-not-allowed.gap-2.focus\\:outline-none.font-semibold.rounded-lg.active\\:scale-\\[0\\.98\\].disabled\\:active\\:scale-100.focus\\:ring-2.focus\\:ring-offset-2.px-6.py-3\\.5.text-sm.bg-indigo-600.text-white.hover\\:bg-indigo-700.shadow-lg.shadow-indigo-200.dark\\:shadow-none.focus\\:ring-indigo-500"
            publish_btn = self.driver.find_element(By.CSS_SELECTOR, publish_btn_selector)
            self.driver.execute_script("arguments[0].click();", publish_btn)
            time.sleep(3)
            
            logger.info(f"✓ Uploaded {product['product_name']} successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to add product {product['product_name']}: {e}")
            return False

def run_product_catalogue_migration(email, password):
    """Main migration flow for Product Catalogue."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from dashboard_automation import VendorPortalAutomation

    # 1. Extraction
    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-notifications")
    
    # Force system Chrome binary and use webdriver-manager
    import shutil
    system_chrome = (
        shutil.which("google-chrome-stable")
        or shutil.which("google-chrome")
        or shutil.which("chromium-browser")
        or shutil.which("chromium")
    )
    if system_chrome:
        opts.binary_location = system_chrome
    
    driver_path = ChromeDriverManager().install()
    p = Path(driver_path)
    found_exe = None
    if p.is_dir():
        for name in ("chromedriver.exe", "chromedriver"):
            if (p / name).exists():
                found_exe = p / name
                break
            for sub in p.glob(f"**/{name}"):
                found_exe = sub
                break
            if found_exe:
                break
    elif p.suffix.lower() != ".exe":
        for name in ("chromedriver.exe", "chromedriver"):
            if (p.parent / name).exists():
                found_exe = p.parent / name
                break
            for sub in p.parent.glob(f"**/{name}"):
                found_exe = sub
                break
            if found_exe:
                break
    
    if found_exe:
        driver_path = str(found_exe)
        logger.info(f"  Resolved webdriver path to: {driver_path}")
        
    service = Service(driver_path)
    old_driver = webdriver.Chrome(service=service, options=opts)
    
    try:
        extractor = OldDashboardProductExtractor(old_driver)
        if not extractor.login(email, password):
            print("✗ Login failed")
            old_driver.quit()
            return False
        print("[1/2] Login successful")
        
        if not extractor.navigate_to_product_catalogue():
            old_driver.quit()
            return False
        print("[2/2] Product Catalogue opened")
        
        products = extractor.extract_products()
        old_driver.quit()
        
        if not products:
            logger.info("No products found to migrate.")
            return True

        # 2. Upload
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                return False
            
            uploader = ProductCatalogueAutomation(auto.driver)
            if not uploader.navigate_to_product_management():
                return False
            
            for p in products:
                uploader.add_product(p)
            
            return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'old_driver' in locals(): old_driver.quit()
        return False
