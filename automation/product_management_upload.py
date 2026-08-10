"""
Product Management Image Upload — Ambica Cables
================================================
Features:
  - Progress tracker: saves completed products to a JSON file so the script
    can be safely interrupted and resumed without re-uploading.
  - Batch processing: launches a fresh Chrome session every BATCH_SIZE products
    to prevent browser crashes from long-running sessions.
  - Dual upload: tries hidden file input first; if native Windows file picker
    dialog appears, uses pyautogui to type the full path directly into it.
"""
import json
import os
import logging
import time
import re
from pathlib import Path
from difflib import SequenceMatcher

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException

from dashboard_automation import VendorPortalAutomation

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
AMBICA_PATH = Path(
    r"c:\Users\admin\Desktop\newbldashboardproject\bldashabordautomation\ambica cables"
)
# Progress file — persists which folders are already done
PROGRESS_FILE = Path(__file__).parent / "ambica_upload_progress.json"

# Process N products per Chrome session to avoid browser timeout/crash
BATCH_SIZE = 10

# ── XPaths ──────────────────────────────────────────────────────────────────
MODAL_XPATH         = "//div[contains(@class,'fixed') and contains(@class,'inset-0')]"
REMOVE_IMG_XPATH    = MODAL_XPATH + "//div[.//img]//*[local-name()='svg' and contains(@class,'lucide-x')]"
ADD_BTN_XPATH       = MODAL_XPATH + "//button[contains(., 'Add Image') or .//span[contains(text(), 'Add Image')]]"
SAVE_BTN_XPATH      = MODAL_XPATH + "//button[contains(text(), 'Save Changes') or contains(text(), 'Save') or .//span[contains(text(), 'Save')]]"
FILE_INPUT_XPATH    = MODAL_XPATH + "//input[@type='file']"
PRODUCT_MGMT_BTN    = "div.grid.grid-cols-1 > button:nth-child(6) > h3"

# Native Windows dialog title keywords to detect file picker
DIALOG_KEYWORDS = ["open", "choose file", "upload", "select file", "file upload", "choose files", "browse"]


# ── Helpers ──────────────────────────────────────────────────────────────────
def normalize_to_word_list(name: str) -> list:
    """Normalize a name to a list of clean word tokens."""
    s = name.lower()
    # Keep alphanumeric characters and dots if they are part of a float number, but remove other dots
    s = re.sub(r'[^a-z0-9.]', ' ', s)
    # Remove dots that are not between numbers (e.g. "sq.mm" -> "sq mm", "90 mt." -> "90 mt")
    s = re.sub(r'(?<!\d)\.|\.(?!\d)', ' ', s)
    # Split to words
    words = [w for w in s.split() if w]
    return words


def get_match_score(words_a: list, words_b: list) -> float:
    """Compute matching score between two lists of words."""
    if not words_a or not words_b:
        return 0.0
    
    matched = 0
    used_b = set()
    for wa in words_a:
        found = False
        # Try exact match first
        for idx, wb in enumerate(words_b):
            if idx not in used_b and wa == wb:
                matched += 1
                used_b.add(idx)
                found = True
                break
        if found:
            continue
            
        # Try spelling similarity (like mutistrand vs multistrand)
        for idx, wb in enumerate(words_b):
            if idx not in used_b:
                if len(wa) >= 4 and len(wb) >= 4:
                    ratio = SequenceMatcher(None, wa, wb).ratio()
                    if ratio >= 0.8:
                        matched += 1
                        used_b.add(idx)
                        break
                        
    # Coverage of words_a (how much of the search query matches the target string)
    coverage = matched / len(words_a)
    
    # Tie-breaker: similarity ratio of the clean normalized strings
    clean_a = " ".join(words_a)
    clean_b = " ".join(words_b)
    ratio = SequenceMatcher(None, clean_a, clean_b).ratio()
    
    # Combined score (coverage scaled, ratio handles tie breaking)
    return coverage * 10.0 + ratio


