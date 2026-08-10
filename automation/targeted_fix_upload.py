"""
Targeted Fix Uploader — upload images to specific dashboard product IDs
=========================================================================
Bypasses folder-name matching entirely; finds the row containing the given
dashboard ID text and opens its Edit Profile modal directly.
"""
import logging
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from dashboard_automation import VendorPortalAutomation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AMBICA_PATH = Path(
    r"c:\Users\admin\Desktop\newbldashboardproject\bldashabordautomation\ambica cables"
)

MODAL_XPATH      = "//div[contains(@class,'fixed') and contains(@class,'inset-0')]"
REMOVE_IMG_XPATH = MODAL_XPATH + "//div[.//img]//*[local-name()='svg' and contains(@class,'lucide-x')]"
SAVE_BTN_XPATH   = (MODAL_XPATH + "//button[contains(text(),'Save Changes')"
                    " or contains(text(),'Save')"
                    " or .//span[contains(text(),'Save')]]")
FILE_INPUT_XPATH = MODAL_XPATH + "//input[@type='file']"

EMAIL    = "ambicacableco1985@gmail.com"
PASSWORD = "Ambica123@"

# ── Targets: {dashboard_product_id: folder_name_in_ambica_cables} ───────────
# These are the products still showing broken/blank images on the dashboard.
# Add any additional IDs you spot that still show blank images.
TARGETS = {
    175: "14_40  x 2 core white parallel wire 90 mtr, 25 coil bag packing",
    173: "23_76 twisted flexible wire 90 mtr, 20 coils bag packing",
    172: "14_76 twisted flexible wire 90 mtr, 25 coils bag packing",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_file_inputs_visible(driver):
    try:
        driver.execute_script("""
            var modal = document.querySelector('.fixed.inset-0');
            var inputs = modal
                ? modal.querySelectorAll('input[type="file"]')
                : document.querySelectorAll('input[type="file"]');
            for (var i = 0; i < inputs.length; i++) {
                inputs[i].style.cssText =
                    'display:block !important; visibility:visible !important;'
                    + 'opacity:1 !important; width:1px !important; height:1px !important;'
                    + 'position:fixed !important; top:0 !important; left:0 !important; z-index:99999;';
            }
        """)
        time.sleep(0.4)
    except Exception:
        pass


def count_thumbnails(driver) -> int:
    try:
        return len(driver.find_elements(By.XPATH, REMOVE_IMG_XPATH))
    except Exception:
        return 0


def wait_for_thumbnail(driver, expected_count: int, timeout: int = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if count_thumbnails(driver) >= expected_count:
            return True
        time.sleep(0.4)
    return False


def remove_existing_images(driver):
    while True:
        try:
            svgs = driver.find_elements(By.XPATH, REMOVE_IMG_XPATH)
            if not svgs:
                break
            logger.info(f"  Removing an existing image (remaining: {len(svgs)})")
            driver.execute_script("arguments[0].click();", svgs[0])
            time.sleep(1.5)
        except Exception:
            break


def upload_images(driver, image_paths: list) -> bool:
    for path in image_paths:
        make_file_inputs_visible(driver)
        file_inputs = driver.find_elements(By.XPATH, FILE_INPUT_XPATH)
        if not file_inputs:
            logger.warning("  No file input found in modal")
            return False
        current = count_thumbnails(driver)
        try:
            file_inputs[0].send_keys(str(path))
            logger.info(f"  Sent: {Path(path).name}")
        except Exception as e:
            logger.warning(f"  send_keys failed: {e}")
            return False
        if wait_for_thumbnail(driver, current + 1):
            logger.info(f"    ✓ Upload confirmed (thumbnail rendered)")
        else:
            logger.warning(f"    ⚠ Thumbnail did not render within 15s")

    final = count_thumbnails(driver)
    if final == len(image_paths):
        logger.info(f"  ✓ Sanity check passed: all {final} thumbnails rendered")
        return True
    else:
        logger.warning(f"  ⚠ Sanity check: expected {len(image_paths)}, got {final}")
        return final > 0


def open_edit_modal_by_id(driver, wait, product_id: int) -> bool:
    """Find the table row containing 'ID: <product_id>' and open its Edit Profile modal."""
    id_text = f"ID: {product_id}"
    row_xpath = f"//table//tr[.//*[contains(text(),'{id_text}')]]"
    try:
        row = wait.until(EC.presence_of_element_located((By.XPATH, row_xpath)))
        logger.info(f"  Found row for {id_text}")
    except TimeoutException:
        logger.error(f"  Row with '{id_text}' not found in table")
        return False

    # Scroll into view
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", row)
    time.sleep(0.5)

    # Click the actions button in the row (last button)
    try:
        btns = row.find_elements(By.TAG_NAME, "button")
        if not btns:
            logger.error(f"  No buttons in row for {id_text}")
            return False
        action_btn = btns[-1]
        driver.execute_script("arguments[0].click();", action_btn)
        time.sleep(1.5)
    except Exception as e:
        logger.error(f"  Could not click action button: {e}")
        return False

    # Click Edit Profile from dropdown
    try:
        edit_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[text()='Edit Profile' or contains(text(),'Edit Profile')]")
        ))
        driver.execute_script("arguments[0].click();", edit_btn)
        time.sleep(1.5)
    except TimeoutException:
        logger.warning("  'Edit Profile' not found in dropdown, trying direct modal open")

    # Wait for modal
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, MODAL_XPATH)))
        time.sleep(1.5)
        logger.info(f"  Modal opened for {id_text}")
        return True
    except TimeoutException:
        logger.error(f"  Modal did not open for {id_text}")
        return False


