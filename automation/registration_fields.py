"""
Registration Fields Automation
Handles adding registration fields in App Settings -> Registration Field
"""

import logging
import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

logger = logging.getLogger(__name__)

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

class RegistrationFieldsAutomation:
    """
    Automates adding registration fields: First Name, Phone Number, Pincode, City, State, Address.
    Repeats for all user types found in the portal.
    """

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)
        self.fields_to_add = [
            "First Name",
            "Phone Number",
            "Pincode",
            "City",
            "State",
            "Address"
        ]

    def _ss(self, name):
        """Take a screenshot for debugging."""
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"reg_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def navigate(self):
        """Navigate to App Settings -> Registration Field section."""
        try:
            logger.info("Going to App Settings...")
            self.driver.get(APP_SETTINGS)
            time.sleep(3)

            # Click "Registration Field" button (usually a card or list item)
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(.,'Registration Field')]")
                )
            ).click()
            time.sleep(3)
            logger.info("  → Registration Field section opened")

            # Confirm "Add Registration Field" button is present
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'Add Registration Field')]")
                )
            )
            logger.info("✓ Registration Fields page ready")
            return True
        except Exception as e:
            logger.error(f"Navigation to Registration Fields failed: {e}")
            self._ss("nav_error")
            return False

    def get_user_types(self):
        """Fetch all available user types from the dropdown."""
        try:
            # Open the "Add Registration Field" popup to read user types
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add Registration Field')]")
                )
            ).click()
            time.sleep(2)

            select_el = self.wait.until(
                EC.presence_of_element_located((By.NAME, "UserType"))
            )
            options = [
                o.text.strip()
                for o in Select(select_el).options
                if o.get_attribute("value")  # skip empty/placeholder
            ]

            # Close popup
            try:
                self.driver.find_element(By.XPATH, "//button[contains(text(),'Cancel')]").click()
            except:
                try:
                    self.driver.find_element(By.XPATH, "//button[contains(text(),'Discard')]").click()
                except:
                    # If both fail, just escape key
                    from selenium.webdriver.common.keys import Keys
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            
            time.sleep(1)
            logger.info(f"Found {len(options)} user types: {options}")
            return options
        except Exception as e:
            logger.error(f"Failed to get user types: {e}")
            self._ss("get_user_types_error")
            return []

    def add_registration_field(self, user_type, system_data_point):
        """
        Add a single registration field for a specific user type.
        system_data_point: The field name to select (e.g., 'First Name')
        """
        try:
            logger.info(f"  Adding field: [{user_type}] -> {system_data_point}")

            # 1. Click "Add Registration Field"
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add Registration Field')]")
                )
            ).click()
            time.sleep(2)

            # 2. Select User Type
            ut_select = self.wait.until(
                EC.presence_of_element_located((By.NAME, "UserType"))
            )
            Select(ut_select).select_by_visible_text(user_type)
            logger.info(f"    → User Type selected: {user_type}")

            # 3. Select System Data Point
            # User specifically mentioned "system data point" dropdown
            try:
                sdp_select = self.wait.until(
                    EC.presence_of_element_located((By.NAME, "SystemDataPoint"))
                )
                Select(sdp_select).select_by_visible_text(system_data_point)
            except:
                # Fallback if name is slightly different
                sdp_select = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//select[contains(@name, 'DataPoint') or contains(@name, 'Field')]"))
                )
                Select(sdp_select).select_by_visible_text(system_data_point)
            
            logger.info(f"    → System Data Point selected: {system_data_point}")

            # 4. Enable Mandatory toggle
            # User mentioned "toggle button for mandatory enable it"
            try:
                # Try finding by name first
                mandatory_toggle = self.driver.find_element(By.NAME, "IsMandatory")
                if not mandatory_toggle.is_selected():
                    self.driver.execute_script("arguments[0].click();", mandatory_toggle)
            except:
                # Fallback to finding by label text
                try:
                    mandatory_label = self.driver.find_element(By.XPATH, "//label[contains(.,'Mandatory')]")
                    mandatory_toggle = mandatory_label.find_element(By.TAG_NAME, "input")
                    if not mandatory_toggle.is_selected():
                        self.driver.execute_script("arguments[0].click();", mandatory_toggle)
                except:
                    logger.warning("    ⚠ Could not find Mandatory toggle - skipping toggle")
            
            logger.info("    → Mandatory toggle enabled")

            # 5. Click "Integrate Now"
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Integrate Now')]")
                )
            ).click()
            logger.info("    → Integrate Now clicked")
            time.sleep(3)

            # 6. Wait for popup to close (button reappears)
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'Add Registration Field')]")
                )
            )
            logger.info(f"  ✓ Field added successfully: {system_data_point}\n")
            return True

        except Exception as e:
            logger.error(f"  ✗ Failed to add field {system_data_point} for {user_type}: {e}")
            self._ss(f"error_{user_type}_{system_data_point.replace(' ', '_')}")
            try:
                # Try to close the popup if it's still open
                cancel_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'Cancel') or contains(text(),'Discard')]")
                cancel_btn.click()
                time.sleep(1)
            except:
                pass
            return False

    def process_all(self):
        """Main runner to add all specified fields for all user types."""
        user_types = self.get_user_types()
        if not user_types:
            logger.error("No user types found. Aborting.")
            return False

        successful = 0
        failed = 0
        total_tasks = len(user_types) * len(self.fields_to_add)

        logger.info(f"Starting registration fields automation: {total_tasks} fields total")
        logger.info("=" * 60)
        
        for utype in user_types:
            logger.info(f"Processing User Type: {utype}")
            for field in self.fields_to_add:
                if self.add_registration_field(utype, field):
                    successful += 1
                else:
                    failed += 1
                time.sleep(1)

        logger.info("=" * 60)
        logger.info(f"Registration fields batch complete → ✓ {successful} succeeded  ✗ {failed} failed")
        return failed == 0
