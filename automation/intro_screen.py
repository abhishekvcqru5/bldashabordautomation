"""
Intro Screens Automation
Handles the "Intro Screens" section under App Settings.

For every image in the introscreen/ folder:
  1. Check / resize to 1080×1920 px  (portrait)
  2. Compress to max 10 MB
  3. Click "Add New Screen"
  4. Enter Marketing Header
  5. Enter Feature Description
  6. Upload processed image
  7. Click "Launch Screen"
  8. Repeat for all images

Default content (2 slides, cycles if more images):
  Slide 1 — "Earn Points, Unlock Rewards"
  Slide 2 — "Scan, Earn, Celebrate"

User can choose Default or Custom content at runtime.
Fully separate from all other automation features.
"""

import logging
import time
from datetime import datetime
from pathlib import Path

from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

logger = logging.getLogger(__name__)

from dashboard_automation import VendorPortalAutomation

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

def get_app_settings_url():
    return getattr(VendorPortalAutomation, "APP_SETTINGS", APP_SETTINGS)
INTRO_FOLDER = Path(__file__).resolve().parent.parent / "introscreen"
PROCESSED_DIR = Path(__file__).resolve().parent / "processed_introscreen"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}

# ── Default content (paired: header → description) ─────────────────────────
DEFAULT_SLIDES = [
    {
        "header": "Earn Points, Unlock Rewards",
        "description": (
            "Turn every purchase or scan into valuable points. "
            "Accumulate rewards over time and redeem them for exciting gifts, "
            "cashback, and exclusive benefits designed to keep you motivated "
            "and engaged."
        ),
    },
    {
        "header": "Scan, Earn, Celebrate",
        "description": (
            "With every QR scan, you step closer to amazing rewards. "
            "Enjoy a seamless experience where your actions are instantly "
            "rewarded with points that can be converted into gifts and "
            "special perks."
        ),
    },
]


# ══════════════════════════════════════════════════════════════
# Image Processor  —  intro screen requirements
# ══════════════════════════════════════════════════════════════
class IntroImageProcessor:
    """
    Resize and compress intro screen images:
        Target  : 1080 × 1920 px  (portrait / phone screen)
        Max size: 10 MB
    """

    TARGET = (1080, 1920)
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(self, output_folder=PROCESSED_DIR):
        self.out = Path(output_folder)
        self.out.mkdir(parents=True, exist_ok=True)

    # ── helpers ───────────────────────────────────────────────
    def _to_rgb(self, img):
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

    def _compress(self, img, out_path, max_bytes, start_quality=92):
        for q in range(start_quality, 9, -5):
            img.save(out_path, "JPEG", quality=q, optimize=True)
            if out_path.stat().st_size <= max_bytes:
                return True, q
        return False, 10

    # ── public ────────────────────────────────────────────────
    def needs_processing(self, src_path):
        try:
            p = Path(src_path)
            size = p.stat().st_size
            img = Image.open(p)
            dims = img.size
            size_ok = size <= self.MAX_BYTES
            dims_ok = dims == self.TARGET
            if size_ok and dims_ok:
                return (
                    True,
                    f"Already OK ({dims[0]}×{dims[1]}, {size / 1024 / 1024:.2f} MB)",
                )
            reasons = []
            if not dims_ok:
                reasons.append(
                    f"{dims[0]}×{dims[1]} → need {self.TARGET[0]}×{self.TARGET[1]}"
                )
            if not size_ok:
                reasons.append(f"{size / 1024 / 1024:.2f} MB > 10 MB limit")
            return False, "  |  ".join(reasons)
        except Exception as e:
            return False, f"Cannot read: {e}"

    def process(self, src_path):
        """
        Validate, resize and compress one intro image.
        Returns output path (str) on success or None on failure.
        """
        src = Path(src_path)
        if not src.exists():
            logger.error(f"  Intro image not found: {src_path}")
            return None

        ok, reason = self.needs_processing(src)
        out_name = src.stem + "_processed.jpg"
        out_path = self.out / out_name

        if ok:
            logger.info(f"  ✓ {src.name}  →  {reason}")
            try:
                img = self._to_rgb(Image.open(src))
                img.save(out_path, "JPEG", quality=92, optimize=True)
                return str(out_path)
            except Exception as e:
                logger.error(f"  Copy failed: {e}")
                return None

        logger.info(f"  ⚙ Processing {src.name}  ({reason})")
        try:
            img = self._to_rgb(Image.open(src))
            img = self._force_resize(img, self.TARGET)
            success, q = self._compress(img, out_path, self.MAX_BYTES)
            mb = out_path.stat().st_size / (1024 * 1024)
            if success:
                logger.info(
                    f"  ✓ {src.name}  →  {out_name}  "
                    f"|  {self.TARGET[0]}×{self.TARGET[1]}  "
                    f"|  {mb:.2f} MB  |  quality {q}"
                )
                return str(out_path)
            logger.error(
                f"  ✗ {src.name} still exceeds 10 MB ({mb:.2f} MB). "
                "Use a lighter source image."
            )
            return None
        except Exception as e:
            logger.error(f"  Processing error for {src.name}: {e}")
            return None

    def process_all(self, folder=INTRO_FOLDER):
        """
        Process every supported image in *folder* (sorted order).
        Returns list of processed output paths.
        """
        folder = Path(folder)
        if not folder.exists():
            logger.error(f"Intro screen folder not found: {folder}")
            return []

        files = sorted(f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXT)
        if not files:
            logger.warning(f"No images found in {folder}")
            return []

        logger.info(f"Found {len(files)} intro image(s) in {folder}/")
        results = []
        for f in files:
            out = self.process(f)
            if out:
                results.append(out)

        logger.info(
            f"  Processed {len(results)}/{len(files)} intro images successfully\n"
        )
        return results


