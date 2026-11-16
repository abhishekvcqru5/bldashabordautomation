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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

from dashboard_automation import VendorPortalAutomation

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

def get_app_settings_url():
    return getattr(VendorPortalAutomation, "APP_SETTINGS", APP_SETTINGS)


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

    def _force_resize(self, img, target):
        """
        Force-resize to exact target dimensions — same as ImageMagick  -resize WxH!
        Stretches to fill the full frame with NO padding and NO white space.
        """
        return img.resize(target, Image.Resampling.LANCZOS)

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
        """Process App Logo → 512×512 on clean white background, max 2 MB."""
        src = Path(input_path)
        if not src.exists():
            logger.error(f"Logo file not found: {input_path}")
            return None
        try:
            raw = Image.open(src)
            if raw.mode != "RGBA":
                raw = raw.convert("RGBA")

            # Fit logo proportionally on a pure white 512×512 canvas
            canvas = Image.new("RGBA", self.LOGO_TARGET, (255, 255, 255, 255))
            max_w = int(self.LOGO_TARGET[0] * 0.92)
            max_h = int(self.LOGO_TARGET[1] * 0.92)
            w, h = raw.size
            ratio = min(max_w / w, max_h / h)
            new_w = max(1, int(w * ratio))
            new_h = max(1, int(h * ratio))

            resized_logo = raw.resize((new_w, new_h), Image.Resampling.LANCZOS)
            offset_x = (self.LOGO_TARGET[0] - new_w) // 2
            offset_y = (self.LOGO_TARGET[1] - new_h) // 2

            mask = resized_logo.split()[-1] if resized_logo.mode == "RGBA" else None
            canvas.paste(resized_logo, (offset_x, offset_y), mask=mask)

            out = self.out / "logo_processed.png"
            canvas.save(out, "PNG", optimize=True)

            # Also save JPG version
            out_jpg = self.out / "logo_processed.jpg"
            canvas.convert("RGB").save(out_jpg, "JPEG", quality=95, optimize=True)

            kb = out.stat().st_size / 1024
            logger.info(f"✓ Logo  → {out.name}  |  512×512 (white background)  |  {kb:.1f} KB")
            return str(out)
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
                img = self._force_resize(img, self.SPLASH_TARGET)
                logger.info("  Splash has transparency — preserving (saving as PNG)")
            else:
                img = self._to_rgb(raw)
                img = self._force_resize(img, self.SPLASH_TARGET)

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
            self.driver.get(get_app_settings_url())
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
            field.click()
            field.send_keys(Keys.CONTROL + "a")
            field.send_keys(Keys.DELETE)
            field.send_keys(company_name)
            self.driver.execute_script("""
                var el = arguments[0];
                var val = arguments[1];
                try {
                    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(el, val);
                } catch (e) {}
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            """, field, company_name)

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
            comp_input = self.driver.find_element(By.NAME, "CompanyName")
            modal = self.driver.execute_script("""
                var el = arguments[0];
                var p = el.parentElement;
                while (p && p !== document.body) {
                    var txt = p.innerText || "";
                    if (txt.includes('Customize Branding') || txt.includes('App Logo') || txt.includes('Save Changes')) {
                        if (txt.includes('Save Changes') || txt.includes('Cancel')) {
                            return p;
                        }
                    }
                    p = p.parentElement;
                }
                return el.closest('form') || el.closest('div[role="dialog"]') || document.body;
            """, comp_input)

            # Look for file inputs inside this real modal
            inputs = self.driver.execute_script("""
                var modal = arguments[0];
                var allInps = modal.querySelectorAll('input[type="file"]');
                var logoInp = null;
                var splashInp = null;

                // Find by label / text container
                var allDivs = modal.querySelectorAll('div');
                for (var i = 0; i < allDivs.length; i++) {
                    var d = allDivs[i];
                    var txt = (d.innerText || "").trim();
                    if (!logoInp && (txt.startsWith('App Logo') || (txt.includes('App Logo') && txt.length < 200))) {
                        var fi = d.querySelector('input[type="file"]');
                        if (fi) logoInp = fi;
                    }
                    if (!splashInp && (txt.startsWith('Splash Screen') || (txt.includes('Splash Screen') && txt.length < 200))) {
                        var fi = d.querySelector('input[type="file"]');
                        if (fi) splashInp = fi;
                    }
                }

                if (!logoInp && allInps.length > 0) logoInp = allInps[0];
                if (!splashInp && allInps.length > 1) splashInp = allInps[1];

                return [logoInp, splashInp];
            """, modal)

            logo_input = inputs[0] if inputs and len(inputs) > 0 else None
            splash_input = inputs[1] if inputs and len(inputs) > 1 else None

            if not logo_input:
                logger.error("  ✗ Could not find App Logo file input inside Customize Branding modal")
                self._ss("missing_logo_input")
                return False

            # Upload Logo (512×512)
            if logo_path and Path(logo_path).exists():
                abs_logo = str(Path(logo_path).resolve())
                self.driver.execute_script("""
                    var el = arguments[0];
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.width = '1px';
                    el.style.height = '1px';
                    el.style.position = 'absolute';
                """, logo_input)
                time.sleep(0.2)
                logo_input.send_keys(abs_logo)
                time.sleep(1)
                self.driver.execute_script("""
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, logo_input)
                time.sleep(1.5)

                logo_state = self.driver.execute_script("""
                    var inp = arguments[0];
                    var container = inp.closest('div[role="presentation"]') || inp.parentElement;
                    var img = container ? container.querySelector('img') : null;
                    return {
                        hasFiles: Boolean(inp.files && inp.files.length > 0),
                        hasPreview: Boolean(img)
                    };
                """, logo_input)
                logger.info(f"  ✓ Logo upload state: {logo_state}")

                if not logo_state.get("hasPreview"):
                    logger.info("    → Triggering dropzone DataTransfer fallback for App Logo...")
                    import base64
                    with open(abs_logo, "rb") as f:
                        b64_content = base64.b64encode(f.read()).decode("utf-8")
                    ext = Path(abs_logo).suffix.lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    self.driver.execute_script("""
                        var inp = arguments[0];
                        var b64 = arguments[1];
                        var name = arguments[2];
                        var mime = arguments[3];

                        var dropzone = inp.closest('div[role="presentation"]') || inp.parentElement;
                        if (!dropzone) return;

                        var bin = atob(b64);
                        var arr = new Uint8Array(bin.length);
                        for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
                        var file = new File([arr], name, { type: mime, lastModified: Date.now() });

                        var dt = new DataTransfer();
                        dt.items.add(file);

                        inp.files = dt.files;
                        inp.dispatchEvent(new Event('change', { bubbles: true }));

                        dropzone.dispatchEvent(new DragEvent('dragenter', { bubbles: true, dataTransfer: dt }));
                        dropzone.dispatchEvent(new DragEvent('dragover', { bubbles: true, dataTransfer: dt }));
                        dropzone.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
                    """, logo_input, b64_content, Path(abs_logo).name, mime)
                    time.sleep(2)
            else:
                logger.warning(f"  ⚠ Logo not found: {logo_path}")

            # Upload Splash (1080×1080)
            if splash_input and splash_path and Path(splash_path).exists():
                abs_splash = str(Path(splash_path).resolve())
                self.driver.execute_script("""
                    var el = arguments[0];
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.width = '1px';
                    el.style.height = '1px';
                    el.style.position = 'absolute';
                """, splash_input)
                time.sleep(0.2)
                splash_input.send_keys(abs_splash)
                time.sleep(1)
                self.driver.execute_script("""
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, splash_input)
                time.sleep(1.5)

                splash_state = self.driver.execute_script("""
                    var inp = arguments[0];
                    var container = inp.closest('div[role="presentation"]') || inp.parentElement;
                    var img = container ? container.querySelector('img') : null;
                    return {
                        hasFiles: Boolean(inp.files && inp.files.length > 0),
                        hasPreview: Boolean(img)
                    };
                """, splash_input)
                logger.info(f"  ✓ Splash upload state: {splash_state}")

                if not splash_state.get("hasPreview"):
                    logger.info("    → Triggering dropzone DataTransfer fallback for Splash Screen...")
                    import base64
                    with open(abs_splash, "rb") as f:
                        b64_content = base64.b64encode(f.read()).decode("utf-8")
                    ext = Path(abs_splash).suffix.lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    self.driver.execute_script("""
                        var inp = arguments[0];
                        var b64 = arguments[1];
                        var name = arguments[2];
                        var mime = arguments[3];

                        var dropzone = inp.closest('div[role="presentation"]') || inp.parentElement;
                        if (!dropzone) return;

                        var bin = atob(b64);
                        var arr = new Uint8Array(bin.length);
                        for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
                        var file = new File([arr], name, { type: mime, lastModified: Date.now() });

                        var dt = new DataTransfer();
                        dt.items.add(file);

                        inp.files = dt.files;
                        inp.dispatchEvent(new Event('change', { bubbles: true }));

                        dropzone.dispatchEvent(new DragEvent('dragenter', { bubbles: true, dataTransfer: dt }));
                        dropzone.dispatchEvent(new DragEvent('dragover', { bubbles: true, dataTransfer: dt }));
                        dropzone.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
                    """, splash_input, b64_content, Path(abs_splash).name, mime)
                    time.sleep(2)
            else:
                logger.warning(f"  ⚠ Splash not found or splash input missing")

            time.sleep(1)

            # ── Check form validation notices inside modal ────
            try:
                form_errors = self.driver.execute_script("""
                    var m = arguments[0];
                    var errs = [];
                    var els = m.querySelectorAll('[class*="text-red"], [class*="error"], [class*="invalid"]');
                    for (var i = 0; i < els.length; i++) {
                        if (els[i].offsetParent !== null) {
                            var t = (els[i].innerText || els[i].textContent || "").trim();
                            if (t && t !== "Click to upload media" && !errs.includes(t)) {
                                errs.push(t);
                            }
                        }
                    }
                    return errs;
                """, modal)
                if form_errors:
                    logger.warning(f"  ⚠ Form validation notice: {form_errors}")
            except Exception:
                pass

            # ── Save Changes ──────────────────────────────────
            save_btn = None
            save_xpaths = [
                "/html/body/div[2]/div[2]/div[3]/button[2]",
                "//body/div[2]/div[2]/div[3]/button[2]",
                "//div[contains(@class,'p-5') and contains(@class,'border-t')]//button[contains(.,'Save Changes') or contains(@class,'bg-indigo-600')]",
                "//button[normalize-space(.)='Save Changes']",
                "//button[contains(.,'Save Changes')]",
                "//button[@type='submit']",
            ]
            for xp in save_xpaths:
                try:
                    cand = self.driver.find_element(By.XPATH, xp)
                    if cand and cand.is_displayed():
                        save_btn = cand
                        break
                except Exception:
                    continue

            if not save_btn:
                try:
                    save_btn = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "div.p-5.border-t button.bg-indigo-600, button[type='submit']")
                        )
                    )
                except Exception:
                    pass

            if not save_btn:
                logger.error("  ✗ Could not find Save/Submit button on brand form")
                self._ss("save_btn_not_found")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
            time.sleep(0.5)

            # Click via native + JavaScript
            try:
                save_btn.click()
                logger.info("  → Save Changes clicked (native)")
            except Exception as click_err:
                logger.warning(f"  ⚠ Native click failed: {click_err}")

            self.driver.execute_script("""
                var btn = arguments[0];
                try { btn.click(); } catch (e) {}
                if (btn.form) {
                    try { btn.form.requestSubmit(btn); } catch (e2) {}
                }
            """, save_btn)
            logger.info("  → Save Changes clicked, waiting for modal to close...")

            # Wait for modal to close
            modal_closed = False
            for i in range(25):
                time.sleep(1)
                is_visible = self.driver.execute_script("""
                    var el = document.querySelector('input[name="CompanyName"]');
                    return el ? (el.offsetParent !== null) : false;
                """)
                if not is_visible:
                    modal_closed = True
                    logger.info(f"  ✓ Brand modal closed after {i+1}s")
                    break

                if i in (3, 7, 12, 18):
                    logger.info(f"  → Retrying submit click at {i+1}s...")
                    self.driver.execute_script("""
                        var btn = arguments[0];
                        try { btn.click(); } catch (e) {}
                        if (btn.form) {
                            try { btn.form.requestSubmit(btn); } catch (e2) {}
                        }
                    """, save_btn)

            if not modal_closed:
                logger.warning("  ⚠ Modal did not close automatically; capturing screenshot & HTML snippet")
                self._ss("modal_not_closed")
                modal_snippet = self.driver.execute_script("""
                    var comp = document.querySelector('input[name="CompanyName"]');
                    var m = comp ? (comp.closest('div.fixed') || comp.parentElement.parentElement.parentElement) : null;
                    return m ? m.outerHTML.substring(0, 1500) : "No modal container found";
                """)
                logger.warning(f"  Modal HTML snippet: {modal_snippet}")

            time.sleep(2)
            logger.info("✓ Brand settings process finished!")
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


