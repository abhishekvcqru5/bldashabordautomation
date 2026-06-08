"""
Dashboard Icons Automation Script
Automates the process of adding dashboard icons to the vendor portal
Real selectors discovered by inspecting the live website.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class VendorPortalAutomation:
    """Automate dashboard icon additions on vendor portal"""

    BASE_URL = "https://app.vcqru.com/vendor/login"
    APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

    def __init__(self, email, password, headless=False):
        self.email = email
        self.password = password
        self.wait_time = 20
        self.driver = None
        self.headless = headless

    # ─────────────────────────────────────────────
    # Toast & Click Helpers
    # ─────────────────────────────────────────────
    _XPATH_TOAST = "//div[contains(@class,'flex items-start') and contains(@class,'p-4')]"

    def _wait_toast_gone(self):
        """Wait until any toast message is gone before trying to click main actions."""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.invisibility_of_element_located((By.XPATH, self._XPATH_TOAST))
            )
        except Exception:
            pass

    def _click_add_new_icon(self):
        """Click 'Add New Icon' button safely, waiting for toasts and handling click interception."""
        self._wait_toast_gone()
        btn = WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(text(),'Add New Icon')]")
            )
        )
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.5)
            btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", btn)

    # ─────────────────────────────────────────────
    # Setup
    # ─────────────────────────────────────────────
    def setup_driver(self):
        try:
            opts = Options()
            opts.add_argument("--disable-gpu")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-notifications")
            if self.headless:
                opts.add_argument("--headless=new")

            # ── Force the system Chrome binary so its version is known ──
            # Selenium's own manager may have cached a newer Chrome in
            # ~/.cache/selenium that doesn't match the system chromedriver.
            # By pinning the binary to the system installation we ensure
            # ChromeDriverManager downloads a driver of the exact same version.
            import shutil
            system_chrome = (
                shutil.which("google-chrome-stable")
                or shutil.which("google-chrome")
                or shutil.which("chromium-browser")
                or shutil.which("chromium")
            )
            if system_chrome:
                opts.binary_location = system_chrome
                logger.info(f"  Using system Chrome binary: {system_chrome}")

            driver_path = ChromeDriverManager().install()
            p = Path(driver_path)
            if p.suffix.lower() != ".exe":
                potential_exe = p.parent / "chromedriver.exe"
                if potential_exe.exists():
                    driver_path = str(potential_exe)
                    logger.info(f"  Resolved webdriver path to: {driver_path}")
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=opts)
            self.driver.set_page_load_timeout(30)
            self.driver.maximize_window()
            logger.info("✓ Chrome driver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return False

    # ─────────────────────────────────────────────
    # Login  (3-step: credentials → agreement → dashboard)
    # ─────────────────────────────────────────────
    def login(self):
        try:
            logger.info(f"Opening login page...")
            self.driver.get(self.BASE_URL)

            # 1) Enter email
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, "email"))
            ).send_keys(self.email)

            # 2) Enter password
            self.driver.find_element(By.NAME, "password").send_keys(self.password)

            # Check policy checkbox on the login page if present
            try:
                login_agree_cb = self.driver.find_element(By.XPATH, "//input[@type='checkbox']")
                if not login_agree_cb.is_selected():
                    self.driver.execute_script("arguments[0].click();", login_agree_cb)
                    logger.info("  → Policy checkbox checked on login page")
            except Exception as cb_err:
                logger.debug(f"Could not find or click policy checkbox on login page: {cb_err}")

            # 3) Click Sign In  (the submit button)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            logger.info("  → Credentials submitted, waiting for dashboard or select service...")

            # Check for "Select service" modal/popup
            try:
                # Wait up to 15 seconds for the Continue button to appear
                continue_btn = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continue To Dashboard') or contains(text(), 'Continue')]"))
                )
                logger.info("  → 'Select Service' popup detected, proceeding...")
                
                # Double check the agreement checkbox
                try:
                    agree_cb = self.driver.find_element(By.XPATH, "//input[@type='checkbox']")
                    if not agree_cb.is_selected():
                        self.driver.execute_script("arguments[0].click();", agree_cb)
                        logger.info("    ✓ Agreed to policies checkbox checked")
                except Exception:
                    pass
                
                self.driver.execute_script("arguments[0].click();", continue_btn)
                logger.info("    ✓ Clicked 'Continue To Dashboard'")
            except Exception as popup_e:
                logger.debug(f"  No 'Select Service' popup detected or skipped: {popup_e}")

            # 4) Wait until URL contains /vendor/dashboard
            WebDriverWait(self.driver, self.wait_time).until(
                EC.url_contains("/vendor/dashboard")
            )

            logger.info("✓ Login successful")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            self._take_screenshot("login_error")
            return False

    # ─────────────────────────────────────────────
    # Navigate to Dashboard Icons section
    # ─────────────────────────────────────────────
    def navigate_to_dashboard_icons(self):
        try:
            logger.info("Navigating to App Settings...")
            self.driver.get(self.APP_SETTINGS)
            time.sleep(3)

            # Click the "Dashboard Icons" card / button
            btn = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[.//h3[contains(text(),'Dashboard Icons')] "
                        "or .//h2[contains(text(),'Dashboard Icons')] "
                        "or contains(.,'Dashboard Icons')]",
                    )
                )
            )
            btn.click()
            time.sleep(3)

            # Confirm "Add New Icon" button is present
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'Add New Icon')]")
                )
            )
            logger.info("✓ Dashboard Icons section loaded")
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to Dashboard Icons: {e}")
            self._take_screenshot("navigation_error")
            return False

    # ─────────────────────────────────────────────
    # Read all user types from the live dropdown
    # ─────────────────────────────────────────────
    def get_available_user_types(self):
        """
        Opens the Add New Icon form, reads all options from
        the UserType dropdown, discards the form, and returns
        a list of (value, text) tuples.
        """
        try:
            self._click_add_new_icon()
            time.sleep(1.5)

            select_el = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, "UserType"))
            )
            options = [
                (o.get_attribute("value"), o.text.strip())
                for o in Select(select_el).options
                if o.get_attribute("value")  # skip blank placeholder
            ]

            # Discard the form
            self.driver.find_element(
                By.XPATH, "//button[contains(text(),'Discard')]"
            ).click()
            time.sleep(1)

            logger.info(f"  Found {len(options)} user types: {[t for _, t in options]}")
            return options

        except Exception as e:
            logger.warning(f"Could not read user types: {e}")
            return []

    # ─────────────────────────────────────────────
    # Add a single icon
    # ─────────────────────────────────────────────
    def add_icon(self, icon_data):
        """
        Add one dashboard icon entry.

        icon_data keys:
            user_type      – visible text in dropdown  e.g. "Retailer" / "Painter"
            icon_identity  – value in dropdown         e.g. "gift" / "wallet"
            display_title  – text label                e.g. "Gift"
            image_path     – path to processed image
            toggle_option  – "both" | "side menu" | "dashboard only"
        """
        display = icon_data.get("display_title", "???")
        try:
            logger.info(
                f"  Adding: [{icon_data.get('user_type')}] "
                f"{display}  ({icon_data.get('icon_identity')})"
            )

            # ── 1. Click "Add New Icon" (waits for any toast to clear first) ────
            self._click_add_new_icon()
            time.sleep(1.5)

            # ── 2. Select User Type ─────────────────────────────
            ut_select = WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, "UserType"))
            )
            try:
                Select(ut_select).select_by_visible_text(icon_data["user_type"])
            except Exception:
                Select(ut_select).select_by_value(icon_data["user_type"])
            logger.info(f"    → User type: {icon_data['user_type']}")

            # ── 3. Select Icon Identity ─────────────────────────
            try:
                Select(self.driver.find_element(By.NAME, "IconName")).select_by_value(
                    icon_data["icon_identity"]
                )
            except Exception as first_err:
                try:
                    icon_select = self.driver.find_element(By.NAME, "IconName")
                    opts = [f"value='{o.get_attribute('value')}', text='{o.text}'" for o in Select(icon_select).options]
                    logger.info(f"    Available IconName options: {opts}")
                except Exception as log_err:
                    logger.warning(f"Could not log available IconName options: {log_err}")
                try:
                    Select(
                        self.driver.find_element(By.NAME, "IconName")
                    ).select_by_visible_text(icon_data["icon_identity"])
                except Exception:
                    raise first_err
            logger.info(f"    → Icon identity: {icon_data['icon_identity']}")

            # ── 4. Enter Display Title ──────────────────────────
            name_field = self.driver.find_element(By.NAME, "Name")
            name_field.clear()
            name_field.send_keys(icon_data["display_title"])
            logger.info(f"    → Display title: {icon_data['display_title']}")

            # ── 4.5 Enter Icon Color if present ─────────────────
            hex_color = icon_data.get("icon_color")
            if hex_color:
                try:
                    # Sync color picker visually
                    color_inputs = self.driver.find_elements(By.NAME, "IconColor")
                    color_picker = None
                    color_text = None
                    for ci in color_inputs:
                        if ci.get_attribute("type") == "color":
                            color_picker = ci
                        elif ci.get_attribute("type") == "text":
                            color_text = ci
                    
                    if color_picker:
                        self.driver.execute_script(
                            """
                            var setter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value').set;
                            setter.call(arguments[0], arguments[1]);
                            arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));
                            arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                            """,
                            color_picker,
                            hex_color,
                        )
                    
                    if color_text:
                        from selenium.webdriver.common.keys import Keys
                        color_text.click()
                        time.sleep(0.1)
                        color_text.send_keys(Keys.CONTROL + "a")
                        color_text.send_keys(Keys.DELETE)
                        color_text.send_keys(hex_color)
                        time.sleep(0.1)
                        self.driver.execute_script("arguments[0].blur()", color_text)
                    logger.info(f"    → Icon color: {hex_color}")
                except Exception as ce:
                    logger.warning(f"    ⚠ Could not set icon color: {ce}")

            # ── 5. Toggle option ────────────────────────────────
            toggle = icon_data.get("toggle_option", "both").lower()
            toggle_map = {
                "both": "IsBoth",
                "side menu": "IsSidebarMenu",
                "dashboard only": "IsIcon",
            }
            cb_name = toggle_map.get(toggle, "IsBoth")
            cb = self.driver.find_element(By.NAME, cb_name)
            if not cb.is_selected():
                self.driver.execute_script("arguments[0].click();", cb)
            logger.info(f"    → Toggle: {toggle}")

            # ── 6. Upload image ─────────────────────────────────
            img_path = icon_data.get("image_path", "")
            if img_path and Path(img_path).exists():
                file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                file_input.send_keys(str(Path(img_path).absolute()))
                time.sleep(2)  # let preview load
                logger.info(f"    → Image uploaded: {Path(img_path).name}")
            else:
                logger.warning(f"    ⚠ Image not found: {img_path}")
                # Discard and skip
                self.driver.find_element(
                    By.XPATH, "//button[contains(text(),'Discard')]"
                ).click()
                time.sleep(1)
                return False

            # ── 7. Submit ───────────────────────────────────────
            WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add Icon')]")
                )
            ).click()
            logger.info("    → Form submitted")

            # ── 8. Wait for form to close (list reappears) ──────
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'Add New Icon')]")
                )
            )
            # Wait for the success toast to vanish before next click
            self._wait_toast_gone()
            time.sleep(0.5)
            logger.info(f"  ✓ Icon added: {display}\n")
            return True

        except Exception as e:
            logger.error(f"  ✗ Failed to add [{display}]: {e}")
            self._take_screenshot(f"error_{display.replace(' ', '_')}")
            # Try to discard so form doesn't block next icon
            try:
                d = self.driver.find_element(
                    By.XPATH, "//button[contains(text(),'Discard')]"
                )
                d.click()
                time.sleep(1)
            except Exception:
                pass
            return False

    # ─────────────────────────────────────────────
    # Batch processing  (supports "all" user types)
    # ─────────────────────────────────────────────
    def process_icons_batch(self, icons_list):
        """
        icons_list entries support  user_type = "all"
        which will expand to every user type found in the dropdown.
        """
        logger.info(f"Starting batch – {len(icons_list)} configured entries")

        # Expand "all" user type entries
        available_user_types = None
        expanded = []
        for entry in icons_list:
            if str(entry.get("user_type", "")).lower() == "all":
                if available_user_types is None:
                    available_user_types = self.get_available_user_types()
                    logger.info(
                        f"Available user types: {[t for _, t in available_user_types]}"
                    )
                for _, utype_text in available_user_types:
                    new_entry = dict(entry)
                    new_entry["user_type"] = utype_text
                    expanded.append(new_entry)
            else:
                expanded.append(entry)

        logger.info(f"Total icons to upload after expansion: {len(expanded)}")
        logger.info("=" * 60)

        successful = 0
        failed = 0

        for idx, icon_data in enumerate(expanded, 1):
            logger.info(f"[{idx}/{len(expanded)}]")
            if self.add_icon(icon_data):
                successful += 1
            else:
                failed += 1
            time.sleep(1)

        logger.info("=" * 60)
        logger.info(f"Batch complete → ✓ {successful} succeeded  ✗ {failed} failed")
        return successful, failed

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────
    def _take_screenshot(self, name):
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

    def __enter__(self):
        self.setup_driver()
        return self

    def __exit__(self, *_):
        self.close()
