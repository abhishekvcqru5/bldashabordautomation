"""
Old Dashboard Migration Module
Handles extraction of Introduction Screens from the old dashboard (vcqru.com)
and uploading them to the new dashboard (app.vcqru.com).
"""

import logging
import time
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from intro_screen import IntroImageProcessor, IntroScreenAutomation
from banner_promotion import BannerImageProcessor, BannerAutomation

logger = logging.getLogger(__name__)

OLD_DASHBOARD_URL = "https://www.vcqru.com/loginVcqru.aspx"
IMAGE_SAVE_DIR = Path(__file__).resolve().parent.parent / "old_dashboard_intro_image"

class OldDashboardExtractor:
    """Extracts data from the old VCQRU dashboard."""

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)
        IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)

    def _ss(self, name):
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"old_dash_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def _find_by_text_js(self, needle, tags=None):
        """
        Find a visible element containing text using DOM innerText.
        Useful for old portals where Selenium text/XPath matching is inconsistent.
        """
        if tags is None:
            tags = ["a", "li", "span", "div"]
        script = """
            const needle = arguments[0].toLowerCase();
            const tags = arguments[1];
            const out = [];
            for (const tag of tags) {
              for (const el of document.querySelectorAll(tag)) {
                const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim().toLowerCase();
                if (!text) continue;
                const style = window.getComputedStyle(el);
                const visible = style && style.display !== "none" && style.visibility !== "hidden" && el.offsetParent !== null;
                if (visible && text.includes(needle)) out.push(el);
              }
            }
            return out.length ? out[0] : null;
        """
        return self.driver.execute_script(script, needle, tags)

    def login(self, email, password):
        """Login to the old dashboard and verify landing state."""
        try:
            logger.info(f"Opening old dashboard login: {OLD_DASHBOARD_URL}")
            self.driver.get(OLD_DASHBOARD_URL)
            time.sleep(4)
            
            # 1. Select Vendor mode
            logger.info("  → Identifying 'Vendor' login tab...")
            
            vendor_clicked = False
            # Strategy A: Label click (most reliable for ASP.NET radio/checkbox skins)
            try:
                # Look for the label text "Vendor" specifically
                labels = self.driver.find_elements(By.TAG_NAME, "label")
                for label in labels:
                    if "Vendor" in label.text:
                        logger.info(f"    ✓ Found label: '{label.text}', clicking...")
                        self.driver.execute_script("arguments[0].click();", label)
                        vendor_clicked = True
                        break
            except Exception as e:
                logger.debug(f"    - Label strategy failed: {e}")

            # Strategy B: Direct ID click
            if not vendor_clicked:
                try:
                    vendor_chk = self.driver.find_element(By.ID, "chkadmin")
                    self.driver.execute_script("arguments[0].click();", vendor_chk)
                    vendor_clicked = True
                    logger.info("    ✓ Selected Vendor via direct ID 'chkadmin'")
                except Exception as e:
                    logger.debug(f"    - ID strategy failed: {e}")

            time.sleep(3) # Wait for Vendor fields to become visible

            # 2. Fill credentials
            logger.info("  → Filling Vendor credentials...")
            try:
                # We need to make sure we are using the VISIBLE fields
                # On this site, there are multiple login forms. We want the Vendor one.
                email_field = self.wait.until(EC.visibility_of_element_located((By.ID, "login_txt_id")))
                pass_field = self.driver.find_element(By.ID, "login_txt_pass")
                login_btn = self.driver.find_element(By.ID, "btnVendor")

                email_field.clear()
                email_field.send_keys(email)
                pass_field.clear()
                pass_field.send_keys(password)
                
                logger.info(f"    - Email entered: {email}")
                logger.info("    - Clicking 'login' button...")
                
                # Use JS click for background task reliability, fallback to selenium click
                try:
                    self.driver.execute_script("arguments[0].click();", login_btn)
                except Exception:
                    login_btn.click()
                
            except Exception as e:
                logger.error(f"  ✗ Failed to fill/submit credentials: {e}")
                self._ss("fill_submit_error")
                return False

            # 3. Wait for actual post-login state
            logger.info("  → Waiting for successful login redirect...")
            success = False
            for _ in range(60):
                current_url = self.driver.current_url.lower()
                in_login_page = "login.aspx" in current_url

                sidebar_visible = bool(
                    self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(normalize-space(.), 'Build Loyalty App') or "
                        "contains(normalize-space(.), 'Dashboard')]",
                    )
                )
                logout_visible = bool(
                    self.driver.find_elements(
                        By.XPATH, "//a[contains(normalize-space(.), 'Logout')]"
                    )
                )

                if (not in_login_page and logout_visible) or (sidebar_visible and logout_visible):
                    logger.info(f"✓ Redirected to: {self.driver.current_url}")
                    success = True
                    break
                time.sleep(1)

            if not success:
                logger.error("  ✗ Login timed out. Still on login page or unknown landing page.")
                self._ss("login_timeout_fail")
                return False

            return True
        except Exception as e:
            logger.error(f"Old dashboard login failed: {e}")
            self._ss("login_exception")
            return False

    def navigate_to_intro_settings(self):
        """Navigate to Build Loyalty -> Introduction Setting."""
        try:
            logger.info(f"Navigating to intro settings from: {self.driver.current_url}")

            self.driver.switch_to.default_content()

            # 1. Handle any potential popups/modals
            try:
                close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Close') or contains(text(), '×')] | //a[contains(@class, 'close')]")
                for btn in close_buttons:
                    if btn.is_displayed():
                        logger.info("    ✓ Found a popup, closing it...")
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
            except:
                pass

            time.sleep(5)

            # Build list of contexts to search
            all_frames = []
            for tag in ("frame", "iframe"):
                try:
                    all_frames.extend(self.driver.find_elements(By.TAG_NAME, tag))
                except:
                    pass
            contexts = [None] + all_frames

            logger.info(f"  → Searching sidebar for Loyalty App across {len(contexts)} context(s)")

            found_intro = False
            for ctx in contexts:
                try:
                    self.driver.switch_to.default_content()
                    if ctx is not None:
                        self.driver.switch_to.frame(ctx)

                    # Step 1: Find and click Build Loyalty App menu
                    loyalty = None
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_blapp > a")
                        if el.is_displayed():
                            loyalty = el
                    except:
                        pass

                    if not loyalty:
                        # Fallback text search
                        loyalty = self._find_by_text_js("build loyalty", ["a", "span", "li"])

                    if not loyalty:
                        continue  # Not in this context

                    logger.info("    ✓ Found Build Loyalty App menu, clicking...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", loyalty
                    )
                    time.sleep(3)

                    # Step 2: Find and click Introduction Setting submenu
                    intro_link = None
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_Liintro > a")
                        if el.is_displayed():
                            intro_link = el
                    except:
                        pass

                    if not intro_link:
                        # Fallback text search
                        intro_link = self._find_by_text_js("introduction setting", ["a", "li"])

                    if not intro_link:
                        # One retry — click loyalty again to re-expand and search again
                        self.driver.execute_script("arguments[0].click();", loyalty)
                        time.sleep(2)
                        intro_link = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_Liintro > a")

                    if not intro_link:
                        continue

                    logger.info("    ✓ Found Introduction Setting link, clicking...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", intro_link
                    )
                    time.sleep(5)
                    found_intro = True
                    break
                except Exception as frame_e:
                    logger.debug(f"    Context navigation failed: {frame_e}")
                    continue

            self.driver.switch_to.default_content()

            if not found_intro:
                logger.error("  ✗ Could not navigate to 'Introduction Setting'.")
                self._ss("loyalty_menu_not_found")
                return False

            return True

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            self._ss("nav_exception")
            return False

    def _download_image_with_session(self, image_url, local_path):
        """Download image from old dashboard using browser cookies."""
        session = requests.Session()
        for cookie in self.driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])
        parsed = urlparse(self.driver.current_url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": referer,
        }
        response = session.get(image_url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(1024):
                if chunk:
                    f.write(chunk)

    def extract_intro_screens(self):
        """
        Extract header, content, and image from the old dashboard.
        Returns a list of dicts: {header, description, image_path}
        """
        screens = []
        try:
            logger.info("  → Searching for introduction screens data...")
            
            # Find all switchable contexts
            all_frames = []
            for tag in ("frame", "iframe"):
                try:
                    all_frames.extend(self.driver.find_elements(By.TAG_NAME, tag))
                except:
                    pass
            contexts = [None] + all_frames

            table = None
            for ctx in contexts:
                try:
                    self.driver.switch_to.default_content()
                    if ctx is not None:
                        self.driver.switch_to.frame(ctx)
                        
                    # 1. Try to find the specific grid/table
                    # Common ASP.NET grid IDs
                    for selector in ["dataTable", "gvIntro", "IntroGrid", "dgIntro", "ContentPlaceHolder1_gvIntro"]:
                        try:
                            t = self.driver.find_element(By.ID, selector)
                            if t.is_displayed():
                                table = t
                                logger.info(f"    ✓ Found table with ID: {selector} in context frame")
                                break
                        except:
                            continue
                    if table:
                        break
                except:
                    continue

            # 2. If not found by ID, try finding any table that looks relevant in each context
            if not table:
                for ctx in contexts:
                    try:
                        self.driver.switch_to.default_content()
                        if ctx is not None:
                            self.driver.switch_to.frame(ctx)
                        tables = self.driver.find_elements(
                            By.XPATH,
                            "//table[contains(@id, 'Intro') or contains(@id, 'intro') or .//img]",
                        )
                        if tables:
                            table = tables[0]
                            logger.info("    ✓ Found table by partial ID match")
                            break
                    except:
                        continue

            # 3. Get rows
            if not table:
                logger.warning("    ⚠ No intro screens table found. Trying general row search in default context...")
                self.driver.switch_to.default_content()
                all_rows = self.driver.find_elements(By.XPATH, "//table//tr")
            else:
                all_rows = table.find_elements(By.TAG_NAME, "tr")
            
            rows = []
            for r in all_rows:
                # Skip header rows
                if r.find_elements(By.TAG_NAME, "th"):
                    continue
                # Skip rows with no tds (like empty/styling rows)
                if not r.find_elements(By.TAG_NAME, "td"):
                    continue
                rows.append(r)
            
            if not rows:
                logger.warning("    ✗ No rows found in the table.")
                self._ss("no_rows_found")
                self.driver.switch_to.default_content()
                return []

            logger.info(f"    → Found {len(rows)} potential rows to extract")

            for i, row in enumerate(rows, 1):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4 and cells[3].find_elements(By.TAG_NAME, "img"):
                        # User's explicit table pattern:
                        # td:nth-child(2) -> cells[1] (header)
                        # td:nth-child(3) -> cells[2] (content)
                        # td:nth-child(4) > img -> cells[3].find_element(By.TAG_NAME, "img")
                        header = cells[1].text.strip()
                        description = cells[2].text.strip()
                        img_url = (cells[3].find_element(By.TAG_NAME, "img").get_attribute("src") or "").strip()
                    else:
                        # Fallback to standard heuristics
                        img_els = row.find_elements(By.TAG_NAME, "img")
                        if not img_els:
                            continue
                        
                        img_url = (img_els[0].get_attribute("src") or "").strip()
                        if not img_url:
                            continue
                        
                        if len(cells) < 3:
                            continue

                        # Try to identify header and description from cells
                        # We skip the image cell and any action/checkbox cells
                        text_cells = [c.text.strip() for c in cells if c.text.strip() and not c.find_elements(By.TAG_NAME, "img")]
                        
                        if len(text_cells) >= 2:
                            header = text_cells[0]
                            description = text_cells[1]
                        else:
                            # Fallback to positional
                            header = cells[1].text.strip()
                            description = cells[2].text.strip()

                    if not header or not description:
                        continue

                    # Download image
                    img_name = (
                        f"old_intro_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    )
                    local_path = IMAGE_SAVE_DIR / img_name
                    
                    logger.info(f"    → Downloading image for: {header[:30]}...")
                    try:
                        self._download_image_with_session(img_url, local_path)
                        screens.append({
                            "header": header,
                            "description": description,
                            "image_path": str(local_path)
                        })
                        logger.info(f"    ✓ Extracted {i}/{len(rows)}")
                    except Exception as dl_error:
                        logger.warning(f"    ⚠ Image download failed for row {i}: {dl_error}")

                except Exception as row_e:
                    logger.debug(f"    ⚠ Error extracting row {i}: {row_e}")
                    continue

            self.driver.switch_to.default_content()
            return screens
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            self._ss("extraction_error")
            self.driver.switch_to.default_content()
            return []

    def navigate_to_banner_settings(self):
        """Navigate to Build Loyalty -> Banner Setting."""
        try:
            logger.info(f"Navigating to banner settings from: {self.driver.current_url}")

            self.driver.switch_to.default_content()

            # 1. Handle any potential popups/modals
            try:
                close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Close') or contains(text(), '×')] | //a[contains(@class, 'close')]")
                for btn in close_buttons:
                    if btn.is_displayed():
                        logger.info("    ✓ Found a popup, closing it...")
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
            except:
                pass

            time.sleep(5)

            # Build list of contexts to search
            all_frames = []
            for tag in ("frame", "iframe"):
                try:
                    all_frames.extend(self.driver.find_elements(By.TAG_NAME, tag))
                except:
                    pass
            contexts = [None] + all_frames

            logger.info(f"  → Searching sidebar for Loyalty App across {len(contexts)} context(s)")

            found_banner = False
            for ctx in contexts:
                try:
                    self.driver.switch_to.default_content()
                    if ctx is not None:
                        self.driver.switch_to.frame(ctx)

                    # Step 1: Find and click Build Loyalty App menu
                    loyalty = None
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_blapp > a")
                        if el.is_displayed():
                            loyalty = el
                    except:
                        pass

                    if not loyalty:
                        # Fallback text search
                        loyalty = self._find_by_text_js("build loyalty", ["a", "span", "li"])

                    if not loyalty:
                        continue  # Not in this context

                    logger.info("    ✓ Found Build Loyalty App menu, clicking...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", loyalty
                    )
                    time.sleep(3)

                    # Step 2: Find and click Banner Setting submenu
                    banner_link = None
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_bannerbl > a")
                        if el.is_displayed():
                            banner_link = el
                    except:
                        pass

                    if not banner_link:
                        # Fallback text search
                        banner_link = self._find_by_text_js("banner setting", ["a", "li"])

                    if not banner_link:
                        # One retry — click loyalty again to re-expand and search again
                        self.driver.execute_script("arguments[0].click();", loyalty)
                        time.sleep(2)
                        banner_link = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_bannerbl > a")

                    if not banner_link:
                        continue

                    logger.info("    ✓ Found Banner Setting link, clicking...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", banner_link
                    )
                    time.sleep(5)
                    found_banner = True
                    break
                except Exception as frame_e:
                    logger.debug(f"    Context navigation failed: {frame_e}")
                    continue

            self.driver.switch_to.default_content()

            if not found_banner:
                logger.error("  ✗ Could not navigate to 'Banner Setting'.")
                self._ss("banner_nav_fail")
                return False

            return True

        except Exception as e:
            logger.error(f"Navigation to banner settings failed: {e}")
            self._ss("banner_nav_exception")
            return False

    def extract_banners(self):
        """
        Extract banner images from the old dashboard.
        Returns a list of dicts: {image_path, title}
        """
        banners = []
        # Save dir for downloaded banners from old dashboard
        banner_save_dir = Path(__file__).resolve().parent.parent / "old_dashboard_banners"
        banner_save_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info("  → Searching for banner images data...")
            
            # Find all switchable contexts
            all_frames = []
            for tag in ("frame", "iframe"):
                try:
                    all_frames.extend(self.driver.find_elements(By.TAG_NAME, tag))
                except:
                    pass
            contexts = [None] + all_frames
                
            img_elements = []
            active_ctx = None
            for idx, frame in enumerate(contexts):
                try:
                    self.driver.switch_to.default_content()
                    if frame:
                        self.driver.switch_to.frame(frame)
                        
                    # Find banner images inside container
                    # We look for the user's specific selector first
                    container_css = "#page-content-wrapper > div > div > div > div > div.card-body.card-body-nopadding > div.col-lg-12"
                    img_selectors = [
                        f"{container_css} img",
                        "//div[contains(@class, 'card-body-nopadding')]//img",
                        "//img[contains(@src, 'Banner') or contains(@src, 'banner')]",
                    ]
                    
                    for sel in img_selectors:
                        if sel.startswith("//"):
                            els = self.driver.find_elements(By.XPATH, sel)
                        else:
                            els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        
                        # filter visible and valid src elements
                        valid_els = []
                        for el in els:
                            src = (el.get_attribute("src") or "").strip()
                            if src and "logo" not in src.lower() and "splash" not in src.lower():
                                valid_els.append((el, src))
                        
                        if valid_els:
                            img_elements = valid_els
                            active_ctx = frame
                            logger.info(f"    ✓ Found {len(img_elements)} banners via selector: {sel} in frame {idx}")
                            break
                    
                    if img_elements:
                        break
                except Exception as frame_e:
                    continue
            
            if not img_elements:
                logger.warning("    ✗ No banner images found.")
                self._ss("no_banners_found")
                self.driver.switch_to.default_content()
                return []
                
            # Make sure we are in the correct frame to access elements
            self.driver.switch_to.default_content()
            if active_ctx:
                self.driver.switch_to.frame(active_ctx)

            for i, (el, img_url) in enumerate(img_elements, 1):
                try:
                    # Deriving name and title
                    img_name = f"old_banner_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    local_path = banner_save_dir / img_name
                    
                    logger.info(f"    → Downloading banner {i}: {img_url}")
                    self._download_image_with_session(img_url, local_path)
                    
                    banners.append({
                        "title": f"old_banner_{i}",
                        "image_path": str(local_path)
                    })
                except Exception as e:
                    logger.warning(f"    ⚠ Failed to download banner {i}: {e}")
                    
            self.driver.switch_to.default_content()
            return banners
        except Exception as e:
            logger.error(f"Banner extraction failed: {e}")
            self._ss("banner_extraction_error")
            self.driver.switch_to.default_content()
            return []

    def navigate_to_gift_settings(self):
        """Navigate to Build Loyalty -> Gift Setting."""
        try:
            logger.info(f"Navigating to gift settings from: {self.driver.current_url}")

            self.driver.switch_to.default_content()

            # 1. Handle any potential popups/modals
            try:
                close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Close') or contains(text(), '×')] | //a[contains(@class, 'close')]")
                for btn in close_buttons:
                    if btn.is_displayed():
                        logger.info("    ✓ Found a popup, closing it...")
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
            except:
                pass

            time.sleep(5)

            # Build list of contexts to search
            all_frames = []
            for tag in ("frame", "iframe"):
                try:
                    all_frames.extend(self.driver.find_elements(By.TAG_NAME, tag))
                except:
                    pass
            contexts = [None] + all_frames

            logger.info(f"  → Searching sidebar for Loyalty App across {len(contexts)} context(s)")

            found_gift = False
            for ctx in contexts:
                try:
                    self.driver.switch_to.default_content()
                    if ctx is not None:
                        self.driver.switch_to.frame(ctx)

                    # Step 1: Find and click Build Loyalty App menu
                    loyalty = None
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_blapp > a")
                        if el.is_displayed():
                            loyalty = el
                    except:
                        pass

                    if not loyalty:
                        # Fallback text search
                        loyalty = self._find_by_text_js("build loyalty", ["a", "span", "li"])

                    if not loyalty:
                        continue  # Not in this context

                    logger.info("    ✓ Found Build Loyalty App menu, clicking...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", loyalty
                    )
                    time.sleep(3)

                    # Step 2: Find and click Gift submenu
                    gift_link = None
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_Libapp6 > a")
                        if el.is_displayed():
                            gift_link = el
                    except:
                        pass

                    if not gift_link:
                        # Fallback text search
                        gift_link = self._find_by_text_js("gift", ["a", "li"])

                    if not gift_link:
                        # One retry — click loyalty again to re-expand and search again
                        self.driver.execute_script("arguments[0].click();", loyalty)
                        time.sleep(2)
                        gift_link = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_Libapp6 > a")

                    if not gift_link:
                        continue

                    logger.info("    ✓ Found Gift Setting link, clicking...")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", gift_link
                    )
                    time.sleep(5)
                    found_gift = True
                    break
                except Exception as frame_e:
                    logger.debug(f"    Context navigation failed: {frame_e}")
                    continue

            self.driver.switch_to.default_content()

            if not found_gift:
                logger.error("  ✗ Could not navigate to 'Gift Setting'.")
                self._ss("gift_menu_not_found")
                return False

            return True

        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            self._ss("nav_exception")
            return False

    def extract_gifts(self):
        """
        Extract gift name, points, value, description, and image from the old dashboard.
        Returns a list of dicts: {name, points, value, description, image_path}
        """
        gifts = []
        gift_save_dir = Path(__file__).resolve().parent.parent / "old_dashboard_gifts"
        gift_save_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info("  → Searching for gifts data...")

            # Find all switchable contexts
            all_frames = []
            for tag in ("frame", "iframe"):
                try:
                    all_frames.extend(self.driver.find_elements(By.TAG_NAME, tag))
                except:
                    pass
            contexts = [None] + all_frames

            table = None
            for ctx in contexts:
                try:
                    self.driver.switch_to.default_content()
                    if ctx is not None:
                        self.driver.switch_to.frame(ctx)

                    # Try to find the specific table by ID 'dataTable'
                    try:
                        t = self.driver.find_element(By.ID, "dataTable")
                        if t.is_displayed():
                            table = t
                            logger.info("    ✓ Found table with ID: dataTable in context frame")
                            break
                    except:
                        continue
                except:
                    continue

            if not table:
                # If not found in frames, try in default context
                self.driver.switch_to.default_content()
                try:
                    table = self.driver.find_element(By.ID, "dataTable")
                    logger.info("    ✓ Found table with ID: dataTable in default context")
                except:
                    pass

            if not table:
                logger.warning("    ✗ No 'dataTable' found for gifts. Trying to find any table with relevant headers...")
                # Try finding any table
                # We will check if there is any table visible
                self.driver.switch_to.default_content()
                for ctx in contexts:
                    try:
                        self.driver.switch_to.default_content()
                        if ctx is not None:
                            self.driver.switch_to.frame(ctx)
                        tables = self.driver.find_elements(By.TAG_NAME, "table")
                        if tables:
                            table = tables[0]
                            logger.info("    ✓ Found a table in frame context")
                            break
                    except:
                        continue

            if not table:
                logger.error("    ✗ Could not find the gifts table.")
                self._ss("no_gifts_table")
                return []

            # Let's find the rows
            all_rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
            if not all_rows:
                all_rows = table.find_elements(By.TAG_NAME, "tr")

            rows = []
            for r in all_rows:
                # Skip header rows
                if r.find_elements(By.TAG_NAME, "th"):
                    continue
                # Skip rows with no tds
                if not r.find_elements(By.TAG_NAME, "td"):
                    continue
                rows.append(r)

            if not rows:
                logger.warning("    ✗ No rows found in the table.")
                self._ss("no_gift_rows")
                return []

            logger.info(f"    → Found {len(rows)} potential gift rows to extract")

            for i, row in enumerate(rows, 1):
                try:
                    # selectors from prompt:
                    # image selector: tr:nth-child(i) > td.gift-imgs > img
                    # description selector: tr:nth-child(i) > td:nth-child(7)
                    # value selector: tr:nth-child(i) > td:nth-child(6)
                    # point selector: tr:nth-child(i) > td:nth-child(5)
                    # name selector: tr:nth-child(i) > td:nth-child(4)
                    
                    try:
                        img_el = row.find_element(By.CSS_SELECTOR, "td.gift-imgs > img")
                        img_url = (img_el.get_attribute("src") or "").strip()
                    except Exception:
                        # Fallback image search
                        img_els = row.find_elements(By.TAG_NAME, "img")
                        img_url = (img_els[0].get_attribute("src") or "").strip() if img_els else ""

                    # Using indices
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 7:
                        logger.warning(f"      Row {i} has only {len(cells)} cells, skipping")
                        continue
                    
                    name = cells[3].text.strip()
                    points = cells[4].text.strip()
                    value = cells[5].text.strip()
                    description = cells[6].text.strip()

                    if not name or not img_url:
                        logger.warning(f"      Row {i} is missing name or image URL, skipping")
                        continue

                    # Download image
                    from urllib.parse import urlparse
                    parsed_url = urlparse(img_url)
                    suffix = Path(parsed_url.path).suffix
                    if not suffix or suffix.lower() not in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
                        suffix = ".jpg"  # default fallback

                    safe_name = "".join([c if c.isalnum() else "_" for c in name])
                    img_name = f"gift_{safe_name}_{i}{suffix}"
                    local_path = gift_save_dir / img_name

                    logger.info(f"    → Downloading image for gift: '{name}'...")
                    try:
                        self._download_image_with_session(img_url, local_path)
                        gifts.append({
                            "name": name,
                            "points": points,
                            "value": value,
                            "description": description,
                            "image_path": str(local_path)
                        })
                        logger.info(f"    ✓ Extracted gift {i}: '{name}' (Points: {points}, Value: {value})")
                    except Exception as dl_error:
                        logger.warning(f"    ⚠ Image download failed for gift '{name}': {dl_error}")

                except Exception as row_e:
                    logger.debug(f"    ⚠ Error extracting row {i}: {row_e}")
                    continue

            self.driver.switch_to.default_content()
            return gifts

        except Exception as e:
            logger.error(f"Gift extraction failed: {e}")
            self._ss("gift_extraction_error")
            self.driver.switch_to.default_content()
            return []

def run_old_dashboard_migration(email, password, new_auto=None):
    """
    Main migration flow:
    1. Extract from old dashboard
    2. Process images (force resize)
    3. Upload to new dashboard
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    
    logger.info("=" * 60)
    logger.info("OLD DASHBOARD MIGRATION — Extraction")
    logger.info("=" * 60)

    # 1. Setup temporary driver for old dashboard
    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-notifications")
    # Removed headless so user can see it
    
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
        logger.info(f"  Using system Chrome binary: {system_chrome}")
    
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
    old_driver.maximize_window()
    
    try:
        extractor = OldDashboardExtractor(old_driver)
        if not extractor.login(email, password):
            return False
        
        if not extractor.navigate_to_intro_settings():
            return False
        
        extracted_data = extractor.extract_intro_screens()
        old_driver.quit()

        if not extracted_data:
            logger.error("No data extracted from old dashboard.")
            return False

        logger.info(f"✓ Extracted {len(extracted_data)} screens.")

        # 2. Process extracted images using the new forced-resize logic
        logger.info("\n" + "=" * 60)
        logger.info("OLD DASHBOARD MIGRATION — Processing Images")
        logger.info("=" * 60)
        
        processor = IntroImageProcessor()
        processed_slides = []
        
        for data in extracted_data:
            # Resize image to 1080x1920!
            processed_path = processor.process(data["image_path"])
            if processed_path:
                processed_slides.append({
                    "header": data["header"],
                    "description": data["description"],
                    "image_path": processed_path
                })

        if not processed_slides:
            logger.error("No images could be processed. Aborting migration.")
            return False

        # 3. Upload to new dashboard using existing IntroScreenAutomation
        logger.info("\n" + "=" * 60)
        logger.info("OLD DASHBOARD MIGRATION — Uploading to New Dashboard")
        logger.info("=" * 60)

        from dashboard_automation import VendorPortalAutomation
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                return False
            
            intro_auto = IntroScreenAutomation(auto.driver)
            if not intro_auto.navigate():
                return False

            successful, failed = intro_auto.launch_all(processed_slides)
            return failed == 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'old_driver' in locals(): old_driver.quit()
        return False


def run_old_dashboard_banner_migration(email, password):
    """
    Full workflow for banner migration:
    1. Extract banners from old dashboard
    2. Process images (force resize to 1920x1080, compress)
    3. Upload/Publish to new dashboard
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from banner_promotion import BannerImageProcessor, BannerAutomation
    
    logger.info("=" * 60)
    logger.info("OLD DASHBOARD BANNER MIGRATION — Extraction")
    logger.info("=" * 60)

    # 1. Setup temporary driver for old dashboard
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
        logger.info(f"  Using system Chrome binary: {system_chrome}")
    
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
    old_driver.maximize_window()
    
    try:
        extractor = OldDashboardExtractor(old_driver)
        if not extractor.login(email, password):
            return False
        
        if not extractor.navigate_to_banner_settings():
            return False
        
        extracted_data = extractor.extract_banners()
        old_driver.quit()

        if not extracted_data:
            logger.error("No banners extracted from old dashboard.")
            return False

        logger.info(f"✓ Extracted {len(extracted_data)} banners.")

        # 2. Process extracted images using BannerImageProcessor
        logger.info("\n" + "=" * 60)
        logger.info("OLD DASHBOARD BANNER MIGRATION — Processing Images")
        logger.info("=" * 60)
        
        processor = BannerImageProcessor()
        processed_banners = []
        
        for data in extracted_data:
            processed_path = processor.process(data["image_path"])
            if processed_path:
                processed_banners.append((data["title"], processed_path))

        if not processed_banners:
            logger.error("No banners could be processed. Aborting migration.")
            return False

        # 3. Upload to new dashboard using BannerAutomation
        logger.info("\n" + "=" * 60)
        logger.info("OLD DASHBOARD BANNER MIGRATION — Uploading to New Dashboard")
        logger.info("=" * 60)

        from dashboard_automation import VendorPortalAutomation
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                return False
            
            banner_auto = BannerAutomation(auto.driver)
            if not banner_auto.navigate():
                return False

            successful, failed = banner_auto.publish_all(processed_banners)
            return failed == 0

    except Exception as e:
        logger.error(f"Banner migration failed: {e}")
        if 'old_driver' in locals(): old_driver.quit()
        return False

def run_old_dashboard_gift_migration(email, password):
    """
    Migration flow for gifts:
    1. Extract gifts from old dashboard.
    2. Upload them to the new dashboard for all user types.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from gift_management import GiftManagementAutomation
    
    print()
    print("  ─── Old Dashboard Credentials ───")
    print("  Enter credentials of the old dashboard to copy gifts from.")
    old_email = input(f"  Old Email    [{email}]: ").strip()
    if not old_email:
        old_email = email
    
    import sys
    if not sys.stdin.isatty():
        old_password = input("  Old Password : ").strip()
    else:
        import getpass
        try:
            old_password = getpass.getpass("  Old Password : ").strip()
        except Exception:
            old_password = input("  Old Password : ").strip()
        
    if not old_password:
        old_password = password

    logger.info("=" * 60)
    logger.info("OLD DASHBOARD GIFT MIGRATION — Extraction")
    logger.info("=" * 60)

    # 1. Setup temporary driver for old dashboard
    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-notifications")
    
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
    
    old_driver = None
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
        old_driver = webdriver.Chrome(service=service, options=opts)
    except Exception as err:
        logger.warning(f"  ⚠ ChromeDriverManager setup failed: {err}. Falling back to default webdriver.Chrome().")
        try:
            old_driver = webdriver.Chrome(options=opts)
        except Exception as fallback_err:
            logger.error(f"  ✗ Fallback Chrome driver setup also failed: {fallback_err}")
            return False

    old_driver.maximize_window()
    
    extracted_gifts = []
    try:
        extractor = OldDashboardExtractor(old_driver)
        if not extractor.login(old_email, old_password):
            old_driver.quit()
            return False
        
        if not extractor.navigate_to_gift_settings():
            old_driver.quit()
            return False
        
        extracted_gifts = extractor.extract_gifts()
        old_driver.quit()

        if not extracted_gifts:
            logger.error("No gifts extracted from old dashboard.")
            return False

        logger.info(f"✓ Extracted {len(extracted_gifts)} gifts.")

    except Exception as e:
        logger.error(f"Gift extraction failed: {e}")
        if 'old_driver' in locals(): old_driver.quit()
        return False

    # 2. Upload to new dashboard using GiftManagementAutomation
    logger.info("\n" + "=" * 60)
    logger.info("OLD DASHBOARD GIFT MIGRATION — Uploading to New Dashboard")
    logger.info("=" * 60)

    from dashboard_automation import VendorPortalAutomation
    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed to new dashboard")
                return False
            
            time.sleep(2)
            gift_auto = GiftManagementAutomation(auto.driver)
            
            if not gift_auto.navigate():
                logger.error("✗ Failed to navigate to Gift Management")
                return False
                
            # Open Add New Gift modal once to detect select options and if it is multi-select
            logger.info("Opening Add New Gift modal to detect UserType dropdown...")
            
            # Find and click Add New Gift button
            add_btn = None
            selectors = [
                "//button[contains(., 'Add New Gift') or contains(., 'Add Gift') or contains(., 'New Gift')]",
                "div.px-6.py-4.flex.items-center.justify-between > button",
                "main div.space-y-8 button"
            ]
            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        add_btn = gift_auto.wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                    else:
                        add_btn = gift_auto.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    if add_btn:
                        break
                except Exception:
                    continue
                    
            if not add_btn:
                logger.error("✗ Could not locate 'Add New Gift' button during detection phase")
                return False
                
            add_btn.click()
            time.sleep(2)
            
            from selenium.webdriver.support.ui import Select
            select_el = gift_auto.driver.find_element(By.ID, "UserType")
            select_obj = Select(select_el)
            is_multiple = select_obj.is_multiple
            logger.info(f"Dropdown 'is_multiple' detected as: {is_multiple}")
            
            # Extract all user types
            target_user_types = []
            for option in select_obj.options:
                val = option.get_attribute("value")
                txt = option.text.strip()
                # Exclude placeholder options (empty value, or containing select)
                if val and txt and "select" not in txt.lower():
                    target_user_types.append(txt)
            
            logger.info(f"Detected target user types: {target_user_types}")
            
            if not target_user_types:
                logger.error("✗ No user types detected in dropdown. Discarding modal.")
                cancel_btn = gift_auto.driver.find_element(By.XPATH, "//button[contains(., 'Cancel') or contains(., 'Discard')]")
                cancel_btn.click()
                return False
            
            # Close/discard modal
            cancel_btn = gift_auto.driver.find_element(By.XPATH, "//button[contains(., 'Cancel') or contains(., 'Discard')]")
            cancel_btn.click()
            time.sleep(2)
            
            successful_uploads = 0
            failed_uploads = 0
            
            if is_multiple:
                logger.info("Proceeding with multi-select upload flow (one upload per gift)...")
                for idx, gift in enumerate(extracted_gifts, 1):
                    logger.info(f"Uploading Gift {idx} of {len(extracted_gifts)}: {gift['name']}")
                    if gift_auto.check_gift_exists(gift['name'], target_user_types[0]):
                        logger.info(f"  → Gift '{gift['name']}' already exists, skipping.")
                        successful_uploads += 1
                        continue
                    if gift_auto.add_new_gift(gift, target_user_types):
                        successful_uploads += 1
                    else:
                        failed_uploads += 1
                    time.sleep(1)
            else:
                logger.info("Proceeding with single-select sequential upload flow (each gift added once per user type)...")
                total_ops = len(extracted_gifts) * len(target_user_types)
                current_op = 0
                for gift in extracted_gifts:
                    for utype in target_user_types:
                        current_op += 1
                        if gift_auto.check_gift_exists(gift['name'], utype):
                            logger.info(f"[{current_op}/{total_ops}] Gift '{gift['name']}' already exists for '{utype}', skipping.")
                            successful_uploads += 1
                            continue
                        logger.info(f"[{current_op}/{total_ops}] Uploading: '{gift['name']}' for '{utype}'")
                        if gift_auto.add_new_gift(gift, [utype]):
                            successful_uploads += 1
                        else:
                            failed_uploads += 1
                        time.sleep(1)
                        
            logger.info("\n" + "=" * 60)
            logger.info("GIFTS MIGRATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful uploads/assignments: {successful_uploads}")
            logger.info(f"✗ Failed uploads/assignments: {failed_uploads}")
            logger.info("=" * 60)
            
            return failed_uploads == 0
            
    except Exception as e:
        logger.error(f"Unexpected error in gifts migration automation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