def safe_click(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.3)
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def load_progress() -> set:
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            done = set(data.get("done", []))
            logger.info(f"Resuming: {len(done)} products already completed")
            return done
        except Exception:
            pass
    return set()


def save_progress(done: set):
    PROGRESS_FILE.write_text(
        json.dumps({"done": sorted(done)}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def make_file_inputs_visible(driver):
    """JS hack: make all hidden file inputs reachable by send_keys."""
    try:
        driver.execute_script("""
            var modal = document.querySelector('.fixed.inset-0');
            var inputs = modal ? modal.querySelectorAll('input[type="file"]') : document.querySelectorAll('input[type="file"]');
            for (var i = 0; i < inputs.length; i++) {
                inputs[i].style.cssText = 'display:block !important; visibility:visible !important;'
                    + 'opacity:1 !important; width:1px !important; height:1px !important;'
                    + 'position:fixed !important; top:0 !important; left:0 !important; z-index:99999;';
            }
        """)
        time.sleep(0.4)
    except Exception:
        pass


def try_send_keys_to_file_input(driver, image_path: str) -> bool:
    """Try send_keys on the hidden file input. Returns True if successful."""
    try:
        file_inputs = driver.find_elements(By.XPATH, FILE_INPUT_XPATH)
        if file_inputs:
            file_inputs[0].send_keys(image_path)
            logger.info(f"  Uploaded via hidden input: {Path(image_path).name}")
            time.sleep(3)
            return True
    except Exception as e:
        logger.info(f"  Hidden input send_keys failed: {e}")
    return False


def try_native_dialog(image_path: str) -> bool:
    """
    Detect native Windows file picker dialog and type the full path into it.
    Returns True if a dialog was found and path was typed.
    """
    try:
        import pyautogui
        import pygetwindow as gw
    except ImportError:
        logger.warning("  pyautogui/pygetwindow not installed. Run: pip install pyautogui pygetwindow")
        return False

    # Wait up to 5s for a file dialog window to appear
    for _ in range(10):
        try:
            titles = gw.getAllTitles()
            for title in titles:
                if any(kw in title.lower() for kw in DIALOG_KEYWORDS):
                    logger.info(f"  Windows file dialog detected: '{title}'")
                    time.sleep(0.5)
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.2)
                    try:
                        import pyperclip
                        pyperclip.copy(image_path)
                        pyautogui.hotkey('ctrl', 'v')
                        logger.info(f"  Pasted path via clipboard: {image_path}")
                    except ImportError:
                        pyautogui.typewrite(image_path, interval=0.03)
                        logger.info(f"  Typed path: {image_path}")
                    time.sleep(0.3)
                    pyautogui.press('enter')
                    time.sleep(2.5)
                    return True
        except Exception:
            pass
        time.sleep(0.5)

    return False


def upload_product_images(driver, wait, image_paths: list) -> bool:
    """Upload list of images to the product gallery modal and wait for thumbnails to render."""
    make_file_inputs_visible(driver)
    file_inputs = driver.find_elements(By.XPATH, FILE_INPUT_XPATH)
    if not file_inputs:
        logger.warning("No file input found in modal")
        return False
        
    # Try uploading all at once first (works if multiple is supported)
    try:
        all_paths = "\n".join(image_paths)
        file_inputs[0].send_keys(all_paths)
        logger.info(f"  Uploaded {len(image_paths)} images at once")
        
        # Wait for all thumbnails to render in the modal
        start_wait = time.time()
        upload_confirmed = False
        target_close_buttons = len(image_paths)
        while time.time() - start_wait < 25:
            current_close_buttons = driver.find_elements(
                By.XPATH, 
                REMOVE_IMG_XPATH
            )
            if len(current_close_buttons) >= target_close_buttons:
                upload_confirmed = True
                break
            time.sleep(0.5)
            
        if upload_confirmed:
            logger.info("    ✓ Upload confirmed (all thumbnails rendered)")
            return True
        else:
            logger.warning("    ⚠ Thumbnails did not render within 25s for batch upload. Trying sequential fallback...")
    except Exception as e:
        logger.info(f"  Batch upload failed: {e}. Trying sequential upload...")
        
    # Sequential fallback
    uploaded_count = 0
    for idx, path in enumerate(image_paths):
        try:
            make_file_inputs_visible(driver)
            file_inputs = driver.find_elements(By.XPATH, FILE_INPUT_XPATH)
            if not file_inputs:
                logger.warning("  No file inputs found in modal during sequential upload")
                break
                
            # Send keys to the last input (the empty slot input)
            file_inputs[-1].send_keys(path)
            logger.info(f"  Sent path to file input: {Path(path).name}")
            
            # Wait up to 15 seconds for this specific upload to complete and render its close button
            start_wait = time.time()
            upload_confirmed = False
            target_close_buttons = uploaded_count + 1
            while time.time() - start_wait < 15:
                current_close_buttons = driver.find_elements(
                    By.XPATH, 
                    REMOVE_IMG_XPATH
                )
                if len(current_close_buttons) >= target_close_buttons:
                    upload_confirmed = True
                    logger.info(f"    ✓ Upload confirmed (thumbnail rendered)")
                    break
                time.sleep(0.5)
                
            if not upload_confirmed:
                logger.warning(f"    Upload warning: Thumbnail did not render within 15s for {Path(path).name}")
                
            uploaded_count += 1
            time.sleep(1.0)  # brief pause before starting next slot
            
        except Exception as seq_err:
            logger.error(f"  Sequential upload failed for {Path(path).name}: {seq_err}")
            
    # Final sanity check: wait up to 10 seconds for overall thumbnail count to match
    start_sanity = time.time()
    while time.time() - start_sanity < 10:
        current_close_buttons = driver.find_elements(
            By.XPATH, 
            REMOVE_IMG_XPATH
        )
        if len(current_close_buttons) >= len(image_paths):
            logger.info(f"  ✓ Sanity check passed: all {len(image_paths)} thumbnails rendered")
            break
        time.sleep(1.0)
            
    return uploaded_count > 0


def navigate_to_product_mgmt(automation, wait):
    """Navigate to App Settings → Product Management. Returns True on success."""
    driver = automation.driver
    driver.get(automation.APP_SETTINGS)
    time.sleep(3)
    try:
        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, PRODUCT_MGMT_BTN)))
        safe_click(driver, btn)
        logger.info("Clicked Product Management")
        time.sleep(3)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody")))
        return True
    except Exception as e:
        logger.error(f"Failed to open Product Management: {e}")
        return False


