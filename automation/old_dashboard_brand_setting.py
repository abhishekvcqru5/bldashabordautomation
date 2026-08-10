"""
Old Dashboard — Brand Setting Extractor
========================================
Connects to the OLD VCQRU dashboard (https://www.vcqru.com/login.aspx),
logs in as Vendor, then navigates to:
    Build Loyalty App → Brand Setting

Extracts and saves locally:
  • Logo image      → brandsetting/logo.<ext>
  • Splash image    → brandsetting/splash.<ext>
  • Company name    → brandsetting/brand_info.json

Login quirks handled:
  - Page uses ASP.NET WebForms with iframes/postbacks
  - Vendor checkbox must be selected before entering credentials
  - Wait conditions cover slow postback transitions
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from brand_setting import BrandImageProcessor, BrandSettingAutomation, SupportNetworkAutomation, extract_colors_from_logo
from dashboard_automation import VendorPortalAutomation

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
OLD_DASHBOARD_URL = "https://www.vcqru.com/login.aspx"
BRAND_SAVE_DIR = Path(__file__).resolve().parent.parent / "brandsetting"
SCREENSHOTS_DIR = Path(__file__).resolve().parent / "screenshots"
WAIT_TIME = 25  # seconds for WebDriverWait


# ── Utility helpers ───────────────────────────────────────────────────────────

def _ss(driver, label: str):
    """Take a debug screenshot."""
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        p = SCREENSHOTS_DIR / f"old_brand_{label}_{ts}.png"
        driver.save_screenshot(str(p))
        logger.info(f"  📸 Screenshot saved: {p}")
    except Exception as e:
        logger.warning(f"Screenshot failed: {e}")


def _download_with_session(driver, url: str, dest: Path) -> bool:
    """
    Download *url* to *dest* by reusing the browser's session cookies.
    Returns True on success.
    """
    if dest.exists():
        logger.info(f"  ↩ Already exists, skipping download: {dest.name}")
        return True

    try:
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])

        parsed = urlparse(driver.current_url)
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Referer": f"{parsed.scheme}://{parsed.netloc}/",
        }
        resp = session.get(url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(8192):
                if chunk:
                    fh.write(chunk)

        size_kb = dest.stat().st_size / 1024
        logger.info(f"  ✓ Downloaded: {dest.name}  ({size_kb:.1f} KB)")
        return True

    except Exception as e:
        logger.error(f"  ✗ Download failed [{url}]: {e}")
        return False


def _ext_from_url(url: str) -> str:
    """Return file extension from URL, defaulting to .jpg."""
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"} else ".jpg"


def _find_by_text_js(driver, needle: str, tags=None):
    """Find the first visible element whose text contains *needle* (case-insensitive)."""
    if tags is None:
        tags = ["a", "span", "li", "div", "td"]
    script = """
        const needle = arguments[0].toLowerCase();
        const tags   = arguments[1];
        for (const tag of tags) {
          for (const el of document.querySelectorAll(tag)) {
            const text = (el.innerText || el.textContent || "")
                            .replace(/\\s+/g, " ").trim().toLowerCase();
            if (!text) continue;
            const s = window.getComputedStyle(el);
            const vis = s && s.display !== "none" && s.visibility !== "hidden"
                           && el.offsetParent !== null;
            if (vis && text.includes(needle)) return el;
          }
        }
        return null;
    """
    return driver.execute_script(script, needle, tags)


# ── Main extractor class ──────────────────────────────────────────────────────

class OldDashboardBrandExtractor:
    """
    Handles full extraction of Brand Setting assets from the old VCQRU dashboard.
    """

    def __init__(self, driver, wait_time: int = WAIT_TIME):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    # ── Login ─────────────────────────────────────────────────────────────────
    def login(self, email: str, password: str) -> bool:
        """
        Open old dashboard, tick Vendor checkbox, enter credentials, submit.
        Returns True when post-login dashboard is detected.
        """
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
            logger.info("    → Filling credentials …")
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
                    _ss(self.driver, "no_login_btn")
                    return False

            # ── Step 4: Wait for post-login state ─────────────────────────────
            logger.info("    → Waiting for post-login redirect …")
            for _ in range(60):
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
            _ss(self.driver, "login_timeout")
            return False

        except Exception as e:
            logger.error(f"Login exception: {e}")
            _ss(self.driver, "login_exception")
            return False

    # ── Navigation ────────────────────────────────────────────────────────────
    def navigate_to_brand_setting(self) -> bool:
        """Navigate: Build Loyalty App → Brand Setting."""
        try:
            self.driver.switch_to.default_content()
            time.sleep(5)  # wait for frameset/sidebar to render

            # Collect all switchable contexts: default + every frame + every iframe
            # pie.aspx uses <frameset><frame> — NOT <iframe> — so we must scan both
            all_frames = []
            for tag in ("frame", "iframe"):
                all_frames += self.driver.find_elements(By.TAG_NAME, tag)
            contexts = [None] + all_frames  # None = default content

            for ctx in contexts:
                try:
                    self.driver.switch_to.default_content()
                    if ctx is not None:
                        self.driver.switch_to.frame(ctx)

                    # ── Step 1: Build Loyalty App ──────────────────────────────
                    # Use known CSS selector first; fall back to text scan
                    loyalty = None
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, "#ctl00_blapp > a")
                        if el.is_displayed():
                            loyalty = el
                    except Exception:
                        pass

                    if not loyalty:
                        # text-based JS scan (handles whitespace / encoding differences)
                        loyalty = self.driver.execute_script("""
                            var needle = 'build loyalty';
                            for (var el of document.querySelectorAll('a,li,span')) {
                                var txt = (el.innerText||el.textContent||'')
                                          .replace(/\\s+/g,' ').trim().toLowerCase();
                                var s = window.getComputedStyle(el);
                                if (txt.includes(needle) &&
                                    s.display!=='none' && s.visibility!=='hidden' &&
                                    el.offsetParent!==null) return el;
                            }
                            return null;
                        """)

                    if not loyalty:
                        continue  # not in this frame

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();",
                        loyalty
                    )
                    time.sleep(3)  # wait for submenu expansion / postback

                    # ── Step 2: Brand Setting ──────────────────────────────────
                    brand = None

                    # CSS selector attempt (sibling li under same parent)
                    for css in (
                        "#ctl00_blapp ~ li a[href*='Brand']",
                        "#ctl00_blapp ~ li a[href*='brand']",
                        "a[href*='BrandSetting']",
                        "a[href*='Brand_Setting']",
                        "a[href*='brandsetting']",
                    ):
                        try:
                            el = self.driver.find_element(By.CSS_SELECTOR, css)
                            if el.is_displayed():
                                brand = el
                                break
                        except Exception:
                            continue

                    # XPath text fallback
                    if not brand:
                        for xp in (
                            "//a[normalize-space()='Brand Setting']",
                            "//a[contains(text(),'Brand Setting')]",
                            "//li[contains(.,'Brand Setting')]//a",
                        ):
                            for el in self.driver.find_elements(By.XPATH, xp):
                                if el.is_displayed():
                                    brand = el
                                    break
                            if brand:
                                break

                    # JS text scan fallback
                    if not brand:
                        brand = self.driver.execute_script("""
                            var needle = 'brand setting';
                            for (var el of document.querySelectorAll('a,li')) {
                                var txt = (el.innerText||el.textContent||'')
                                          .replace(/\\s+/g,' ').trim().toLowerCase();
                                var s = window.getComputedStyle(el);
                                if (txt===needle &&
                                    s.display!=='none' && s.visibility!=='hidden' &&
                                    el.offsetParent!==null) return el;
                            }
                            return null;
                        """)

                    # One retry — click loyalty again to re-expand
                    if not brand:
                        self.driver.execute_script("arguments[0].click();", loyalty)
                        time.sleep(2)
                        brand = self.driver.execute_script("""
                            var needle = 'brand setting';
                            for (var el of document.querySelectorAll('a,li')) {
                                var txt = (el.innerText||el.textContent||'')
                                          .replace(/\\s+/g,' ').trim().toLowerCase();
                                if (txt.includes(needle) && el.offsetParent!==null) return el;
                            }
                            return null;
                        """)

                    if not brand:
                        continue

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();",
                        brand
                    )
                    time.sleep(5)  # wait for postback / page load

                    self.driver.switch_to.default_content()
                    print("[2/2] Brand Setting opened")
                    print("✓ Navigation success")
                    return True

                except Exception:
                    continue

            self.driver.switch_to.default_content()
            print("✗ Navigation failed")
            _ss(self.driver, "nav_brand_fail")
            return False

        except Exception:
            print("✗ Navigation failed")
            _ss(self.driver, "nav_exception")
            return False

    # ── Extraction ────────────────────────────────────────────────────────────
    def extract_brand_data(self) -> dict:
        """Extract brand and support data using exact selectors."""
        result = {
            "company_name": "", 
            "logo_url": "", 
            "splash_url": "",
            "phone": "",
            "email": "",
            "website": "",
            "terms_conditions": "",
            "support_content": "",
            "privacy_policy": ""
        }
        try:
            # Scan default content and all frames/iframes
            frames = [None] + self.driver.find_elements(By.TAG_NAME, "iframe") + self.driver.find_elements(By.TAG_NAME, "frame")
            for frame in frames:
                try:
                    self.driver.switch_to.default_content()
                    if frame: self.driver.switch_to.frame(frame)
                    
                    # Brand fields
                    if not result["company_name"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtcompanyName")
                            result["company_name"] = el.get_attribute("value") or ""
                        except: pass
                    
                    if not result["logo_url"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_imgLogoPreview")
                            result["logo_url"] = el.get_attribute("src") or ""
                        except: pass
                        
                    if not result["splash_url"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_imgSplashPreview")
                            result["splash_url"] = el.get_attribute("src") or ""
                        except: pass

                    # Support / Contact fields
                    if not result["phone"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtcontactusmobile")
                            result["phone"] = el.get_attribute("value") or ""
                        except: pass

                    if not result["email"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtcontactusemail")
                            result["email"] = el.get_attribute("value") or ""
                        except: pass

                    if not result["support_content"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtcon")
                            result["support_content"] = el.get_attribute("value") or ""
                        except: pass

                    if not result["terms_conditions"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtterm")
                            result["terms_conditions"] = el.get_attribute("value") or ""
                        except: pass

                    if not result["website"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtaboutus")
                            result["website"] = el.get_attribute("value") or ""
                        except: pass

                    if not result["privacy_policy"]:
                        try:
                            el = self.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtprevicypolicy")
                            result["privacy_policy"] = el.get_attribute("value") or ""
                        except: pass
                except: continue
                
            self.driver.switch_to.default_content()
            return result
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return result

    # ── Save ──────────────────────────────────────────────────────────────────
    def save_brand_data(self, data: dict) -> dict:
        """
        Download images and save company name to disk.

        Saves to:
          brandsetting/logo.<ext>
          brandsetting/splash.<ext>
          brandsetting/brand_info.json

        Returns a summary dict with local paths and status.
        """
        BRAND_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        summary = {
            "company_name": data.get("company_name", ""),
            "logo_path": None,
            "splash_path": None,
            "json_path": None,
            "logo_ok": False,
            "splash_ok": False,
            "json_ok": False,
        }

        # ── Download Logo ─────────────────────────────────────────────────────
        if data.get("logo_url"):
            ext = _ext_from_url(data["logo_url"])
            logo_dest = BRAND_SAVE_DIR / f"logo{ext}"
            ok = _download_with_session(self.driver, data["logo_url"], logo_dest)
            summary["logo_path"] = str(logo_dest)
            summary["logo_ok"] = ok
        else:
            logger.warning("  ⚠ No logo URL found — skipping logo download")

        # ── Download Splash ───────────────────────────────────────────────────
        if data.get("splash_url"):
            ext = _ext_from_url(data["splash_url"])
            splash_dest = BRAND_SAVE_DIR / f"splash{ext}"
            ok = _download_with_session(self.driver, data["splash_url"], splash_dest)
            summary["splash_path"] = str(splash_dest)
            summary["splash_ok"] = ok
        else:
            logger.warning("  ⚠ No splash URL found — skipping splash download")

        # ── Save company name JSON ────────────────────────────────────────────
        json_path = BRAND_SAVE_DIR / "brand_info.json"
        try:
            existing = {}
            if json_path.exists():
                try:
                    with open(json_path, "r") as fh:
                        existing = json.load(fh)
                except Exception:
                    existing = {}

            existing.update({
                "company_name": data.get("company_name", ""),
                "logo_url_source": data.get("logo_url", ""),
                "splash_url_source": data.get("splash_url", ""),
                "phone": data.get("phone", ""),
                "email": data.get("email", ""),
                "website": data.get("website", ""),
                "terms_conditions": data.get("terms_conditions", ""),
                "support_content": data.get("support_content", ""),
                "privacy_policy": data.get("privacy_policy", ""),
                "extracted_at": datetime.now().isoformat(),
            })

            with open(json_path, "w") as fh:
                json.dump(existing, fh, indent=2)

            logger.info(f"  ✓ brand_info.json saved: {json_path}")
            summary["json_path"] = str(json_path)
            summary["json_ok"] = True

        except Exception as e:
            logger.error(f"  ✗ Could not save brand_info.json: {e}")

        return summary


# ── Top-level runner ──────────────────────────────────────────────────────────

def run_old_dashboard_brand_setting(email: str, password: str) -> bool:
    """
    Full end-to-end flow:
      1. Launch Chrome
      2. Login to old dashboard (vcqru.com) as Vendor
      3. Navigate to Build Loyalty App → Brand Setting
      4. Extract company name, logo URL, splash URL
      5. Download images + save JSON to brandsetting/
      6. Print summary and return True/False
    """
    logger.info("=" * 60)
    logger.info("OLD DASHBOARD — Brand Setting Extraction")
    logger.info("=" * 60)

    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    
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
    driver = webdriver.Chrome(service=service, options=opts)
    driver.maximize_window()

    try:
        extractor = OldDashboardBrandExtractor(driver)

        # ── 1. Login ───────────────────────────────────────────────────────────
        logger.info("\n[1/4] Logging in to old dashboard …")
        if not extractor.login(email, password):
            logger.error("✗ Login failed. Aborting.")
            return False

        # ── 2. Navigate ────────────────────────────────────────────────────────
        logger.info("\n[2/4] Navigating to Build Loyalty App → Brand Setting …")
        if not extractor.navigate_to_brand_setting():
            logger.error("✗ Navigation failed. Aborting.")
            return False

        # ── 3. Extract ─────────────────────────────────────────────────────────
        logger.info("\n[3/4] Extracting brand data …")
        data = extractor.extract_brand_data()

        if not data["company_name"] and not data["logo_url"] and not data["splash_url"]:
            logger.error("✗ No brand data could be extracted. Check screenshots for debug info.")
            return False

        # ── 4. Save ────────────────────────────────────────────────────────────
        logger.info("\n[4/4] Saving assets to disk …")
        summary = extractor.save_brand_data(data)
        driver.quit()

        # ── 5. Transfer to Current Dashboard ───────────────────────────────────
        logger.info("\n[5/5] Transferring to current dashboard (app.vcqru.com) …")
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login(): return False
            
            # Process images
            proc = BrandImageProcessor()
            l_path = proc.process_logo(summary["logo_path"]) if summary["logo_ok"] else None
            s_path = proc.process_splash(summary["splash_path"]) if summary["splash_ok"] else None
            
            # Extract colors & Upload
            colors = extract_colors_from_logo(summary["logo_path"]) if summary["logo_ok"] else {}
            brand_auto = BrandSettingAutomation(auto.driver)
            
            if brand_auto.navigate():
                brand_auto.fill_and_save(
                    company_name=summary["company_name"],
                    logo_path=l_path,
                    splash_path=s_path,
                    colors=colors
                )

            # Support Network
            support_auto = SupportNetworkAutomation(auto.driver)
            if support_auto.navigate():
                return support_auto.fill_and_save({
                    "phone": data.get("phone", ""),
                    "email": data.get("email", ""),
                    "website": data.get("website", ""),
                    "terms_conditions": data.get("terms_conditions", ""),
                    "support_content": data.get("support_content", ""),
                    "privacy_policy": data.get("privacy_policy", "")
                })
        return False

    except Exception as e:
        logger.error(f"Unexpected error in brand setting extraction: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        try:
            driver.quit()
            logger.info("  Browser closed")
        except Exception:
            pass