# ══════════════════════════════════════════════════════════════
# Content builder  —  pairs each image with header + description
# ══════════════════════════════════════════════════════════════
def build_slides_default(image_paths):
    """
    Pair each processed image with default content (cycles if more
    images than default slides are defined).
    Returns list of dicts: {image_path, header, description}
    """
    slides = []
    n = len(DEFAULT_SLIDES)
    for i, img_path in enumerate(image_paths):
        content = DEFAULT_SLIDES[i % n]  # cycle through defaults
        slides.append(
            {
                "image_path": img_path,
                "header": content["header"],
                "description": content["description"],
            }
        )
    return slides


def build_slides_custom(image_paths):
    """
    Ask the user for header + description for each image interactively.
    Returns list of dicts: {image_path, header, description}
    """
    slides = []
    total = len(image_paths)
    print()
    print(f"  You have {total} intro screen image(s). Enter content for each:\n")

    for i, img_path in enumerate(image_paths, 1):
        img_name = Path(img_path).name
        print(f"  ── Slide {i}/{total}  ({img_name}) ────────────────────")

        header = input(f"  Marketing Header      : ").strip()
        if not header:
            print("  ⚠  Empty header — using default.")
            header = DEFAULT_SLIDES[(i - 1) % len(DEFAULT_SLIDES)]["header"]

        print(f"  Feature Description   : (press Enter twice to finish)")
        lines = []
        while True:
            line = input("    > ")
            if line == "" and lines:
                break
            lines.append(line)
        description = " ".join(lines).strip()
        if not description:
            print("  ⚠  Empty description — using default.")
            description = DEFAULT_SLIDES[(i - 1) % len(DEFAULT_SLIDES)]["description"]

        slides.append(
            {
                "image_path": img_path,
                "header": header,
                "description": description,
            }
        )
        print()

    return slides