# ── Broken-thumbnail scan helpers ────────────────────────────────────────────

def is_row_thumbnail_broken(driver, row) -> bool:
    """Return True if the product row's thumbnail image is missing, failed to load (404), or empty."""
    try:
        return bool(driver.execute_script("""
            var row = arguments[0];
            var img = row.querySelector('td img');
            if (!img) return true;                              // No img element at all
            var src = img.getAttribute('src') || '';
            if (!src || src === '' || src === window.location.href) return true;  // Empty/invalid src
            if (src.startsWith('data:') && src.length < 100) return true;  // Tiny data URI placeholder
            
            // Check for common default placeholder images
            var srcLower = src.toLowerCase();
            if (srcLower.indexOf('no-image') !== -1 || srcLower.indexOf('placeholder') !== -1 || srcLower.indexOf('default') !== -1) {
                return true;
            }
            
            // If Chrome has completed loading the image, check if its naturalWidth is 0 (broken)
            if (img.complete && img.naturalWidth === 0) return true;
            return false;
        """, row))
    except Exception:
        return False


def get_row_product_name(row) -> str:
    """Extract the product name text from a table row (2nd column)."""
    try:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 2:
            return cols[1].text.replace("\n", " ").strip()
    except Exception:
        pass
    return ""


def click_next_page(driver) -> bool:
    """Click the pagination Next button. Returns True if clicked successfully."""
    try:
        next_btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(text())='Next' or @aria-label='Next page'"
            " or @aria-label='next' or contains(@class,'next')]"
            "[not(@disabled) and not(contains(@class,'disabled'))]"
        )
        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(2.5)
        return True
    except NoSuchElementException:
        return False
    except Exception:
        return False


