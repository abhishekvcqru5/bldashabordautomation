"""
User Type Creation Automation
Handles adding new user types in App Settings -> User Type
"""

import logging
import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

from dashboard_automation import VendorPortalAutomation

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

def get_app_settings_url():
    return getattr(VendorPortalAutomation, "APP_SETTINGS", APP_SETTINGS)


class UserTypeAutomation:
    """
    Automates creating new user types under App Settings -> User Type.
    Enables Scan, Claim Reward, and View Point toggles.
    """

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time, poll_frequency=0.3)
        self._short_wait = WebDriverWait(driver, 5, poll_frequency=0.2)

    def _ss(self, name):
        """Take a screenshot for debugging."""
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"usertype_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def navigate(self):
        """Navigate to App Settings -> User Type section."""
        try:
            logger.info("Going to App Settings...")
            self.driver.get(get_app_settings_url())
            time.sleep(3)

            # Locate the "User Type" card and click it.
            # Try multiple selector strategies for robustness.
            user_type_btn = None
            selectors = [
                "//button[.//h3[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'user type')] or .//h2[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'user type')] or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'user type')]",
                "//button[contains(., 'User Type') or contains(., 'UserType')]",
                "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden > main > div.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3.gap-5 > button:nth-child(10)",
            ]

            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        user_type_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                    else:
                        user_type_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    if user_type_btn:
                        break
                except Exception:
                    continue

            if not user_type_btn:
                logger.error("Could not find the 'User Type' card button under App Settings.")
                self._ss("nav_user_type_fail")
                return False

            user_type_btn.click()
            logger.info("  → User Type section opened")
            time.sleep(3)

            # Confirm page is ready (look for the header Add button)
            self._wait_for_add_btn()
            logger.info("✓ User Type page ready")
            return True

        except Exception as e:
            logger.error(f"Navigation to User Type failed: {e}")
            self._ss("nav_error")
            return False

    def _wait_for_add_btn(self):
        """Wait until the 'Add' button in User Type header is visible and clickable."""
        xpaths = [
            "//button[contains(text(), 'Add') or contains(text(), 'New') or contains(text(), 'Create')]",
            "//div[contains(@class, 'flex')]//button[contains(., 'Add')]",
            "#root > div.flex.h-screen.bg-gray-50.dark\\:bg-dark-900.overflow-hidden.text-gray-900.dark\\:text-gray-100.transition-colors.transition-all.duration-200 > div.flex-1.flex.flex-col.min-w-0.overflow-hidden > main > div.space-y-8 > div.bg-white.dark\\:bg-card.rounded-xl.border-2.border-gray-100.dark\\:border-white\\/10.overflow-hidden.relative > div.px-6.py-4.flex.items-center.justify-between.border-b.border-gray-100.dark\\:border-white\\/10.bg-indigo-50\\/50.dark\\:bg-indigo-500\\/5 > div > button",
        ]
        for xp in xpaths:
            try:
                if xp.startswith("//"):
                    return self.wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                else:
                    return self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, xp)))
            except Exception:
                continue
        raise TimeoutException("Timed out waiting for User Type list Add button.")

    def _enable_toggle(self, child_index, name_keyword):
        """Enable checkbox toggle button at grid child index or by name keyword."""
        # 1. Try finding checkbox inside the grid child element
        try:
            grid = self.driver.find_element(By.CSS_SELECTOR, "form > div.grid")
            child = grid.find_element(By.CSS_SELECTOR, f"div:nth-child({child_index})")
            cb = child.find_element(By.XPATH, ".//input[@type='checkbox']")
            if not cb.is_selected():
                self.driver.execute_script("arguments[0].click();", cb)
            logger.info(f"    → Enabled toggle in grid child {child_index} ({name_keyword})")
            return True
        except Exception as e:
            logger.debug(f"Could not find checkbox at child {child_index}: {e}")

        # 2. Try text search fallback
        try:
            xpath = f"//label[contains(., '{name_keyword}') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{name_keyword.lower()}')]"
            label = self.driver.find_element(By.XPATH, xpath)
            cb = label.find_element(By.XPATH, ".//input[@type='checkbox']")
            if not cb.is_selected():
                self.driver.execute_script("arguments[0].click();", cb)
            logger.info(f"    → Enabled toggle by text fallback: {name_keyword}")
            return True
        except Exception as e:
            logger.debug(f"Could not find checkbox by text fallback for {name_keyword}: {e}")

        # 3. Final fallback: click the child label itself
        try:
            grid = self.driver.find_element(By.CSS_SELECTOR, "form > div.grid")
            label_el = grid.find_element(By.CSS_SELECTOR, f"div:nth-child({child_index}) label")
            self.driver.execute_script("arguments[0].click();", label_el)
            logger.info(f"    → Clicked container label child {child_index} fallback for {name_keyword}")
            return True
        except Exception as e:
            logger.error(f"    ✗ All toggle strategies failed for child {child_index} / {name_keyword}: {e}")
            return False

    def create_user_type(self, user_type_name):
        """Create a single user type with Scan, Claim Reward, and View Point toggles enabled."""
        try:
            logger.info(f"Starting creation of User Type: {user_type_name}")

            # 1. Click Add button to open the modal
            self._wait_for_add_btn().click()
            time.sleep(2)

            # 2. Find Type Label input and enter value
            input_selectors = [
                (By.ID, "UserType"),
                (By.NAME, "UserType"),
                (By.XPATH, "//input[@id='UserType' or @name='UserType' or @placeholder='User Type' or contains(@placeholder, 'User Type')]"),
            ]
            input_el = None
            for by, val in input_selectors:
                try:
                    input_el = self._short_wait.until(EC.presence_of_element_located((by, val)))
                    if input_el:
                        break
                except Exception:
                    continue

            if not input_el:
                raise NoSuchElementException("Could not find the 'UserType' text field inside the modal.")

            input_el.clear()
            input_el.send_keys(user_type_name)
            logger.info(f"    → Entered name: {user_type_name}")

            # 3. Enable the toggles
            # Scan (Child 1)
            self._enable_toggle(1, "Scan")
            # Claim Reward (Child 3)
            self._enable_toggle(3, "Claim Reward")
            # View Point (Child 4)
            self._enable_toggle(4, "View Point")

            # 4. Find the submit/Add button inside the modal and click it
            submit_btn = None
            submit_xpaths = [
                "//div[contains(@class, 'p-5') and contains(@class, 'border-t')]//button[contains(text(), 'Add') or contains(text(), 'Save') or contains(text(), 'Submit') or contains(@class, 'bg-indigo-600')]",
                "//button[contains(text(), 'Add') or contains(text(), 'Save') or contains(text(), 'Submit')]",
                "//form//button[@type='submit']",
            ]
            for xp in submit_xpaths:
                try:
                    submit_btn = self._short_wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                    if submit_btn:
                        break
                except Exception:
                    continue

            if not submit_btn:
                # Direct CSS selector fallback from user
                css_sel = "div.p-5.border-t.border-gray-50.dark\\:border-white\\/5.flex.justify-end.space-x-4.flex-shrink-0 > button.bg-indigo-600"
                submit_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_sel)))

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            time.sleep(0.5)
            submit_btn.click()
            logger.info("    → Form submitted")

            # 5. Wait until the form/modal closes (which is when the list Add button is clickable again)
            self._wait_for_add_btn()
            logger.info(f"✓ User Type '{user_type_name}' created successfully!\n")
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"✗ Failed to create User Type '{user_type_name}': {e}")
            self._ss(f"fail_{user_type_name}")
            # Try to discard the form by clicking Cancel/Discard so the script doesn't hang
            for cancel_xp in (
                "//button[contains(text(), 'Cancel') or contains(text(), 'Discard')]",
                "//button[@aria-label='Close']"
            ):
                try:
                    self.driver.find_element(By.XPATH, cancel_xp).click()
                    time.sleep(1)
                    break
                except Exception:
                    continue
            return False