def process_target(driver, wait, product_id: int, folder_name: str) -> bool:
    logger.info(f"\n{'─'*60}")
    logger.info(f"Target: ID={product_id} | Folder: {folder_name}")

    folder_path = AMBICA_PATH / folder_name
    if not folder_path.exists():
        logger.error(f"  Folder not found: {folder_path}")
        return False

    image_paths = sorted([
        str(p) for p in folder_path.iterdir()
        if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    ])
    if not image_paths:
        logger.error(f"  No images in: {folder_path}")
        return False

    logger.info(f"  Images: {len(image_paths)}")

    if not open_edit_modal_by_id(driver, wait, product_id):
        return False

    remove_existing_images(driver)

    if not upload_images(driver, image_paths):
        logger.error(f"  Upload failed for ID: {product_id}")
        return False

    # Save
    try:
        save_btn = wait.until(EC.element_to_be_clickable((By.XPATH, SAVE_BTN_XPATH)))
        driver.execute_script("arguments[0].click();", save_btn)
        logger.info(f"  Clicked Save Changes")
        time.sleep(2)
        logger.info(f"  ✓ Done: ID {product_id}")
        return True
    except Exception as e:
        logger.error(f"  Could not save: {e}")
        return False


def navigate_to_product_mgmt(automation, wait):
    driver = automation.driver
    try:
        driver.get(automation.APP_SETTINGS)
        time.sleep(3)
        btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "div.grid.grid-cols-1 > button:nth-child(6) > h3")
        ))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(3)
        logger.info("Clicked Product Management")
        return True
    except Exception as e:
        logger.error(f"Navigate to Product Management failed: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("TARGETED FIX UPLOADER — Ambica Cables")
    logger.info(f"Fixing {len(TARGETS)} products")
    logger.info("=" * 60)

    succeeded = []
    failed = []

    with VendorPortalAutomation(EMAIL, PASSWORD, headless=False) as automation:
        driver = automation.driver
        wait = WebDriverWait(driver, 30)

        if not automation.login():
            logger.error("Login failed — aborting")
            return
        logger.info("✓ Logged in")
        time.sleep(2)

        if not navigate_to_product_mgmt(automation, wait):
            logger.error("Could not open Product Management")
            return

        for product_id, folder_name in TARGETS.items():
            try:
                ok = process_target(driver, wait, product_id, folder_name)
                (succeeded if ok else failed).append(product_id)
                time.sleep(1)
            except Exception as e:
                logger.error(f"  Unhandled error for ID {product_id}: {e}")
                failed.append(product_id)

    logger.info("\n" + "=" * 60)
    logger.info("TARGETED FIX SUMMARY")
    logger.info(f"  ✓ Succeeded: {len(succeeded)} → IDs: {succeeded}")
    logger.info(f"  ✗ Failed:    {len(failed)} → IDs: {failed}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
