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
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException
)

logger = logging.getLogger(__name__)

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

# XPaths kept as constants to avoid rebuilding strings repeatedly
_XPATH_ADD_BTN   = "//button[contains(text(),'Add Registration Field')]"
_XPATH_INTEGRATE = "//button[contains(text(),'Integrate Now')]"
_XPATH_CANCEL    = "//button[contains(text(),'Cancel') or contains(text(),'Discard')]"
_XPATH_REG_FIELD = "//button[contains(.,'Registration Field')]"


class RegistrationFieldsAutomation:
    """
    Automates adding registration fields: First Name, Phone Number, Pincode, City, State, Address.
    Repeats for all user types found in the portal.
    """

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time, poll_frequency=0.3)
        # Shorter wait used for quick checks where failure is acceptable
        self._short_wait = WebDriverWait(driver, 5, poll_frequency=0.2)
        self.fields_to_add = [
            "First Name",
            "Phone Number",
            "Pincode",
            "City",
            "State",
            "Address",
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    def _wait_clickable(self, by, value, wait=None):
        """Return a clickable element, retrying on stale refs."""
        w = wait or self.wait
        return w.until(EC.element_to_be_clickable((by, value)))

    def _wait_present(self, by, value, wait=None):
        """Return an element once present in the DOM."""
        w = wait or self.wait
        return w.until(EC.presence_of_element_located((by, value)))

    def _close_popup(self):
        """Close an open modal as fast as possible."""
        for xpath in (_XPATH_CANCEL, "//button[@aria-label='Close']",
                      "//button[contains(@class,'close')]"):
            try:
                self._short_wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                ).click()
                return
            except (TimeoutException, NoSuchElementException):
                continue
        # Last resort: Escape key
        try:
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass

    # XPath for the success toast overlay that appears after each save
    _XPATH_TOAST = "//div[contains(@class,'flex items-start') and contains(@class,'p-4')]"

    def _wait_toast_gone(self):
        """
        Wait until the success-toast overlay is no longer visible.
        This overlay blocks clicks on the 'Add Registration Field' button.
        Tries up to 15 s; silently continues if toast was never found.
        """
        try:
            self.wait.until(
                EC.invisibility_of_element_located((By.XPATH, self._XPATH_TOAST))
            )
            logger.info("    → Toast dismissed")
        except Exception:
            # Toast may not have appeared or already gone — safe to continue
            pass

    def _wait_for_add_btn(self):
        """Wait until 'Add Registration Field' is clickable, scroll it into view,
        and return the element.  Uses JS scroll to guarantee it is not hidden
        behind any sticky header or toast overlay."""
        btn = self._wait_clickable(By.XPATH, _XPATH_ADD_BTN)
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        return btn

    def _open_add_popup(self):
        """Click 'Add Registration Field' (with JS fallback) and wait for UserType dropdown."""
        btn = self._wait_for_add_btn()
        try:
            btn.click()
        except Exception:
            # Fallback: JS click in case an overlay still intercepts
            self.driver.execute_script("arguments[0].click();", btn)
        return self._wait_present(By.NAME, "UserType")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def navigate(self):
        """Navigate to App Settings -> Registration Field section."""
        try:
            logger.info("Going to App Settings...")
            self.driver.get(APP_SETTINGS)

            # Wait for the Registration Field card/button — no blind sleep
            self._wait_clickable(By.XPATH, _XPATH_REG_FIELD).click()
            logger.info("  → Registration Field section opened")

            # Confirm page is ready
            self._wait_for_add_btn()
            logger.info("✓ Registration Fields page ready")
            return True

        except Exception as e:
            logger.error(f"Navigation to Registration Fields failed: {e}")
            self._ss("nav_error")
            return False

    def get_user_types(self):
        """Fetch all available user types from the dropdown."""
        try:
            select_el = self._open_add_popup()
            options = [
                o.text.strip()
                for o in Select(select_el).options
                if o.get_attribute("value")   # skip empty/placeholder
            ]
            self._close_popup()
            # Wait until modal is fully gone before returning
            self.wait.until(
                EC.invisibility_of_element_located((By.XPATH, _XPATH_INTEGRATE))
            )
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

            # 1. Open popup and wait for UserType dropdown
            select_el = self._open_add_popup()

            # 2. Select User Type
            Select(select_el).select_by_visible_text(user_type)
            logger.info(f"    → User Type selected: {user_type}")

            # 3. Select System Data Point (wait for it to appear/refresh after user type change)
            sdp_select = None
            for name_attr in ("SystemDataPoint",):
                try:
                    sdp_select = self._wait_present(By.NAME, name_attr)
                    break
                except TimeoutException:
                    pass
            if sdp_select is None:
                sdp_select = self._wait_present(
                    By.XPATH,
                    "//select[contains(@name,'DataPoint') or contains(@name,'Field')]"
                )
            Select(sdp_select).select_by_visible_text(system_data_point)
            logger.info(f"    → System Data Point selected: {system_data_point}")

            # 4. Enable Mandatory toggle (no sleep — just find and act)
            self._enable_mandatory_toggle()

            # 5. Click "Integrate Now"
            self._wait_clickable(By.XPATH, _XPATH_INTEGRATE).click()
            logger.info("    → Integrate Now clicked")

            # 6. Wait for toast/overlay to disappear FIRST, then confirm button is back
            self._wait_toast_gone()
            self._wait_for_add_btn()
            logger.info(f"  ✓ Field added successfully: {system_data_point}\n")
            return True

        except Exception as e:
            logger.error(
                f"  ✗ Failed to add field {system_data_point} for {user_type}: {e}"
            )
            self._ss(f"error_{user_type}_{system_data_point.replace(' ', '_')}")
            try:
                self._close_popup()
            except Exception:
                pass
            return False

    def _enable_mandatory_toggle(self):
        """Enable the Mandatory toggle if it is not already on."""
        # Strategy 1: direct input by name
        try:
            toggle = self._short_wait.until(
                EC.presence_of_element_located((By.NAME, "IsMandatory"))
            )
            if not toggle.is_selected():
                self.driver.execute_script("arguments[0].click();", toggle)
            logger.info("    → Mandatory toggle enabled")
            return
        except (TimeoutException, NoSuchElementException):
            pass

        # Strategy 2: label text
        try:
            label = self.driver.find_element(
                By.XPATH, "//label[contains(.,'Mandatory')]"
            )
            toggle = label.find_element(By.TAG_NAME, "input")
            if not toggle.is_selected():
                self.driver.execute_script("arguments[0].click();", toggle)
            logger.info("    → Mandatory toggle enabled")
            return
        except NoSuchElementException:
            pass

        logger.warning("    ⚠ Could not find Mandatory toggle — skipping")

    def process_all(self):
        """Main runner to add all specified fields for all user types."""
        user_types = self.get_user_types()
        if not user_types:
            logger.error("No user types found. Aborting.")
            return False

        successful = 0
        failed = 0
        total_tasks = len(user_types) * len(self.fields_to_add)

        logger.info(
            f"Starting registration fields automation: {total_tasks} fields total"
        )
        logger.info("=" * 60)

        for utype in user_types:
            logger.info(f"Processing User Type: {utype}")
            for field in self.fields_to_add:
                if self.add_registration_field(utype, field):
                    successful += 1
                else:
                    failed += 1
                # Minimal gap to let any post-save animation settle (0.3 s is enough)
                time.sleep(0.3)

        logger.info("=" * 60)
        logger.info(
            f"Registration fields batch complete → ✓ {successful} succeeded  "
            f"✗ {failed} failed"
        )
        return failed == 0

    def process_specific(self, target_user_types: list):
        """
        Add all registration fields but ONLY for the specified user types.

        Parameters
        ----------
        target_user_types : list[str]
            User type names as entered by the operator.  Matching is
            case-insensitive; any name not found in the portal is skipped
            with a warning.
        """
        portal_user_types = self.get_user_types()
        if not portal_user_types:
            logger.error("No user types found on portal. Aborting.")
            return False

        # Build a case-insensitive lookup: lower-name → actual portal name
        portal_map = {u.lower(): u for u in portal_user_types}

        # Resolve requested names against portal names
        matched = []
        for requested in target_user_types:
            key = requested.strip().lower()
            if key in portal_map:
                matched.append(portal_map[key])
                logger.info(f"  ✓ Matched user type: '{portal_map[key]}'")
            else:
                logger.warning(
                    f"  ⚠ User type '{requested}' not found on portal — skipping.\n"
                    f"    Available types: {portal_user_types}"
                )

        if not matched:
            logger.error("None of the requested user types were found on the portal. Aborting.")
            return False

        successful = 0
        failed = 0
        total_tasks = len(matched) * len(self.fields_to_add)

        logger.info("=" * 60)
        logger.info(
            f"Starting registration fields automation for {len(matched)} user type(s): "
            f"{matched}  —  {total_tasks} fields total"
        )
        logger.info("=" * 60)

        for utype in matched:
            logger.info(f"Processing User Type: {utype}")
            for field in self.fields_to_add:
                if self.add_registration_field(utype, field):
                    successful += 1
                else:
                    failed += 1
                time.sleep(0.3)

        logger.info("=" * 60)
        logger.info(
            f"Registration fields (specific) batch complete → "
            f"✓ {successful} succeeded  ✗ {failed} failed"
        )
        return failed == 0