# ══════════════════════════════════════════════════════════════
# Intro Screen Automation  (expects an already-logged-in driver)
# ══════════════════════════════════════════════════════════════
class IntroScreenAutomation:
    """
    Publishes intro screens on the vendor portal.
    Accepts an already-authenticated Selenium WebDriver.
    """

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    # ── helpers ───────────────────────────────────────────────
    def _ss(self, name):
        try:
            d = Path(__file__).resolve().parent / "screenshots"
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"intro_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def _dismiss_any_modal(self):
        """Dismiss any active popup/modal or backdrop if still visible."""
        try:
            cancels = self.driver.find_elements(
                By.XPATH, "//button[contains(text(),'Cancel') or contains(.,'Cancel')]"
            )
            for btn in cancels:
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(1)
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)

            close_buttons = self.driver.find_elements(
                By.XPATH, "//div[contains(@class,'fixed')]//button[*[local-name()='svg']]"
            )
            for btn in close_buttons:
                if btn.is_displayed():
                    try:
                        btn.click()
                        time.sleep(1)
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)

            WebDriverWait(self.driver, 4).until(
                EC.invisibility_of_element_located(
                    (By.XPATH, "//div[contains(@class,'backdrop-blur') or contains(@class,'bg-black/60')]")
                )
            )
        except Exception:
            pass

    # ── navigation ────────────────────────────────────────────
    def navigate(self):
        """
        App Settings → Intro Screens section.
        Returns True when "Add New Screen" button is visible and clickable.
        """
        try:
            logger.info("Going to App Settings...")
            self.driver.get(get_app_settings_url())
            time.sleep(3)

            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(.,'Intro Screens')]")
                )
            ).click()
            time.sleep(3)
            logger.info("  → Intro Screens section opened")

            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add New Screen')]")
                )
            )
            logger.info("✓ Intro Screens page ready")
            return True

        except Exception as e:
            logger.error(f"Navigation to Intro Screens failed: {e}")
            self._ss("nav_error")
            return False

    # ── launch one screen ─────────────────────────────────────
    def launch_screen(self, slide):
        """
        Open the popup, fill header + description + image, click Launch Screen.
        slide dict keys: image_path, header, description
        Returns True on success.
        """
        header = slide["header"]
        description = slide["description"]
        image_path = slide["image_path"]

        try:
            logger.info(f"  Launching screen: [{header[:50]}]")

            # 0. Clear any lingering modal/backdrop
            self._dismiss_any_modal()

            # 1. Open popup
            add_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add New Screen')]")
                )
            )
            try:
                add_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(2)

            # 2. Marketing Header
            header_field = None
            for xpath in [
                "//*[contains(text(),'Marketing Header')]/following::input[1]",
                "//input[@name='Header' or @name='header']",
                "//input[contains(@placeholder,'Welcome to the future')]",
                "//div[contains(@class,'fixed')]//input[not(@type='file') and not(@type='hidden')]",
            ]:
                try:
                    els = self.driver.find_elements(By.XPATH, xpath)
                    for el in els:
                        if el.is_displayed():
                            header_field = el
                            break
                    if header_field:
                        break
                except Exception:
                    continue

            if not header_field:
                header_field = self.wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//*[contains(text(),'Marketing Header')]/following::input[1] | //input[@name='Header' or @name='header']")
                    )
                )

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", header_field)
            header_field.clear()
            header_field.send_keys(header)
            try:
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                    header_field
                )
            except Exception:
                pass
            logger.info(f"    → Header: {header}")

            # 3. Feature Description (textarea)
            desc_field = None
            for xpath in [
                "//*[contains(text(),'Feature Description')]/following::textarea[1]",
                "//textarea[@name='Contents' or @name='contents' or @name='Description']",
                "//div[contains(@class,'fixed')]//textarea",
            ]:
                try:
                    els = self.driver.find_elements(By.XPATH, xpath)
                    for el in els:
                        if el.is_displayed():
                            desc_field = el
                            break
                    if desc_field:
                        break
                except Exception:
                    continue

            if not desc_field:
                desc_field = self.wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//*[contains(text(),'Feature Description')]/following::textarea[1] | //textarea")
                    )
                )

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", desc_field)
            desc_field.clear()
            desc_field.send_keys(description)
            try:
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                    desc_field
                )
            except Exception:
                pass
            logger.info(f"    → Description: {description[:60]}...")

            # 4. Upload image
            file_input = None
            for xpath in [
                "//*[contains(text(),'Introduction Banner')]/following::input[@type='file'][1]",
                "//*[contains(text(),'Click to upload media')]/ancestor::div[1]//input[@type='file']",
                "//*[contains(text(),'Click to upload media')]/following::input[@type='file'][1]",
                "//*[contains(text(),'Click to upload media')]/preceding::input[@type='file'][1]",
            ]:
                try:
                    els = self.driver.find_elements(By.XPATH, xpath)
                    if els:
                        file_input = els[0]
                        break
                except Exception:
                    continue

            if not file_input:
                all_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                if all_inputs:
                    file_input = all_inputs[-1]

            if not file_input:
                raise NoSuchElementException("Could not locate file input inside intro screen modal")

            try:
                self.driver.execute_script("""
                    arguments[0].style.cssText = 'display:block !important; visibility:visible !important;'
                        + 'opacity:1 !important; width:1px !important; height:1px !important;'
                        + 'position:fixed !important; top:0 !important; left:0 !important; z-index:99999;';
                """, file_input)
            except Exception:
                pass

            abs_path = str(Path(image_path).resolve())
            file_input.send_keys(abs_path)
            try:
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                    file_input
                )
            except Exception:
                pass
            time.sleep(2)
            logger.info(f"    → Image uploaded: {Path(image_path).name}")

            # 5. Launch Screen
            launch_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Launch Screen')]")
                )
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", launch_btn)
            try:
                launch_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", launch_btn)
            logger.info("    → Launch Screen clicked, waiting for completion...")

            # 6. Wait for popup to actually close
            modal_closed = False
            start_wait = time.time()
            while time.time() - start_wait < 25:
                err_nodes = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class,'fixed')]//*[contains(text(),'required') or contains(@class,'text-red')]"
                )
                visible_errs = [e.text.strip() for e in err_nodes if e.is_displayed() and e.text.strip()]
                if visible_errs and (time.time() - start_wait > 4):
                    logger.error(f"  ✗ Form validation error: {', '.join(visible_errs)}")
                    break

                btns = self.driver.find_elements(
                    By.XPATH, "//button[contains(text(),'Launch Screen')]"
                )
                visible_btns = [b for b in btns if b.is_displayed()]
                if not visible_btns:
                    modal_closed = True
                    break
                time.sleep(0.5)

            if not modal_closed:
                logger.error(f"  ✗ Modal did not close for screen [{header[:40]}]")
                self._ss(f"error_{header[:20].strip()}")
                self._dismiss_any_modal()
                return False

            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located(
                        (By.XPATH, "//div[contains(@class,'backdrop-blur') or contains(@class,'bg-black/60')]")
                    )
                )
            except Exception:
                pass

            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Add New Screen')]")
                )
            )
            time.sleep(1)
            logger.info(f"  ✓ Intro screen launched: {header}\n")
            return True

        except Exception as e:
            logger.error(f"  ✗ Failed to launch screen [{header[:40]}]: {e}")
            self._ss(f"error_slide")
            self._dismiss_any_modal()
            return False

    # ── batch ─────────────────────────────────────────────────
    def launch_all(self, slides):
        """
        Launch all intro screens in the list.
        slides: list of dicts from build_slides_default / build_slides_custom
        Returns (successful, failed) counts.
        """
        total = len(slides)
        successful = 0
        failed = 0

        logger.info(f"Starting batch  —  {total} intro screen(s) to launch")
        logger.info("=" * 60)

        for idx, slide in enumerate(slides, 1):
            logger.info(f"[{idx}/{total}]")
            self._dismiss_any_modal()
            if self.launch_screen(slide):
                successful += 1
            else:
                failed += 1
            time.sleep(2)

        logger.info("=" * 60)
        logger.info(
            f"Intro screens done  →  ✓ {successful} launched   ✗ {failed} failed"
        )
        return successful, failed
