"""
Brand Setting Automation
Handles Identity & Branding on the VCQRU vendor portal:
  - Company Name        (asked at runtime)
  - Colors              (Header / Footer / Body / Background — from config, optional)
  - App Logo            512×512 px, max 2 MB
  - Splash Screen       1080×1080 px, max 10 MB

Kept fully separate from dashboard_icons code.
"""

import logging
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"


# ══════════════════════════════════════════════════════════════
# Auto color extractor — reads the logo at runtime, derives palette
# ══════════════════════════════════════════════════════════════
def _rgb_to_hex(r, g, b):
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken(r, g, b, factor=0.65):
    """Return a darker shade by multiplying each channel by factor."""
    return int(r * factor), int(g * factor), int(b * factor)


def _is_grey(r, g, b, threshold=30):
    """True if the colour is close to neutral grey."""
    return max(abs(r - g), abs(g - b), abs(r - b)) < threshold


def extract_colors_from_logo(logo_path):
    """
    Read *logo_path*, find its dominant brand colour, and return a
    ready-to-use 4-colour palette dict.

    Palette rules (fixed, as requested):
        header_color     — dominant logo colour (medium-dark)
        background_color — 35 % darker version of the dominant colour
        body_color       — always #FFFFFF  (pure white)
        footer_color     — always #F5F5F5  (near-white / light)

    If the logo is fully greyscale / no saturated pixels are found,
    the darkest representative neutral tone is used instead.

    Returns
    -------
    dict with the four colour keys, or None on error.
    """
    src = Path(logo_path)
    if not src.exists():
        logger.error(f"Logo not found for colour extraction: {logo_path}")
        return None

    try:
        img = Image.open(src).convert("RGB")
        pixels = list(img.getdata())

        # ── 1. Collect saturated (colourful) pixels ─────────────────
        saturated = []
        for r, g, b in pixels:
            brightness = (r + g + b) / 3
            mx = max(r, g, b)
            saturation = (mx - min(r, g, b)) / (mx + 1)
            if saturation > 0.18 and 25 < brightness < 235:
                # bucket into groups of 16 for clustering
                saturated.append((r // 16 * 16, g // 16 * 16, b // 16 * 16))

        # ── 2. Find dominant colour ──────────────────────────────
        dominant = None

        if saturated:
            top = Counter(saturated).most_common()
            # pick first non-grey bucket
            for (r, g, b), _ in top:
                if not _is_grey(r, g, b):
                    dominant = (r, g, b)
                    break

        # ── 3. Fallback: darkest non-white grey in the logo ────────
        if dominant is None:
            logger.info("  No saturated colour found — using darkest neutral tone")
            greys = [
                (r, g, b)
                for r, g, b in pixels
                if _is_grey(r, g, b) and (r + g + b) / 3 < 180
            ]
            if greys:
                avg = (
                    int(sum(x[0] for x in greys) / len(greys)),
                    int(sum(x[1] for x in greys) / len(greys)),
                    int(sum(x[2] for x in greys) / len(greys)),
                )
                dominant = avg
            else:
                dominant = (45, 45, 45)  # absolute fallback: dark charcoal

        dr, dg, db = dominant
        darker = _darken(dr, dg, db, factor=0.65)

        palette = {
            "header_color": _rgb_to_hex(dr, dg, db),  # logo colour
            "background_color": _rgb_to_hex(*darker),  # 35% darker
            "body_color": "#FFFFFF",  # always white
            "footer_color": "#F5F5F5",  # always near-white
        }

        # ── 4. Log the palette so the user can see it ────────────
        logger.info("  Colours extracted from logo:")
        logger.info(
            f"    Header Color     →  {palette['header_color']}  (dominant logo colour)"
        )
        logger.info(
            f"    Background Color →  {palette['background_color']}  (35% darker)"
        )
        logger.info(f"    Body Color       →  {palette['body_color']}  (always white)")
        logger.info(
            f"    Footer Color     →  {palette['footer_color']}  (always light)"
        )

        return palette

    except Exception as e:
        logger.error(f"Colour extraction failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# Image Processor — brand-specific sizes & limits
# ══════════════════════════════════════════════════════════════
class BrandImageProcessor:
    """
    Resize and compress brand images to meet portal requirements.

    Logo   : 512×512 px, max 2 MB
    Splash : 1080×1080 px, max 10 MB
    """

    LOGO_TARGET = (512, 512)
    LOGO_MAX_BYTES = 2 * 1024 * 1024  # 2 MB

    SPLASH_TARGET = (1080, 1080)
    SPLASH_MAX_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(self, output_folder="automation/processed_brand"):
        self.out = Path(output_folder)
        self.out.mkdir(parents=True, exist_ok=True)

    # ── helpers ──────────────────────────────────────────────
    def _has_transparency(self, img):
        """
        Return True if the image has a real alpha channel with
        any non-fully-opaque pixel.
        """
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode in ("RGBA", "LA"):
            alpha = img.split()[-1]
            return alpha.getextrema()[0] < 255  # at least one non-opaque pixel
        return False

    def _to_rgba(self, img):
        """Ensure image is in RGBA mode (preserves transparency)."""
        if img.mode == "P":
            return img.convert("RGBA")
        if img.mode == "LA":
            return img.convert("RGBA")
        if img.mode == "RGB":
            return img.convert("RGBA")
        return img  # already RGBA

    def _to_rgb(self, img):
        """Flatten to RGB with white background (only used for opaque images)."""
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            return bg
        if img.mode == "P":
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            return bg
        return img.convert("RGB") if img.mode != "RGB" else img

    def _fit_with_padding(self, img, target, transparent=False):
        """
        Scale to fit inside target (no crop, no stretch).
        transparent=True  → pad with transparent pixels (preserves alpha)
        transparent=False → pad with white pixels
        """
        ratio = min(target[0] / img.width, target[1] / img.height)
        if ratio > 1:
            ratio = 1.0
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        if transparent:
            canvas = Image.new("RGBA", target, (0, 0, 0, 0))  # fully transparent
            canvas.paste(img, ((target[0] - new_w) // 2, (target[1] - new_h) // 2))
        else:
            canvas = Image.new("RGB", target, (255, 255, 255))  # white
            canvas.paste(img, ((target[0] - new_w) // 2, (target[1] - new_h) // 2))
        return canvas

    def _save(
        self, img, out_path_no_ext, max_bytes, start_quality=95, transparent=False
    ):
        """
        Save image in the correct format:
          transparent=True  → PNG  (preserves alpha, lossless, tries size reduction)
          transparent=False → JPEG (lossy, quality descent until under max_bytes)

        Returns (actual_path, ok, quality_or_note).
        """
        if transparent:
            # Save as PNG — lossless, no quality setting
            out = Path(str(out_path_no_ext) + ".png")
            img.save(out, "PNG", optimize=True)
            size = out.stat().st_size
            if size <= max_bytes:
                return out, True, "PNG lossless"
            # PNG too large → try reducing to smaller canvas keeping transparency
            logger.warning(
                f"PNG size {size / 1024 / 1024:.2f} MB exceeds limit — "
                f"trying PNG with reduced resolution"
            )
            target = img.size
            for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
                w = int(target[0] * scale)
                h = int(target[1] * scale)
                small = img.resize((w, h), Image.Resampling.LANCZOS)
                small.save(out, "PNG", optimize=True)
                if out.stat().st_size <= max_bytes:
                    return out, True, f"PNG scaled {int(scale * 100)}%"
            return out, False, "PNG still too large"
        else:
            # Save as JPEG — descend quality
            out = Path(str(out_path_no_ext) + ".jpg")
            for q in range(start_quality, 9, -5):
                img.save(out, "JPEG", quality=q, optimize=True)
                if out.stat().st_size <= max_bytes:
                    return out, True, f"JPEG q{q}"
            return out, False, "JPEG quality exhausted"

    # ── public methods ────────────────────────────────────────
    def process_logo(self, input_path):
        """Process App Logo → 512×512, max 2 MB. Preserves transparency."""
        src = Path(input_path)
        if not src.exists():
            logger.error(f"Logo file not found: {input_path}")
            return None
        try:
            raw = Image.open(src)
            transparent = self._has_transparency(raw)

            if transparent:
                img = self._to_rgba(raw)
                img = self._fit_with_padding(img, self.LOGO_TARGET, transparent=True)
                logger.info("  Logo has transparency — preserving (saving as PNG)")
            else:
                img = self._to_rgb(raw)
                img = self._fit_with_padding(img, self.LOGO_TARGET, transparent=False)

            out, ok, note = self._save(
                img,
                self.out / "logo_processed",
                self.LOGO_MAX_BYTES,
                start_quality=95,
                transparent=transparent,
            )
            kb = out.stat().st_size / 1024
            if ok:
                logger.info(f"✓ Logo  → {out.name}  |  {kb:.1f} KB  |  {note}")
                return str(out)
            logger.error(
                f"Logo still exceeds 2 MB after processing ({kb:.0f} KB). "
                "Please provide a smaller source image."
            )
            return None
        except Exception as e:
            logger.error(f"Logo processing error: {e}")
            return None

    def process_splash(self, input_path):
        """Process Splash Screen → 1080×1080, max 10 MB. Preserves transparency."""
        src = Path(input_path)
        if not src.exists():
            logger.error(f"Splash file not found: {input_path}")
            return None
        try:
            raw = Image.open(src)
            transparent = self._has_transparency(raw)

            if transparent:
                img = self._to_rgba(raw)
                img = self._fit_with_padding(img, self.SPLASH_TARGET, transparent=True)
                logger.info("  Splash has transparency — preserving (saving as PNG)")
            else:
                img = self._to_rgb(raw)
                img = self._fit_with_padding(img, self.SPLASH_TARGET, transparent=False)

            out, ok, note = self._save(
                img,
                self.out / "splash_processed",
                self.SPLASH_MAX_BYTES,
                start_quality=90,
                transparent=transparent,
            )
            mb = out.stat().st_size / (1024 * 1024)
            if ok:
                logger.info(f"✓ Splash → {out.name}  |  {mb:.2f} MB  |  {note}")
                return str(out)
            logger.error(
                f"Splash still exceeds 10 MB after processing ({mb:.2f} MB). "
                "Please provide a smaller source image."
            )
            return None
        except Exception as e:
            logger.error(f"Splash processing error: {e}")
            return None


# ══════════════════════════════════════════════════════════════
# Brand Setting Automation  (receives an already-logged-in driver)
# ══════════════════════════════════════════════════════════════
class BrandSettingAutomation:
    """
    Fills the Identity & Branding form on the vendor portal.
    Expects an already-authenticated Selenium WebDriver instance.
    """

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    # ── internal helpers ──────────────────────────────────────
    def _ss(self, name):
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"brand_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def _set_color(self, field_name, hex_value):
        """
        Set a brand colour correctly in a React-controlled form.

        React ignores direct JS .value assignments on controlled inputs.
        The real state lives in the *hex text field* (type=text, maxlength=7)
        that sits next to each color picker.  We:
          1. Sync the color-picker visually via the React native setter.
          2. Find the sibling hex text input inside the same container.
          3. Triple-click to select all existing text, then type the new value
             using real keyboard events so React's onChange fires properly.
          4. Blur to commit.
        """
        from selenium.webdriver.common.keys import Keys

        try:
            # ── 1. Color picker (visual only) via React native setter ──
            color_el = self.driver.find_element(By.NAME, field_name)
            self.driver.execute_script(
                """
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                setter.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                """,
                color_el,
                hex_value,
            )

            # ── 2. Find the sibling hex text input in the same container ──
            # Structure: <div container> <input type=color> <input type=text maxlength=7> </div>
            hex_el = self.driver.execute_script(
                """
                var c   = arguments[0].parentElement;
                var all = c.querySelectorAll('input[type="text"]');
                return all.length ? all[0] : null;
                """,
                color_el,
            )

            if hex_el is None:
                logger.warning(f"    Hex text field not found for {field_name}")
                return

            # ── 3. Type into the hex text field (React registers this) ──
            hex_el.click()
            time.sleep(0.1)
            # Select-all + delete whatever is there, then type new value
            hex_el.send_keys(Keys.CONTROL + "a")
            hex_el.send_keys(Keys.DELETE)
            hex_el.send_keys(hex_value)  # e.g. "#405070"
            time.sleep(0.1)

            # ── 4. Blur to commit React state ──
            self.driver.execute_script("arguments[0].blur()", hex_el)
            time.sleep(0.2)

            logger.info(f"    → {field_name}: {hex_value}")

        except Exception as e:
            logger.warning(f"    Could not set {field_name}: {e}")

    # ── public methods ────────────────────────────────────────
    def navigate(self):
        """
        App Settings → Identity & Branding → Edit Branding.
        Returns True if the form popup is open, False otherwise.
        """
        try:
            logger.info("Going to App Settings...")
            self.driver.get(APP_SETTINGS)
            time.sleep(3)

            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(.,'Identity & Branding')]")
                )
            ).click()
            time.sleep(3)
            logger.info("  → Identity & Branding section opened")

            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Edit Branding')]")
                )
            ).click()
            time.sleep(2)
            logger.info("  → Edit Branding popup opened")

            # Confirm form is ready
            self.wait.until(EC.presence_of_element_located((By.NAME, "CompanyName")))
            logger.info("✓ Brand setting form is ready")
            return True

        except Exception as e:
            logger.error(f"Navigation to brand setting failed: {e}")
            self._ss("nav_error")
            return False

    def fill_and_save(self, company_name, logo_path, splash_path, colors=None):
        """
        Fill the brand form and click Save Changes.

        Parameters
        ----------
        company_name : str
        logo_path    : str  — path to processed logo (512×512, <2 MB)
        splash_path  : str  — path to processed splash (1080×1080, <10 MB)
        colors       : dict — optional keys: header_color, footer_color,
                              body_color, background_color  (hex strings e.g. "#FF0000")
                              Empty string or missing key = leave unchanged.
        """
        try:
            # ── Company Name ──────────────────────────────────
            logger.info(f"  Setting company name: {company_name}")
            field = self.driver.find_element(By.NAME, "CompanyName")
            field.clear()
            field.send_keys(company_name)

            # ── Colors (all optional) ─────────────────────────
            if colors:
                mapping = {
                    "header_color": "HeaderColor",
                    "footer_color": "FooterColor",
                    "body_color": "BodyColor",
                    "background_color": "BackgroundColor",
                }
                for cfg_key, field_name in mapping.items():
                    hex_val = (colors.get(cfg_key) or "").strip()
                    if hex_val:
                        self._set_color(field_name, hex_val)

            # ── File uploads ──────────────────────────────────
            # The portal has exactly 2 file inputs: [0]=logo, [1]=splash
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            if len(file_inputs) < 2:
                logger.error(f"Expected 2 file inputs, found {len(file_inputs)}")
                return False

            if logo_path and Path(logo_path).exists():
                file_inputs[0].send_keys(str(Path(logo_path).absolute()))
                time.sleep(2)
                logger.info(f"  ✓ Logo uploaded:   {Path(logo_path).name}")
            else:
                logger.warning(f"  ⚠ Logo not found: {logo_path}")

            if splash_path and Path(splash_path).exists():
                file_inputs[1].send_keys(str(Path(splash_path).absolute()))
                time.sleep(2)
                logger.info(f"  ✓ Splash uploaded: {Path(splash_path).name}")
            else:
                logger.warning(f"  ⚠ Splash not found: {splash_path}")

            # ── Save Changes ──────────────────────────────────
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Save Changes')]")
                )
            ).click()
            logger.info("  → Save Changes clicked, waiting for confirmation...")
            time.sleep(3)

            # Form closes → Edit Branding button reappears
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'Edit Branding')]")
                )
            )
            logger.info("✓ Brand settings saved successfully!")
            return True

        except Exception as e:
            logger.error(f"Brand form fill/save failed: {e}")
            self._ss("form_error")
            # Try Cancel so the popup doesn't block anything else
            try:
                self.driver.find_element(
                    By.XPATH, "//button[contains(text(),'Cancel')]"
                ).click()
                time.sleep(1)
            except Exception:
                pass
            return False
