"""
Promotion Banners Automation
Handles the "Promotion Banners" section under App Settings.

For every image found in the banner/ folder:
  1. Check / resize to 1920×1080 px
  2. Compress to max 5 MB
  3. Click "Deploy New Banner"
  4. Enter title  (derived from filename, e.g. vcqrubanne01 → "vcqrubanne01")
  5. Upload processed image
  6. Click "Publish Banner"
  7. Repeat until all images are published

Kept fully separate from dashboard icons and brand setting code.
"""

import logging
import time
from datetime import datetime
from pathlib import Path

from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"
BANNER_FOLDER = Path("banner")
PROCESSED_DIR = Path("automation/processed_banners")

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}


# ══════════════════════════════════════════════════════════════
# Image Processor  —  banner-specific requirements
# ══════════════════════════════════════════════════════════════
class BannerImageProcessor:
    """
    Resize and compress banner images:
        Target  : 1920 × 1080 px  (landscape)
        Max size: 5 MB
    """

    TARGET = (1920, 1080)
    MAX_BYTES = 5 * 1024 * 1024  # 5 MB

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
        Force-resize to exact target dimensions — same as ImageMagick  -resize 1920x1080!
        Stretches to fill the full frame with NO padding and NO white space.
        """
        return img.resize(target, Image.Resampling.LANCZOS)

    def _compress(self, img, out_path, max_bytes, start_quality=92):
        """Drop JPEG quality until file is under max_bytes."""
        for q in range(start_quality, 9, -5):
            img.save(out_path, "JPEG", quality=q, optimize=True)
            if out_path.stat().st_size <= max_bytes:
                return True, q
        return False, 10

    # ── public ────────────────────────────────────────────────
    def needs_processing(self, src_path):
        """
        Return (ok, reason) where ok=True means the file already
        meets requirements (size AND dimensions).
        """
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
                    f"Already OK  ({dims[0]}×{dims[1]}, {size / 1024 / 1024:.2f} MB)",
                )
            reasons = []
            if not dims_ok:
                reasons.append(
                    f"size {dims[0]}×{dims[1]} → need {self.TARGET[0]}×{self.TARGET[1]}"
                )
            if not size_ok:
                reasons.append(f"{size / 1024 / 1024:.2f} MB > 5 MB limit")
            return False, "  |  ".join(reasons)
        except Exception as e:
            return False, f"Cannot read: {e}"

    def process(self, src_path):
        """
        Validate, resize, and compress one banner image.
        Returns the output path (str) on success, or None on failure.
        """
        src = Path(src_path)
        if not src.exists():
            logger.error(f"  Banner image not found: {src_path}")
            return None

        ok, reason = self.needs_processing(src)
        out_name = src.stem + "_processed.jpg"
        out_path = self.out / out_name

        if ok:
            # Already meets requirements — still copy to processed folder as JPEG
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
            img = self._force_resize(
                img, self.TARGET
            )  # force exact 1920×1080, no padding

            success, q = self._compress(img, out_path, self.MAX_BYTES)
            mb = out_path.stat().st_size / (1024 * 1024)

            if success:
                logger.info(
                    f"  ✓ {src.name}  →  {out_name}  "
                    f"|  {self.TARGET[0]}×{self.TARGET[1]}  "
                    f"|  {mb:.2f} MB  |  quality {q}"
                )
                return str(out_path)
            else:
                logger.error(
                    f"  ✗ {src.name} still exceeds 5 MB after max compression "
                    f"({mb:.2f} MB). Use a lighter source image."
                )
                return None

        except Exception as e:
            logger.error(f"  Processing error for {src.name}: {e}")
            return None

    def process_all(self, folder=BANNER_FOLDER):
        """
        Process every supported image in *folder*.
        Returns list of (title, processed_path) tuples in sorted order.
        """
        folder = Path(folder)
        if not folder.exists():
            logger.error(f"Banner folder not found: {folder}")
            return []

        files = sorted(f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXT)

        if not files:
            logger.warning(f"No images found in {folder}")
            return []

        logger.info(f"Found {len(files)} banner image(s) in {folder}/")
        results = []
        for f in files:
            out = self.process(f)
            if out:
                # Title = filename stem (e.g. vcqrubanne01)
                title = f.stem
                results.append((title, out))

        logger.info(f"\n  Processed {len(results)}/{len(files)} banners successfully\n")
        return results


# ══════════════════════════════════════════════════════════════
# Banner Automation  (expects an already-logged-in driver)
# ══════════════════════════════════════════════════════════════
class BannerAutomation:
    """
    Publishes promotion banners on the vendor portal.
    Accepts an already-authenticated Selenium WebDriver.
    """

    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    # ── helpers ───────────────────────────────────────────────
    def _ss(self, name):
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"banner_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    # ── navigation ────────────────────────────────────────────
    def navigate(self):
        """
        App Settings → Promotion Banners section.
        Returns True when "Deploy New Banner" button is visible.
        """
        try:
            logger.info("Going to App Settings...")
            self.driver.get(APP_SETTINGS)
            time.sleep(3)

            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(.,'Promotion Banners')]")
                )
            ).click()
            time.sleep(3)
            logger.info("  → Promotion Banners section opened")

            # Confirm the Deploy button is present
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'Deploy New Banner')]")
                )
            )
            logger.info("✓ Promotion Banners page ready")
            return True

        except Exception as e:
            logger.error(f"Navigation to Promotion Banners failed: {e}")
            self._ss("nav_error")
            return False

    # ── publish one banner ────────────────────────────────────
    def publish_banner(self, title, image_path):
        """
        Click Deploy New Banner, fill form, upload image, click Publish.
        Returns True on success.
        """
        try:
            logger.info(f"  Publishing: [{title}]  ({Path(image_path).name})")

            # 1. Open popup
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Deploy New Banner')]")
                )
            ).click()
            time.sleep(2)

            # 2. Banner Title
            title_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "Title"))
            )
            title_field.clear()
            title_field.send_keys(title)
            logger.info(f"    → Title entered: {title}")

            # 3. Upload image
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(str(Path(image_path).absolute()))
            time.sleep(2)
            logger.info(f"    → Image uploaded: {Path(image_path).name}")

            # 4. Publish Banner
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Publish Banner')]")
                )
            ).click()
            logger.info("    → Publish Banner clicked")
            time.sleep(3)

            # 5. Wait for popup to close (Deploy New Banner button reappears)
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(text(),'Deploy New Banner')]")
                )
            )
            time.sleep(1)
            logger.info(f"  ✓ Banner published: {title}\n")
            return True

        except Exception as e:
            logger.error(f"  ✗ Failed to publish [{title}]: {e}")
            self._ss(f"error_{title}")
            # Try cancel so popup doesn't block the next one
            try:
                self.driver.find_element(
                    By.XPATH, "//button[contains(text(),'Cancel')]"
                ).click()
                time.sleep(1)
            except Exception:
                pass
            return False

    # ── batch ─────────────────────────────────────────────────
    def publish_all(self, banners):
        """
        Publish all banners in the list.
        banners : list of (title, processed_image_path)
        Returns (successful, failed) counts.
        """
        total = len(banners)
        successful = 0
        failed = 0

        logger.info(f"Starting batch  —  {total} banner(s) to publish")
        logger.info("=" * 60)

        for idx, (title, img_path) in enumerate(banners, 1):
            logger.info(f"[{idx}/{total}]")
            if self.publish_banner(title, img_path):
                successful += 1
            else:
                failed += 1
            time.sleep(1)

        logger.info("=" * 60)
        logger.info(f"Banners done  →  ✓ {successful} published   ✗ {failed} failed")
        return successful, failed
