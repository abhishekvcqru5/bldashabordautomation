
import logging
import time
from datetime import datetime
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

class GiftManagementAutomation:
    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    def _ss(self, name):
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"gift_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def navigate(self):
        try:
            logger.info("Going to App Settings...")
            self.driver.get(APP_SETTINGS)
            time.sleep(3)

            # Click Gift Management
            # Selector: #root > div... > main > div.grid... > button:nth-child(5) > h3
            gift_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "main > div.grid > button:nth-child(5)")
                )
            )
            gift_btn.click()
            time.sleep(3)
            logger.info("  → Gift Management section opened")
            return True
        except Exception as e:
            logger.error(f"Navigation to gift management failed: {e}")
            self._ss("nav_error")
            return False

    def process_gifts(self, image_path):
        try:
            # Wait for table to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr")))
            
            # Get the number of rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
            total_rows = len(rows)
            logger.info(f"  Found {total_rows} gifts to process")

            for i in range(1, total_rows + 1):
                logger.info(f"  --- Processing Gift {i} of {total_rows} ---")
                
                try:
                    # Re-find the action button for the i-th row (table might have refreshed)
                    action_btn_sel = f"table > tbody > tr:nth-child({i}) td.sticky.right-0 div > button"
                    action_btn = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, action_btn_sel))
                    )
                    
                    # Scroll into view to be safe
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action_btn)
                    time.sleep(0.5)
                    
                    action_btn.click()
                    time.sleep(1)
                    logger.info(f"    → Action button {i} clicked")

                    # 2. Click Edit Offering
                    # The dropdown is usually global or relative to the action button
                    # We'll use a text-based search for "Edit Offering" within the opened dropdown
                    edit_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Edit Offering')]"))
                    )
                    edit_btn.click()
                    time.sleep(2)
                    logger.info("    → Edit Offering clicked")

                    # 3. Remove old image
                    try:
                        remove_btn = self.driver.find_elements(By.CSS_SELECTOR, "div.fixed.inset-0 button.text-red-500, div.fixed.inset-0 button[title*='Delete'], div.fixed.inset-0 button[title*='Remove']")
                        if remove_btn:
                            remove_btn[0].click()
                            time.sleep(1)
                            logger.info("    → Old image removed")
                    except Exception:
                        pass

                    # 4. Upload new image
                    try:
                        file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                        file_input.send_keys(str(Path(image_path).absolute()))
                        time.sleep(2)
                        logger.info(f"    → Image uploaded")
                    except Exception as e:
                        logger.warning(f"    ⚠ Upload failed: {e}")

                    # 5. Enable Cash Out toggle
                    try:
                        # Find the toggle container for Cash Out
                        # It's usually a label or div containing the text "Cash Out"
                        toggle_label = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, "//div[contains(., 'Cash Out')]//label"))
                        )
                        toggle_label.click()
                        time.sleep(1)
                        logger.info("    → Cash Out enabled")
                    except Exception as e:
                        logger.warning(f"    ⚠ Could not find Cash Out toggle: {e}")

                    # 6. Click IMPS button
                    try:
                        imps_btn = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'IMPS')]"))
                        )
                        imps_btn.click()
                        time.sleep(1)
                        logger.info("    → IMPS button clicked")
                    except Exception as e:
                        logger.warning(f"    ⚠ Could not find IMPS button: {e}")

                    # 7. Click Save button
                    save_btn_sel = "div.fixed.inset-0 div.p-5.border-t button.bg-indigo-600"
                    save_btn = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, save_btn_sel))
                    )
                    save_btn.click()
                    time.sleep(3)
                    logger.info(f"  ✓ Gift {i} updated successfully")

                    # Wait for table to be visible again
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr")))
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"  ✗ Error processing Gift {i}: {e}")
                    self._ss(f"gift_error_{i}")
                    # Try to close popup if it's still open
                    try:
                        cancel_btn = self.driver.find_elements(By.XPATH, "//button[contains(., 'Cancel')]")
                        if cancel_btn:
                            cancel_btn[0].click()
                            time.sleep(1)
                    except:
                        pass
                    continue

            logger.info("✓ Finished processing all gifts in the table")
            return True

        except Exception as e:
            logger.error(f"Fatal error in process_gifts: {e}")
            self._ss("fatal_error")
            return False

def run_gift_management(email, password, image_path):
    from dashboard_automation import VendorPortalAutomation
    
    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                return False
            
            time.sleep(2)
            gift_auto = GiftManagementAutomation(auto.driver)
            
            if not gift_auto.navigate():
                return False
            
            return gift_auto.process_gifts(image_path)
            
    except Exception as e:
        logger.error(f"Unexpected error in gift management: {e}")
        return False