# ══════════════════════════════════════════════════════════════
# Support Network Automation  (receives an already-logged-in driver)
# ══════════════════════════════════════════════════════════════
class SupportNetworkAutomation:
    """
    Fills the Support Network form on the vendor portal.
    Expects an already-authenticated Selenium WebDriver instance.

    Fields handled:
      - Phone number
      - Email
      - Website
      - Terms & Conditions
      - Support / Help content
      - Privacy Policy
    """

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    # ── internal helpers ──────────────────────────────────────
    def _ss(self, name):
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"support_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def _fill_field(self, name_or_xpath, value, by=By.NAME):
        """Clear and fill a text field identified by name or xpath."""
        if not value:
            return
        try:
            el = self.driver.find_element(by, name_or_xpath)
            el.clear()
            el.send_keys(value)
            logger.info(f"    → Filled: {name_or_xpath}")
        except Exception as e:
            logger.warning(f"    Could not fill {name_or_xpath}: {e}")

    # ── public methods ────────────────────────────────────────
    def navigate(self):
        """
        App Settings → Support Network → Edit Support Network.
        Returns True if the form popup is open, False otherwise.
        """
        try:
            logger.info("Going to App Settings for Support Network...")
            self.driver.get(APP_SETTINGS)
            time.sleep(3)

            # Click the "Support Network" section header
            # Try multiple strategies for robustness
            support_clicked = False

            # Strategy 1: h3 heading text
            for xp in (
                "//h3[contains(normalize-space(.),'Support Network')]",
                "//button[contains(normalize-space(.),'Support Network')]",
                "//*[contains(normalize-space(.),'Support Network') and (self::h3 or self::button or self::div)]",
            ):
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();",
                                el
                            )
                            support_clicked = True
                            logger.info("  → Support Network section opened")
                            break
                except Exception:
                    continue
                if support_clicked:
                    break

            if not support_clicked:
                logger.error("  ✗ Could not find Support Network section")
                self._ss("support_nav_fail")
                return False

            time.sleep(3)

            # Click "Edit Support Network" or similar edit button
            edit_clicked = False
            for xp in (
                "//button[contains(normalize-space(.),'Edit Support')]",
                "//button[contains(normalize-space(.),'Edit')]",
                "//a[contains(normalize-space(.),'Edit Support')]",
            ):
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();",
                                el
                            )
                            edit_clicked = True
                            logger.info("  → Edit Support Network popup opened")
                            break
                except Exception:
                    continue
                if edit_clicked:
                    break

            if not edit_clicked:
                logger.warning("  ⚠ Could not find Edit button — form may already be open")

            time.sleep(2)
            logger.info("✓ Support Network form is ready")
            return True

        except Exception as e:
            logger.error(f"Navigation to Support Network failed: {e}")
            self._ss("support_nav_error")
            return False

    def fill_and_save(self, data: dict):
        """
        Fill the Support Network form and click Save.

        Parameters
        ----------
        data : dict with keys:
            phone, email, website, terms_conditions,
            support_content, privacy_policy
        """
        try:
            # Map data keys to possible form field names/xpaths
            field_map = {
                "phone": [
                    (By.ID, "ContactNumber"),
                    (By.NAME, "Phone"),
                    (By.NAME, "phone"),
                    (By.NAME, "ContactPhone"),
                    (By.XPATH, "//input[@placeholder='Phone' or @placeholder='Phone Number' or contains(@name,'phone') or contains(@name,'Phone')]"),
                ],
                "email": [
                    (By.ID, "ContactEmail"),
                    (By.NAME, "Email"),
                    (By.NAME, "email"),
                    (By.NAME, "ContactEmail"),
                    (By.XPATH, "//input[@placeholder='Email' or contains(@name,'email') or contains(@name,'Email')]"),
                ],
                "website": [
                    (By.ID, "AboutUsLink"),
                    (By.NAME, "Website"),
                    (By.NAME, "website"),
                    (By.NAME, "WebsiteUrl"),
                    (By.XPATH, "//input[@placeholder='Website' or contains(@name,'website') or contains(@name,'Website')]"),
                ],
                "terms_conditions": [
                    (By.ID, "TermsConditionLink"),
                    (By.NAME, "TermsConditions"),
                    (By.NAME, "termsConditions"),
                    (By.NAME, "Terms"),
                    (By.XPATH, "//textarea[contains(@name,'erms') or contains(@placeholder,'erms')]"),
                    (By.XPATH, "//input[contains(@name,'erms') or contains(@placeholder,'erms')]"),
                ],
                "support_content": [
                    (By.ID, "ContactContents"),
                    (By.NAME, "SupportContent"),
                    (By.NAME, "supportContent"),
                    (By.NAME, "HelpContent"),
                    (By.XPATH, "//textarea[contains(@name,'upport') or contains(@name,'elp') or contains(@placeholder,'upport')]"),
                    (By.XPATH, "//input[contains(@name,'upport') or contains(@name,'elp')]"),
                ],
                "privacy_policy": [
                    (By.ID, "PrivacyPolicyLink"),
                    (By.NAME, "PrivacyPolicy"),
                    (By.NAME, "privacyPolicy"),
                    (By.XPATH, "//textarea[contains(@name,'rivacy') or contains(@placeholder,'rivacy')]"),
                    (By.XPATH, "//input[contains(@name,'rivacy') or contains(@placeholder,'rivacy')]"),
                ],
            }

            for key, selectors in field_map.items():
                value = data.get(key, "")
                if not value:
                    logger.info(f"    ⏭ Skipping empty field: {key}")
                    continue

                filled = False
                for by, sel in selectors:
                    try:
                        el = self.driver.find_element(by, sel)
                        if el.is_displayed():
                            el.clear()
                            el.send_keys(value)
                            logger.info(f"    ✓ {key} filled")
                            filled = True
                            break
                    except Exception:
                        continue

                if not filled:
                    logger.warning(f"    ⚠ Could not find field for: {key}")

            # ── Save Changes ──────────────────────────────────
            time.sleep(1)
            save_clicked = False
            for xp in (
                "//button[contains(normalize-space(.),'Save Changes')]",
                "//button[contains(normalize-space(.),'Save')]",
                "//button[@type='submit']",
            ):
                try:
                    els = self.driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();",
                                el
                            )
                            save_clicked = True
                            logger.info("  → Save clicked")
                            break
                except Exception:
                    continue
                if save_clicked:
                    break

            if not save_clicked:
                logger.error("  ✗ Could not find Save button")
                self._ss("support_save_fail")
                return False

            time.sleep(3)
            logger.info("✓ Support Network saved successfully!")
            return True

        except Exception as e:
            logger.error(f"Support Network fill/save failed: {e}")
            self._ss("support_form_error")
            try:
                self.driver.find_element(
                    By.XPATH, "//button[contains(text(),'Cancel')]"
                ).click()
                time.sleep(1)
            except Exception:
                pass
            return False
