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
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

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

            self.driver = webdriver.Chrome(options=opts)
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

            # 3) Click Sign In  (the submit button)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            logger.info("  → Credentials submitted, waiting for agreement modal...")

            # 4) Wait for the agreement checkbox to appear
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.NAME, "agreement"))
            )

            # 5) Tick the agreement checkbox if not already checked
            cb = self.driver.find_element(By.NAME, "agreement")
            if not cb.is_selected():
                cb.click()
            time.sleep(0.5)

            # 6) Click "Continue To Dashboard"
            WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Continue To Dashboard')]")
                )
            ).click()
            logger.info("  → Agreement accepted, waiting for dashboard...")

            # 7) Wait until URL contains /vendor/dashboard
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
            add_btn = WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add New Icon')]")
                )
            )
            add_btn.click()
            time.sleep(2)

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

            # ── 1. Click "Add New Icon" ─────────────────────────
            WebDriverWait(self.driver, self.wait_time).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add New Icon')]")
                )
            ).click()
            time.sleep(2)

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
            except Exception:
                Select(
                    self.driver.find_element(By.NAME, "IconName")
                ).select_by_visible_text(icon_data["icon_identity"])
            logger.info(f"    → Icon identity: {icon_data['icon_identity']}")

            # ── 4. Enter Display Title ──────────────────────────
            name_field = self.driver.find_element(By.NAME, "Name")
            name_field.clear()
            name_field.send_keys(icon_data["display_title"])
            logger.info(f"    → Display title: {icon_data['display_title']}")

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
            time.sleep(1)
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