def find_folder_for_product(product_name: str):
    """Find the best-matching folder in AMBICA_PATH for a dashboard product name."""
    if not AMBICA_PATH.exists():
        return None
    name_words = normalize_to_word_list(product_name)
    best_folder = None
    best_score = 0.0
    THRESHOLD = 8.5
    for folder in AMBICA_PATH.iterdir():
        if not folder.is_dir():
            continue
        score = get_match_score(normalize_to_word_list(folder.name), name_words)
        if score > best_score:
            best_score = score
            best_folder = folder
    return best_folder if best_score >= THRESHOLD else None


def scan_and_fix_broken_thumbnails(driver, wait, automation) -> tuple:
    """
    Scan every page of the Product Management table.
    For each row whose thumbnail is broken/empty, find the matching folder
    and re-upload the images.
    Returns (fixed_count, failed_count).
    """
    fixed = 0
    failed = 0
    page = 1
    already_fixed = set()  # Track names fixed this session to avoid infinite loops

    while True:
        logger.info(f"\n── Scanning page {page} for broken thumbnails...")
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr")))
            time.sleep(3)  # Let lazy images and layout settle completely
        except Exception:
            logger.warning("Table not loaded on page scan")
            break

        # Collect broken product names on this page (skip already fixed this session)
        rows = driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
        broken_names = []
        for row in rows:
            if is_row_thumbnail_broken(driver, row):
                name = get_row_product_name(row)
                if name and name not in already_fixed:
                    broken_names.append(name)

        logger.info(f"  Found {len(broken_names)} broken thumbnail(s) on page {page}")
        if broken_names:
            logger.info(f"  Products: {broken_names}")

        # Fix each broken product one at a time
        for product_name in broken_names:
            logger.info(f"\n  → Fixing broken thumbnail: {product_name}")
            
            # Re-locate row on the page to prevent stale references
            rows = driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
            target_row = None
            for r in rows:
                if get_row_product_name(r) == product_name:
                    target_row = r
                    break
            
            if not target_row:
                logger.warning(f"    Row for '{product_name}' no longer found on page {page}")
                continue

            folder = find_folder_for_product(product_name)
            if not folder:
                logger.warning(f"    No matching folder for: '{product_name}'")
                failed += 1
                already_fixed.add(product_name)  # Skip on re-scan
                continue

            images = sorted([
                str(p) for p in folder.iterdir()
                if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            ])
            if not images:
                logger.warning(f"    No images in folder: {folder.name}")
                failed += 1
                already_fixed.add(product_name)
                continue

            logger.info(f"    Matched folder: {folder.name} ({len(images)} images)")
            result = process_one_product(driver, wait, folder, images, row=target_row)

            # Always mark as handled so we don't re-process regardless of result
            already_fixed.add(product_name)

            if result == "ok":
                fixed += 1
                logger.info(f"    ✓ Fixed: {product_name}")
                time.sleep(2)  # Settle
            else:
                failed += 1
                logger.warning(f"    ✗ Failed: {product_name}")
                # Re-navigate back to Product Management
                if not navigate_to_product_mgmt(automation, wait):
                    logger.error("Could not return to Product Management after fix")
                    return fixed, failed

                # Navigate back to current page number
                for _ in range(page - 1):
                    if not click_next_page(driver):
                        break
                time.sleep(1)
                break  # Restart scan of this page after re-navigation
        else:
            # No new broken rows on this page → go to next page
            if not click_next_page(driver):
                logger.info(f"  No more pages after page {page}. Scan complete.")
                break
            page += 1

    return fixed, failed


