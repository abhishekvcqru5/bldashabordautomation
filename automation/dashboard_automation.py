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

            # Allow geolocation automatically
            prefs = {
                "profile.default_content_setting_values.geolocation": 1,
                "profile.default_content_setting_values.notifications": 2
            }
            opts.add_experimental_option("prefs", prefs)

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

            try:
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
                self.driver = webdriver.Chrome(service=service, options=opts)
            except Exception as err:
                logger.warning(f"  ⚠ ChromeDriverManager setup failed: {err}. Falling back to default webdriver.Chrome().")
                self.driver = webdriver.Chrome(options=opts)

            # ── Grant geolocation permission via CDP (prevents Chrome's OS-level popup) ──
            try:
                self.driver.execute_cdp_cmd(
                    "Browser.grantPermissions",
                    {
                        "permissions": ["geolocation"],
                        "origin": "https://app.vcqru.com"
                    }
                )
                logger.info("  ✓ Geolocation permission granted via CDP (Browser.grantPermissions)")
            except Exception as perm_err:
                logger.warning(f"  ⚠ Browser.grantPermissions failed: {perm_err}")

            # ── Also override geolocation coordinates ──
            try:
                self.driver.execute_cdp_cmd(
                    "Emulation.setGeolocationOverride",
                    {
                        "latitude": 28.6139,
                        "longitude": 77.2090,
                        "accuracy": 100
                    }
                )
                logger.info("  ✓ Geolocation coordinates overridden via CDP")
            except Exception as cdp_err:
                logger.warning(f"  ⚠ Failed to override geolocation via CDP: {cdp_err}")

            self.driver.set_page_load_timeout(30)
            self.driver.maximize_window()
            logger.info("✓ Chrome driver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return False

    # ─────────────────────────────────────────────
    # Policy / Terms Agreement Popup Handler
    # ─────────────────────────────────────────────
    def _handle_policy_popup(self, wait_seconds=12):
        """
        Detects the policy/terms-agreement modal (fixed, z-50 overlay),
        checks the agreement checkbox, then clicks the Continue button.
        Returns True if the popup was found and handled, False if not present.
        """
        try:
            # Wait for the modal overlay — identified by its fixed+z-50 classes
            modal = WebDriverWait(self.driver, wait_seconds).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.fixed.inset-0.z-50.flex.items-center.justify-center"
                ))
            )
            logger.info("  → Policy agreement popup detected")

            # ── Step 1: find & tick the checkbox ──────────────────────────────
            checkbox_clicked = False

            # Try 1: <input type="checkbox"> anywhere inside the modal
            try:
                cb = modal.find_element(By.XPATH, ".//input[@type='checkbox']")
                if not cb.is_selected():
                    self.driver.execute_script("arguments[0].click();", cb)
                    logger.info("    ✓ Policy checkbox checked (input[type=checkbox])")
                else:
                    logger.info("    ✓ Policy checkbox was already checked")
                checkbox_clicked = True
            except Exception:
                pass

            # Try 2: custom toggle div (the user's specific CSS path inside the footer area)
            if not checkbox_clicked:
                try:
                    toggle_div = modal.find_element(
                        By.CSS_SELECTOR,
                        "div.p-5.border-t > div > div > div"
                    )
                    self.driver.execute_script("arguments[0].click();", toggle_div)
                    logger.info("    ✓ Policy toggle div clicked (CSS fallback)")
                    checkbox_clicked = True
                except Exception:
                    pass

            # Try 3: any clickable role=checkbox element
            if not checkbox_clicked:
                try:
                    role_cb = modal.find_element(By.XPATH, ".//*[@role='checkbox']")
                    self.driver.execute_script("arguments[0].click();", role_cb)
                    logger.info("    ✓ Policy checkbox clicked (role=checkbox fallback)")
                    checkbox_clicked = True
                except Exception:
                    pass

            if not checkbox_clicked:
                logger.warning("    ⚠ Could not find policy checkbox — attempting Continue anyway")

            time.sleep(0.5)

            # ── Step 2: click Continue button ─────────────────────────────────
            continue_clicked = False

            # Try 1: button text contains "Continue"
            try:
                btn = modal.find_element(
                    By.XPATH,
                    ".//button[contains(normalize-space(.), 'Continue')]"
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", btn)
                logger.info("    ✓ Clicked Continue button")
                continue_clicked = True
            except Exception:
                pass

            # Try 2: footer-area button (user's exact CSS path)
            if not continue_clicked:
                try:
                    btn = modal.find_element(
                        By.CSS_SELECTOR,
                        "div.p-5.border-t > div > button"
                    )
                    self.driver.execute_script("arguments[0].click();", btn)
                    logger.info("    ✓ Clicked Continue button (CSS fallback)")
                    continue_clicked = True
                except Exception:
                    pass

            if not continue_clicked:
                logger.warning("    ⚠ Could not find Continue button in policy popup")
                return False

            # Wait for the modal to disappear
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.invisibility_of_element(modal)
                )
                logger.info("    ✓ Policy popup dismissed")
            except Exception:
                pass  # Modal may have already gone

            time.sleep(1)
            return True

        except Exception:
            # Popup simply wasn't present — not an error
            logger.debug("  No policy agreement popup detected (not present or already dismissed)")
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

            # Check policy checkbox on the login page if present (pre-login page checkbox)
            try:
                login_agree_cb = self.driver.find_element(By.XPATH, "//input[@type='checkbox']")
                if not login_agree_cb.is_selected():
                    self.driver.execute_script("arguments[0].click();", login_agree_cb)
                    logger.info("  → Policy checkbox checked on login page")
            except Exception as cb_err:
                logger.debug(f"Could not find or click policy checkbox on login page: {cb_err}")

            # 3) Click Sign In  (the submit button)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            logger.info("  → Credentials submitted, waiting for post-login popups...")

            # ── Stage 1: handle policy/terms popup (appears right after login) ──
            self._handle_policy_popup(wait_seconds=12)

            # ── Stage 2: handle in-app "Allow Location Access" button (if site shows one) ──
            try:
                allow_loc_btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(normalize-space(.), 'Allow Location')]"
                    ))
                )
                logger.info("  → In-app 'Allow Location' button detected, clicking...")
                self.driver.execute_script("arguments[0].click();", allow_loc_btn)
                logger.info("    ✓ Clicked 'Allow Location Access'")
                time.sleep(2)
            except Exception:
                logger.debug("  No in-app 'Allow Location' button detected")

            # ── Stage 3: handle policy popup again if it re-appears after location step ──
            self._handle_policy_popup(wait_seconds=5)

            # 4) Navigate directly to App Settings URL
            logger.info("  → Navigating directly to App Settings URL...")
            self.driver.get(self.APP_SETTINGS)
            
            WebDriverWait(self.driver, self.wait_time).until(
                EC.url_contains("/vendor/app-settings")
            )

            logger.info("✓ Login successful and on App Settings page")
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
            select_obj = Select(ut_select)
            target = icon_data["user_type"]
            matched = False
            
            # Try to match by value first
            for opt in select_obj.options:
                val = opt.get_attribute("value")
                if val == target:
                    select_obj.select_by_value(val)
                    logger.info(f"    → User type selected by value: {val}")
                    matched = True
                    break
            
            # Try to match by visible text (case-insensitive and stripped)
            if not matched:
                target_clean = target.strip().lower()
                # Pass 1: exact match
                for opt in select_obj.options:
                    opt_text = opt.text.strip().lower()
                    if opt_text == target_clean:
                        select_obj.select_by_visible_text(opt.text)
                        logger.info(f"    → User type selected by exact text: {opt.text}")
                        matched = True
                        break
                
                # Pass 2: substring match (excluding placeholders)
                if not matched:
                    for opt in select_obj.options:
                        opt_text = opt.text.strip().lower()
                        if target_clean in opt_text and "select" not in opt_text:
                            select_obj.select_by_visible_text(opt.text)
                            logger.info(f"    → User type selected by substring text: {opt.text}")
                            matched = True
                            break
            
            if not matched:
                try:
                    select_obj.select_by_visible_text(target)
                    logger.info(f"    → User type selected by text (fallback): {target}")
                except Exception:
                    select_obj.select_by_value(target)
                    logger.info(f"    → User type selected by value (fallback): {target}")

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
                for utype_val, utype_text in available_user_types:
                    new_entry = dict(entry)
                    new_entry["user_type"] = utype_val
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
