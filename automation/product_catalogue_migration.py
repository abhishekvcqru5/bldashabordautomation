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
PRODUCT_IMAGE_DIR = Path("product_catalogue")

class OldDashboardProductExtractor:
    """Extracts product data from the old VCQRU dashboard."""

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)
        PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    def login(self, email, password):
        """Reuse login logic from existing migration script pattern."""
        try:
            self.driver.get(OLD_DASHBOARD_URL)
            time.sleep(2)
            
            # Select Vendor mode
            try:
                vendor_chk = self.driver.find_element(By.ID, "chkadmin")
                self.driver.execute_script("arguments[0].click();", vendor_chk)
                time.sleep(2)
            except:
                pass

            email_field = self.wait.until(EC.visibility_of_element_located((By.ID, "login_txt_id")))
            pass_field = self.driver.find_element(By.ID, "login_txt_pass")
            login_btn = self.driver.find_element(By.ID, "btnVendor")

            email_field.clear()
            email_field.send_keys(email)
            pass_field.clear()
            pass_field.send_keys(password)
            
            self.driver.execute_script("arguments[0].click();", login_btn)
            
            # Wait for login success
            success = False
            for _ in range(30):
                if "login.aspx" not in self.driver.current_url.lower():
                    success = True
                    break
                time.sleep(1)
            return success
        except Exception as e:
            logger.error(f"Old dashboard login failed: {e}")
            return False

    def navigate_to_product_catalogue(self):
        """Navigate to Product Catalogue with iframe and retry support."""
        selector = "#ctl00_Liprodcutcatalogbl > a"
        
        for attempt in range(2):
            try:
                contexts = [None]
                try: contexts.extend(self.driver.find_elements(By.TAG_NAME, "iframe"))
                except: pass

                for ctx in contexts:
                    self.driver.switch_to.default_content()
                    if ctx: self.driver.switch_to.frame(ctx)
                    
                    try:
                        el = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        if el:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                            time.sleep(1)
                            try:
                                el.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", el)
                            
                            time.sleep(3)
                            # Handle "Add Product Details" to reveal table
                            try:
                                btn = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnaddproductdetails")
                                self.driver.execute_script("arguments[0].click();", btn)
                                time.sleep(2)
                            except: pass
                            
                            print("✓ Navigation success")
                            return True
                    except: continue
                
            except Exception:
                if attempt == 1:
                    self.driver.save_screenshot(f"fail_nav_{int(time.time())}.png")
            time.sleep(2)

        print("✗ Navigation failed")
        return False

    def _download_image(self, url, row_idx, product_name):
        """Download product image with clean naming."""
        if not url:
            return None
        
        if url.startswith("/"):
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
            
            for i, row in enumerate(rows, 1):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 10:
                    continue
                
                # Fields per row based on user request
                data = {
                    "s_no": cells[0].text.strip(),
                    "category": cells[1].text.strip(),
                    "subcategory": cells[2].text.strip(),
                    "product_name": cells[3].text.strip(),
                    "description": cells[4].text.strip(),
                    "points": cells[6].text.strip(), # td:nth-child(7) is index 6
                    "price": cells[7].text.strip(),  # td:nth-child(8) is index 7
                    "stock": cells[8].text.strip(),  # td:nth-child(9) is index 8
                }
                
                # Skip empty rows
                if not data["product_name"]:
                    continue
                
                # Image Path -> td:nth-child(10) is index 9
                img_el = cells[9].find_elements(By.TAG_NAME, "img")
                img_url = img_el[0].get_attribute("src") if img_el else None
                
                if img_url:
                    data["image_path"] = self._download_image(img_url, i, data["product_name"])
                else:
                    data["image_path"] = None
                
                products.append(data)
                logger.info(f"Extracted: {data['product_name']}")
                
            return products
        except Exception as e:
            logger.error(f"Product extraction failed: {e}")
            return []

class ProductCatalogueAutomation:
    """Handles uploading products to the new dashboard."""

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    def navigate_to_product_management(self):
        """Navigate to App Setting -> Product Management."""
        try:
            # Selector: button.group:nth-child(6) > h3:nth-child(3)
            btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.group:nth-child(6) > h3:nth-child(3)")))
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Navigation to product management failed: {e}")
            return False

    def add_product(self, product):
        """Fill and submit the 'Add New Product' form."""
        try:
            # Click "Add New Product" - button.hover:bg-indigo-700:nth-child(2)
            add_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.hover:bg-indigo-700:nth-child(2)")))
            self.driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(2)
            
            # Fill popup
            # Image upload -> .w-24
            if product.get("image_path"):
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                file_input.send_keys(product["image_path"])
                time.sleep(1)
            
            self.driver.find_element(By.ID, "ProductName").send_keys(product["product_name"])
            
            # Category and SubCategory might be dropdowns
            try:
                cat_select = Select(self.driver.find_element(By.ID, "CategoryId"))
                cat_select.select_by_visible_text(product["category"])
            except:
                self.driver.find_element(By.ID, "CategoryId").send_keys(product["category"])
                
            try:
                subcat_select = Select(self.driver.find_element(By.ID, "SubCategory"))
                subcat_select.select_by_visible_text(product["subcategory"])
            except:
                self.driver.find_element(By.ID, "SubCategory").send_keys(product["subcategory"])

            self.driver.find_element(By.ID, "ProductDescription").send_keys(product["description"])
            self.driver.find_element(By.ID, "Point").send_keys(product["points"])
            self.driver.find_element(By.ID, "StockQuantity").send_keys(product["stock"])
            self.driver.find_element(By.ID, "Price").send_keys(product["price"])
            
            # Disable toggle: div.p-4:nth-child(1) > div:nth-child(1) > label:nth-child(1) > div:nth-child(2) > div:nth-child(2)
            try:
                toggle = self.driver.find_element(By.CSS_SELECTOR, "div.p-4:nth-child(1) > div:nth-child(1) > label:nth-child(1) > div:nth-child(2) > div:nth-child(2)")
                self.driver.execute_script("arguments[0].click();", toggle)
            except:
                pass
            
            # Publish: button.px-6:nth-child(2)
            publish_btn = self.driver.find_element(By.CSS_SELECTOR, "button.px-6:nth-child(2)")
            self.driver.execute_script("arguments[0].click();", publish_btn)
            time.sleep(3)
            
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
    # opts.add_argument("--headless")  # Removed to make it visible for now
    
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
    
    service = Service(ChromeDriverManager().install())
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