def process_one_product(driver, wait, folder, image_paths, row=None) -> str:
    """
    Process a single product folder.
    Returns 'ok', 'skip', or 'fail'.
    """
    folder_name = folder.name
    folder_words = normalize_to_word_list(folder_name)

    # ── 0. Dynamically scan table headers ────────────────────────────────
    product_col_idx = 1  # Default to 2nd column
    action_col_idx = -1  # Default to last column
    try:
        headers = driver.find_elements(By.CSS_SELECTOR, "table > thead > tr > th")
        for idx, th in enumerate(headers):
            text = th.text.lower().strip()
            if "product" in text or "name" in text:
                product_col_idx = idx
                logger.debug(f"Dynamic column scanner: Product name column is index {idx}")
            elif "action" in text:
                action_col_idx = idx
                logger.debug(f"Dynamic column scanner: Action column is index {idx}")
    except Exception as col_err:
        logger.warning(f"Error scanning columns dynamically: {col_err}. Using defaults.")

    best_row = None
    best_name = ""

    if row is not None:
        best_row = row
        best_name = get_row_product_name(row)
        logger.info(f"  Using provided row for: '{best_name}'")
    else:
        # ── 1. Find matching row in table using token similarity ─────────────
        rows = driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
        best_score = 0.0

        for r in rows:
            try:
                cols = r.find_elements(By.TAG_NAME, "td")
                if len(cols) <= max(product_col_idx, action_col_idx):
                    continue
                    
                product_name = cols[product_col_idx].text.replace("\n", " ").strip()
                row_words = normalize_to_word_list(product_name)
                
                score = get_match_score(folder_words, row_words)
                if score > best_score:
                    best_score = score
                    best_row = r
                    best_name = product_name
            except Exception:
                continue

        # Accept match if score is sufficiently high (>= 9.0)
        MATCH_THRESHOLD = 9.0
        if best_row is None or best_score < MATCH_THRESHOLD:
            logger.warning(f"  No table match for: {folder_name} (Best score: {best_score:.2f}, match: '{best_name}')")
            return "skip"

        logger.info(f"  Matched → '{best_name}' (Score: {best_score:.2f})")

    try:
        # ── 2. Click action button ──────────────────────────────────────
        cols = best_row.find_elements(By.TAG_NAME, "td")
        action_td = cols[action_col_idx]
        
        # Try finding button by text first, then by selector
        try:
            action_btn = action_td.find_element(By.XPATH, ".//button[contains(., 'Actions')]")
        except NoSuchElementException:
            action_btn = action_td.find_element(By.TAG_NAME, "button")
            
        safe_click(driver, action_btn)
        time.sleep(1.5)

        # ── 3. Click Edit Profile (dropdown menu item) ──────────────────
        try:
            # Look globally for a span containing "Edit Profile"
            edit_span = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[text()='Edit Profile' or contains(text(), 'Edit Profile')]")
            ))
            # Try clicking the span, fallback to parent button if needed
            try:
                safe_click(driver, edit_span)
            except Exception:
                parent_btn = edit_span.find_element(By.XPATH, "./ancestor::button")
                safe_click(driver, parent_btn)
        except Exception as edit_err:
            logger.error(f"Failed to click Edit Profile: {edit_err}")
            return "fail"
            
        time.sleep(2)

        # ── 4. Wait for modal ────────────────────────────────────────────
        wait.until(EC.presence_of_element_located((By.XPATH, MODAL_XPATH)))
        logger.info("  Modal opened")
        time.sleep(1.5)

        # ── 5. Remove all existing images ────────────────────────────────
        try:
            # Dynamically query close buttons to avoid stale element reference errors after React updates
            while True:
                remove_svgs = driver.find_elements(By.XPATH, MODAL_XPATH + "//*[local-name()='svg' and contains(@class, 'lucide-x')]")
                if not remove_svgs:
                    break
                logger.info(f"  Removing an existing image (remaining: {len(remove_svgs)})")
                svg = remove_svgs[0]
                try:
                    try:
                        parent_button = svg.find_element(By.XPATH, "./parent::button")
                        safe_click(driver, parent_button)
                    except Exception:
                        safe_click(driver, svg)
                    time.sleep(1.5)  # Wait for React DOM update to finish
                except Exception as remove_err:
                    logger.warning(f"  Failed to click remove image button: {remove_err}")
                    break
            time.sleep(1)
        except Exception as e:
            logger.info(f"  Remove image skipped: {e}")

        # ── 6. Upload gallery images ──────────────────────────────────────
        upload_done = upload_product_images(driver, wait, image_paths)

        if not upload_done:
            logger.error(f"  All upload methods failed for: {folder_name}")
            try:
                close = driver.find_element(By.XPATH, MODAL_XPATH + "//button[contains(@class,'absolute')]")
                safe_click(driver, close)
                time.sleep(1)
            except Exception:
                pass
            return "fail"

        # ── 7. Click Save ────────────────────────────────────────────────
        try:
            save_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, SAVE_BTN_XPATH))
            )
            safe_click(driver, save_btn)
            logger.info("  Clicked Save Changes")
        except Exception as save_err:
            logger.error(f"  Failed to click Save Changes button: {save_err}")
            # Try to click by class or selector or text directly
            try:
                save_btn = driver.find_element(By.XPATH, "//button[contains(., 'Save Changes') or contains(text(), 'Save')]")
                safe_click(driver, save_btn)
                logger.info("  Clicked Save (fallback)")
            except Exception:
                return "fail"

        # ── 8. Wait for modal to close, then force-close if needed ─────────────
        try:
            WebDriverWait(driver, 15).until(
                EC.invisibility_of_element_located((By.XPATH, MODAL_XPATH))
            )
            logger.info(f"  ✓ Done: {best_name}")
        except TimeoutException:
            # Modal still open — try to close it explicitly then confirm saved
            logger.warning("  Modal did not auto-close — trying to force-close")
            closed = False
            # Try 1: click the close/X button
            for close_xpath in [
                MODAL_XPATH + "//button[contains(@class,'absolute') and contains(@class,'top')]",
                MODAL_XPATH + "//button[@aria-label='Close' or @aria-label='close']",
                MODAL_XPATH + "//button[.//*[local-name()='svg' and contains(@class,'close')]]",
                MODAL_XPATH + "//button[last()]",
            ]:
                try:
                    close_btn = driver.find_element(By.XPATH, close_xpath)
                    safe_click(driver, close_btn)
                    time.sleep(1.5)
                    # Check if modal gone now
                    modals = driver.find_elements(By.XPATH, MODAL_XPATH)
                    if not modals or not modals[0].is_displayed():
                        closed = True
                        break
                except Exception:
                    continue
            # Try 2: press Escape key
            if not closed:
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys('\ue00c')  # ESC
                    time.sleep(1.5)
                    modals = driver.find_elements(By.XPATH, MODAL_XPATH)
                    if not modals or not modals[0].is_displayed():
                        closed = True
                except Exception:
                    pass
            # Try 3: JS remove modal
            if not closed:
                try:
                    driver.execute_script("""
                        var modals = document.querySelectorAll('.fixed.inset-0');
                        modals.forEach(function(m) { m.remove(); });
                    """)
                    time.sleep(0.5)
                    closed = True
                except Exception:
                    pass

            if closed:
                logger.info(f"  ✓ Done (force-closed modal): {best_name}")
            else:
                logger.warning(f"  Could not close modal — marking fail: {best_name}")
                return "fail"

        time.sleep(1)
        return "ok"

    except (InvalidSessionIdException, Exception) as e:
        logger.error(f"  Error processing '{folder_name}': {e}")
        # Try to dismiss modal
        try:
            close = driver.find_element(
                By.XPATH,
                MODAL_XPATH + "//button[contains(@class,'absolute')]"
            )
            safe_click(driver, close)
            time.sleep(1)
        except Exception:
            pass
        # Re-raise session errors so batch loop can restart browser
        if isinstance(e, InvalidSessionIdException) or "invalid session" in str(e).lower():
            raise
        return "fail"



def run_product_management_upload(email, password):
    logger.info("=" * 60)
    logger.info("PRODUCT MANAGEMENT IMAGE UPLOAD — Ambica Cables")
    logger.info("=" * 60)

    if not AMBICA_PATH.exists():
        logger.error(f"Ambica Cables folder not found: {AMBICA_PATH}")
        return False

    # Check if we should run scan-only or full
    is_unattended = os.getenv("AUTOMATION_CHOICE") is not None
    if is_unattended:
        mode = "1"  # Default to scan-only in unattended mode
    else:
        print("\n  ─── Product Management Upload Modes ───")
        print("  Press 1 : Scan & Fix Broken/Empty Thumbnails (Recommended)")
        print("  Press 2 : Full Folder Upload (Iterate folders → Scan & Fix)")
        print("  Press 0 : Cancel")
        print()
        mode = input("  Select mode [1]: ").strip()
        if not mode:
            mode = "1"
        if mode == "0":
            logger.info("Task cancelled by user.")
            return True

    if mode == "1":
        logger.info("\n" + "=" * 60)
        logger.info("SCANNING FOR BROKEN/EMPTY THUMBNAILS...")
        logger.info("=" * 60)
        try:
            with VendorPortalAutomation(email, password, headless=False) as automation2:
                driver2 = automation2.driver
                wait2 = WebDriverWait(driver2, 20)
                if automation2.login():
                    time.sleep(2)
                    if navigate_to_product_mgmt(automation2, wait2):
                        scan_fixed, scan_failed = scan_and_fix_broken_thumbnails(driver2, wait2, automation2)
                        logger.info("\n" + "=" * 60)
                        logger.info("SCAN SUMMARY")
                        logger.info(f"  ✓ Broken thumbnails fixed : {scan_fixed}")
                        logger.info(f"  ✗ Could not fix           : {scan_failed}")
                        logger.info("=" * 60)
                        if scan_fixed == 0 and scan_failed == 0:
                            logger.info("  All thumbnails are healthy — nothing needed fixing!")
        except Exception as scan_err:
            logger.error(f"Scan error: {scan_err}")
            return False
        return True

    # ── Collect all product folders ──────────────────────────────────────
    all_folders = sorted([f for f in AMBICA_PATH.iterdir() if f.is_dir()])
    logger.info(f"Total folders found: {len(all_folders)}")

    # ── Load progress (skip already done) ───────────────────────────────
    done_set = load_progress()

    # Filter only folders with images that are not yet done
    pending = []
    for folder in all_folders:
        if folder.name in done_set:
            logger.info(f"  ✓ Already done (skipping): {folder.name}")
            continue
        images = (
            list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg"))
            + list(folder.glob("*.png")) + list(folder.glob("*.webp"))
        )
        if not images:
            logger.warning(f"  No image in folder (skipping): {folder.name}")
            done_set.add(folder.name)  # mark as handled so we don't retry
            save_progress(done_set)
            continue
        pending.append((folder, [str(img.absolute()) for img in images]))

    if not pending:
        logger.info("All products already processed! Nothing to do.")
        return True

    logger.info(f"Pending: {len(pending)} products to upload")

    # ── Process in batches ───────────────────────────────────────────────
    succeeded = 0
    failed = 0
    total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        batch = pending[batch_num * BATCH_SIZE : (batch_num + 1) * BATCH_SIZE]
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH {batch_num + 1}/{total_batches} — {len(batch)} products")
        logger.info(f"{'='*60}")

        try:
            with VendorPortalAutomation(email, password, headless=False) as automation:
                driver = automation.driver
                wait = WebDriverWait(driver, 15)

                # ── Login ────────────────────────────────────────────────
                logger.info("Logging in…")
                if not automation.login():
                    logger.error("Login failed — aborting batch")
                    # These items will be retried on next run (not marked done)
                    failed += len(batch)
                    continue
                time.sleep(2)

                # ── Navigate to Product Management ───────────────────────
                if not navigate_to_product_mgmt(automation, wait):
                    logger.error("Could not open Product Management — aborting batch")
                    failed += len(batch)
                    continue

                # ── Process each folder in this batch ────────────────────
                for folder, image_paths in batch:
                    folder_name = folder.name
                    logger.info(f"\n{'─'*60}")
                    logger.info(f"Processing: {folder_name}")
                    logger.info(f"Image paths: {image_paths}")

                    try:
                        result = process_one_product(driver, wait, folder, image_paths)
                    except (InvalidSessionIdException, Exception) as session_err:
                        if "invalid session" in str(session_err).lower():
                            logger.error(f"  Browser session died — will restart for remaining items")
                            failed += 1
                            # Items after this in the batch will be retried next batch
                            break
                        result = "fail"

                    if result == "ok":
                        succeeded += 1
                        done_set.add(folder_name)
                        save_progress(done_set)   # save after EVERY success
                    elif result == "fail":
                        failed += 1
                        # Don't add to done_set — will retry next run
                    # "skip" — no match in table
                    else:
                        done_set.add(folder_name)  # skip permanently
                        save_progress(done_set)

        except Exception as batch_err:
            logger.error(f"Batch {batch_num + 1} crashed: {batch_err}")
            import traceback
            logger.error(traceback.format_exc())

    # ── Final Summary ─────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("PRODUCT MANAGEMENT UPLOAD — FIRST PASS SUMMARY")
    logger.info(f"  ✓ Succeeded this run : {succeeded}")
    logger.info(f"  ✗ Failed this run    : {failed}")
    logger.info(f"  Total done (all runs): {len(done_set)}")
    logger.info("=" * 60)

    # ── Second pass: scan table for any remaining broken thumbnails ────────
    logger.info("\n" + "=" * 60)
    logger.info("SECOND PASS — Scanning for broken/empty thumbnails...")
    logger.info("=" * 60)
    try:
        with VendorPortalAutomation(email, password, headless=False) as automation2:
            driver2 = automation2.driver
            wait2 = WebDriverWait(driver2, 20)
            if automation2.login():
                time.sleep(2)
                if navigate_to_product_mgmt(automation2, wait2):
                    scan_fixed, scan_failed = scan_and_fix_broken_thumbnails(driver2, wait2, automation2)
                    logger.info("\n" + "=" * 60)
                    logger.info("SECOND PASS SUMMARY")
                    logger.info(f"  ✓ Broken thumbnails fixed : {scan_fixed}")
                    logger.info(f"  ✗ Could not fix           : {scan_failed}")
                    logger.info("=" * 60)
                    if scan_fixed == 0 and scan_failed == 0:
                        logger.info("  All thumbnails are healthy — nothing needed fixing!")
    except Exception as scan_err:
        logger.error(f"Second pass scan error: {scan_err}")

    return failed == 0


if __name__ == "__main__":
    import os
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    email = os.getenv("VENDOR_EMAIL", "ambicacableco1985@gmail.com")
    password = os.getenv("VENDOR_PASSWORD", "Ambica123@")

    # Pass --scan-only to only run the broken-thumbnail scan (skip folder loop)
    if "--scan-only" in sys.argv:
        logger.info("Running in SCAN-ONLY mode — fixing broken thumbnails...")
        with VendorPortalAutomation(email, password, headless=False) as auto:
            drv = auto.driver
            wt = WebDriverWait(drv, 20)
            if auto.login():
                time.sleep(2)
                if navigate_to_product_mgmt(auto, wt):
                    s_fixed, s_failed = scan_and_fix_broken_thumbnails(drv, wt, auto)
                    logger.info(f"Scan complete: fixed={s_fixed}, failed={s_failed}")
    else:
        run_product_management_upload(email, password)

