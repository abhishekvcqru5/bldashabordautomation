
import logging
import time
from datetime import datetime
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

logger = logging.getLogger(__name__)

from dashboard_automation import VendorPortalAutomation

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

def get_app_settings_url():
    return getattr(VendorPortalAutomation, "APP_SETTINGS", APP_SETTINGS)

class GiftManagementAutomation:
    def __init__(self, driver, wait_time=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_time)

    def _ss(self, name):
        try:
            d = Path("automation/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"gift_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(str(p))
            logger.info(f"  📸 Screenshot saved: {p}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def navigate(self):
        try:
            logger.info("Going to App Settings...")
            self.driver.get(get_app_settings_url())
            time.sleep(3)

            # Click Gift Management
            # Selector: #root > div... > main > div.grid... > button:nth-child(5) > h3
            gift_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "main > div.grid > button:nth-child(5)")
                )
            )
            gift_btn.click()
            time.sleep(3)
            logger.info("  → Gift Management section opened")
            return True
        except Exception as e:
            logger.error(f"Navigation to gift management failed: {e}")
            self._ss("nav_error")
            return False

    def check_gift_exists(self, gift_name, user_type):
        """
        Check if a gift with the given name and user type already exists in the table.
        """
        try:
            # Wait up to 5 seconds for table to load
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr"))
            )
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
            for row in rows:
                text = row.text.lower()
                if gift_name.lower().strip() in text and user_type.lower().strip() in text:
                    return True
            return False
        except Exception:
            return False

    def process_gifts(self, image_path):
        try:
            # Wait for table to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr")))
            
            # Get the number of rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
            total_rows = len(rows)
            logger.info(f"  Found {total_rows} gifts to process")

            for i in range(1, total_rows + 1):
                logger.info(f"  --- Processing Gift {i} of {total_rows} ---")
                
                try:
                    # Re-find the action button for the i-th row (table might have refreshed)
                    action_btn_sel = f"table > tbody > tr:nth-child({i}) td.sticky.right-0 div > button"
                    action_btn = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, action_btn_sel))
                    )
                    
                    # Scroll into view to be safe
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", action_btn)
                    time.sleep(0.5)
                    
                    action_btn.click()
                    time.sleep(1)
                    logger.info(f"    → Action button {i} clicked")

                    # 2. Click Edit Offering
                    # The dropdown is usually global or relative to the action button
                    # We'll use a text-based search for "Edit Offering" within the opened dropdown
                    edit_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Edit Offering')]"))
                    )
                    edit_btn.click()
                    time.sleep(2)
                    logger.info("    → Edit Offering clicked")

                    # 3. Remove old image
                    try:
                        remove_btn = self.driver.find_elements(By.CSS_SELECTOR, "div.fixed.inset-0 button.text-red-500, div.fixed.inset-0 button[title*='Delete'], div.fixed.inset-0 button[title*='Remove']")
                        if remove_btn:
                            remove_btn[0].click()
                            time.sleep(1)
                            logger.info("    → Old image removed")
                    except Exception:
                        pass

                    # 4. Upload new image
                    try:
                        file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                        file_input.send_keys(str(Path(image_path).absolute()))
                        time.sleep(2)
                        logger.info(f"    → Image uploaded")
                    except Exception as e:
                        logger.warning(f"    ⚠ Upload failed: {e}")

                    # 5. Enable Cash Out toggle
                    try:
                        # Find the toggle container for Cash Out
                        # It's usually a label or div containing the text "Cash Out"
                        toggle_label = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, "//div[contains(., 'Cash Out')]//label"))
                        )
                        toggle_label.click()
                        time.sleep(1)
                        logger.info("    → Cash Out enabled")
                    except Exception as e:
                        logger.warning(f"    ⚠ Could not find Cash Out toggle: {e}")

                    # 6. Click IMPS button
                    try:
                        imps_btn = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'IMPS')]"))
                        )
                        imps_btn.click()
                        time.sleep(1)
                        logger.info("    → IMPS button clicked")
                    except Exception as e:
                        logger.warning(f"    ⚠ Could not find IMPS button: {e}")

                    # 7. Click Save button
                    save_btn_sel = "div.fixed.inset-0 div.p-5.border-t button.bg-indigo-600"
                    save_btn = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, save_btn_sel))
                    )
                    save_btn.click()
                    time.sleep(3)
                    logger.info(f"  ✓ Gift {i} updated successfully")

                    # Wait for table to be visible again
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr")))
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"  ✗ Error processing Gift {i}: {e}")
                    self._ss(f"gift_error_{i}")
                    # Try to close popup if it's still open
                    try:
                        cancel_btn = self.driver.find_elements(By.XPATH, "//button[contains(., 'Cancel')]")
                        if cancel_btn:
                            cancel_btn[0].click()
                            time.sleep(1)
                    except:
                        pass
                    continue

            logger.info("✓ Finished processing all gifts in the table")
            return True

        except Exception as e:
            logger.error(f"Fatal error in process_gifts: {e}")
            self._ss("fatal_error")
            return False

    def get_available_user_types(self):
        """
        Open the Add New Gift modal, inspect the #UserType dropdown to dynamically
        fetch all available user types, and close the modal.
        Returns: (user_types: list[str], is_multiple: bool)
        """
        try:
            add_btn = None
            selectors = [
                "//button[contains(., 'Add New Gift') or contains(., 'Add Gift') or contains(., 'New Gift')]",
                "div.px-6.py-4.flex.items-center.justify-between > button",
                "main div.space-y-8 button"
            ]
            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        add_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                    else:
                        add_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    if add_btn:
                        break
                except Exception:
                    continue

            if not add_btn:
                logger.error("Could not find 'Add New Gift' button to fetch user types.")
                return [], False

            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
            time.sleep(0.5)
            try:
                add_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(2)

            select_el = self.wait.until(EC.presence_of_element_located((By.ID, "UserType")))
            select_obj = Select(select_el)
            is_multiple = select_obj.is_multiple

            user_types = []
            for opt in select_obj.options:
                val = opt.get_attribute("value")
                txt = opt.text.strip()
                if val and val.strip() and txt and txt.lower() != "select user type":
                    user_types.append(txt)

            # Close modal
            cancel_btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'Cancel') or contains(., 'Discard')]")
            if cancel_btns:
                cancel_btns[0].click()
                time.sleep(1)

            return user_types, is_multiple
        except Exception as e:
            logger.warning(f"Failed to dynamically fetch user types: {e}")
            try:
                cancel_btns = self.driver.find_elements(By.XPATH, "//button[contains(., 'Cancel') or contains(., 'Discard')]")
                if cancel_btns:
                    cancel_btns[0].click()
            except Exception:
                pass
            return [], False

    def add_new_gift(self, gift_data, target_user_types=None):
        """
        Add a single new gift offering.
        gift_data keys:
            name         - Name of the gift
            description  - Description of the gift
            points       - Redemption points (optional, string of digits)
            value        - Market value (optional, string of digits)
            image_path   - Absolute path to the gift image
        target_user_types - List of user type names to select (optional)
        """
        name = gift_data.get("name", "Unnamed Gift")
        logger.info(f"  Adding new gift: '{name}' (Target user types: {target_user_types})")

        try:
            # Wait for previous modal / overlay to be gone
            try:
                WebDriverWait(self.driver, 6).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.fixed.inset-0"))
                )
            except Exception:
                pass
            time.sleep(0.5)

            # 1. Click "Add New Gift" button
            add_btn = None
            selectors = [
                "//button[contains(., 'Add New Gift') or contains(., 'Add Gift') or contains(., 'New Gift')]",
                "div.px-6.py-4.flex.items-center.justify-between > button",
                "//main//button[contains(., 'Add') or contains(., 'Gift') or contains(., 'New')]",
                "main div.space-y-8 button"
            ]
            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        add_btn = WebDriverWait(self.driver, 8).until(EC.element_to_be_clickable((By.XPATH, sel)))
                    else:
                        add_btn = WebDriverWait(self.driver, 8).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    if add_btn and add_btn.is_displayed():
                        break
                except Exception:
                    continue

            if not add_btn:
                logger.error("    ✗ Could not find 'Add New Gift' button.")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
            time.sleep(0.5)
            try:
                add_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", add_btn)
            time.sleep(2)
            logger.info("    → 'Add New Gift' clicked")

            # 2. Enter Gift Name
            gift_name_field = self.wait.until(EC.presence_of_element_located((By.ID, "Gift_name")))
            gift_name_field.clear()
            gift_name_field.send_keys(name)
            logger.info(f"    → Entered label: {name}")

            # 3. Enter Detail Description
            gift_desc_field = self.driver.find_element(By.ID, "Gift_desc")
            gift_desc_field.clear()
            gift_desc_field.send_keys(gift_data.get("description", name))
            logger.info("    → Entered description")

            # 4. Upload Image(s)
            image_paths = gift_data.get("image_paths")
            if not image_paths:
                single_p = gift_data.get("image_path")
                image_paths = [single_p] if single_p else []

            for p_idx, img_p in enumerate(image_paths, 1):
                if not img_p or not Path(img_p).exists():
                    logger.warning(f"    ⚠ Image path not found: {img_p}")
                    continue
                abs_path = str(Path(img_p).resolve())
                try:
                    file_input = None
                    # Search inside topmost modal
                    modal_els = self.driver.find_elements(By.CSS_SELECTOR, "div.fixed.inset-0")
                    if modal_els:
                        modal_inputs = modal_els[-1].find_elements(By.CSS_SELECTOR, "input[type='file']")
                        if modal_inputs:
                            file_input = modal_inputs[-1]
                    
                    if not file_input:
                        space_y_inputs = self.driver.find_elements(By.CSS_SELECTOR, "div.space-y-1\\.5 input[type='file'], div.space-y-1.5 input[type='file']")
                        if space_y_inputs:
                            file_input = space_y_inputs[-1]

                    if not file_input:
                        all_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                        if all_inputs:
                            file_input = all_inputs[-1]

                    if file_input:
                        # Make visible for Chrome send_keys
                        try:
                            self.driver.execute_script("""
                                arguments[0].style.cssText = 'display:block !important; visibility:visible !important;'
                                    + 'opacity:1 !important; width:100px !important; height:30px !important;'
                                    + 'position:fixed !important; top:0 !important; left:0 !important; z-index:999999;';
                            """, file_input)
                        except Exception:
                            pass

                        try:
                            self.driver.execute_script("arguments[0].value = '';", file_input)
                        except Exception:
                            pass

                        file_input.send_keys(abs_path)

                        # Trigger React synthetic input/change events
                        try:
                            self.driver.execute_script("""
                                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                            """, file_input)
                        except Exception:
                            pass

                        time.sleep(2)
                        logger.info(f"    → Image uploaded ({p_idx}/{len(image_paths)}): {Path(img_p).name}")
                    else:
                        logger.warning(f"    ⚠ Could not locate file input in modal for: {Path(img_p).name}")
                except Exception as img_e:
                    logger.warning(f"    ⚠ Image input error: {img_e}")

            # 5. Enter Redemption Point (#Gift_point)
            try:
                point_els = self.driver.find_elements(By.ID, "Gift_point")
                if point_els and point_els[0].is_displayed():
                    gift_point_field = point_els[0]
                    gift_point_field.clear()
                    points_val = str(gift_data.get("points", "0"))
                    gift_point_field.send_keys(points_val)
                    logger.info(f"    → Entered redeem points: {points_val}")
            except Exception as pt_e:
                logger.warning(f"    ⚠ Could not fill Gift_point: {pt_e}")

            # 5.1 Enter Market Value (#Gift_value)
            try:
                val_els = self.driver.find_elements(By.ID, "Gift_value")
                if val_els and val_els[0].is_displayed():
                    gift_value_field = val_els[0]
                    gift_value_field.clear()
                    market_val = str(gift_data.get("value", "0"))
                    gift_value_field.send_keys(market_val)
                    logger.info(f"    → Entered market value: {market_val}")
            except Exception as val_e:
                logger.warning(f"    ⚠ Could not find or fill Gift_value field: {val_e}")

            # 6. Interact with User Type dropdown (#UserType)
            try:
                user_type_els = self.driver.find_elements(By.ID, "UserType")
                if user_type_els and user_type_els[0].is_displayed():
                    select_el = user_type_els[0]
                    select_obj = Select(select_el)
                    
                    if target_user_types:
                        if isinstance(target_user_types, str):
                            target_list = [target_user_types]
                        else:
                            target_list = list(target_user_types)

                        targets_lower = [t.lower().strip() for t in target_list]
                        matched_option_texts = []
                        for option in select_obj.options:
                            opt_text = option.text.strip().lower()
                            opt_val = option.get_attribute("value").strip().lower()
                            for target in targets_lower:
                                if target == opt_text or target == opt_val:
                                    matched_option_texts.append(option.text)
                                    break

                        if select_obj.is_multiple:
                            select_obj.deselect_all()
                            for opt_text in matched_option_texts:
                                select_obj.select_by_visible_text(opt_text)
                            logger.info(f"    → Selected user types: {matched_option_texts}")
                        elif matched_option_texts:
                            select_obj.select_by_visible_text(matched_option_texts[0])
                            logger.info(f"    → Selected user type: {matched_option_texts[0]}")
                    else:
                        # Select all non-empty options if multi-select
                        if select_obj.is_multiple:
                            for option in select_obj.options:
                                if option.get_attribute("value") and option.get_attribute("value").strip():
                                    try:
                                        select_obj.select_by_visible_text(option.text)
                                    except Exception:
                                        pass
                            logger.info("    → Selected all available user types")
            except Exception as ut_e:
                logger.warning(f"    ⚠ UserType selection skipped/handled: {ut_e}")

            # 7. Submit / Click "Create Offering"
            submit_btn = None
            submit_selectors = [
                "div.fixed.inset-0 div.p-5.border-t button.bg-indigo-600",
                "//button[contains(., 'Create Offering') or contains(., 'Create offering') or contains(., 'Create') or contains(., 'Add') or contains(@class, 'bg-indigo-600')]",
                "div.fixed.inset-0 button.bg-indigo-600"
            ]
            for sel in submit_selectors:
                try:
                    if sel.startswith("//"):
                        submit_btn = self.driver.find_element(By.XPATH, sel)
                    else:
                        submit_btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if submit_btn and submit_btn.is_displayed():
                        break
                except Exception:
                    continue

            if not submit_btn:
                logger.error("    ✗ Could not find submit/create button.")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_btn)
            time.sleep(0.5)
            try:
                submit_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", submit_btn)
            time.sleep(3)
            logger.info(f"  ✓ Offering created for '{name}'")

            # Wait for modal to disappear/table to reload
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.fixed.inset-0"))
                )
            except Exception:
                pass
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, 'backdrop-blur') or contains(@class, 'bg-black/60')]"))
                )
            except Exception:
                pass
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"  ✗ Failed to add gift offering: {e}")
            self._ss(f"add_gift_fail_{name.replace(' ', '_')}")
            # Attempt to click cancel/close modal if still open
            try:
                cancel_btn = self.driver.find_elements(By.XPATH, "//button[contains(., 'Cancel') or contains(., 'Discard')]")
                if cancel_btn:
                    cancel_btn[0].click()
                    time.sleep(1)
            except Exception:
                pass
            return False

def run_gift_management(email, password, image_path):
    from dashboard_automation import VendorPortalAutomation
    
    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                return False
            
            time.sleep(2)
            gift_auto = GiftManagementAutomation(auto.driver)
            
            if not gift_auto.navigate():
                return False
            
            return gift_auto.process_gifts(image_path)
            
    except Exception as e:
        logger.error(f"Unexpected error in gift management: {e}")
        return False

def run_interactive_gifts_upload(email, password):
    """
    Option 24: 
    1. Check images in gift/ folder.
    2. Open Vendor Portal and dynamically fetch available User Types from the modal.
    3. For each numbered image, prompt user for:
       - Gift Label (#Gift_name)
       - Gift Description (#Gift_desc)
       - Redeem Points (#Gift_point)
       - Market Value (#Gift_value)
       - Target Audience (#UserType) - user selects from dynamic list (or All)
    4. Display a final review table.
    5. On user submit, run the automated upload for all defined gifts.
    """
    import re
    from dashboard_automation import VendorPortalAutomation

    # 1. Locate gift folder
    possible_folders = [
        Path(__file__).resolve().parent.parent / "gift",
        Path(__file__).resolve().parent / "gift",
        Path("gift")
    ]
    gift_folder = None
    for folder in possible_folders:
        if folder.exists() and folder.is_dir():
            gift_folder = folder
            break

    if not gift_folder:
        gift_folder = Path(__file__).resolve().parent.parent / "gift"
        gift_folder.mkdir(parents=True, exist_ok=True)

    # 2. Find image files
    valid_extensions = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".gif"}
    image_files = [
        f for f in gift_folder.iterdir() 
        if f.is_file() and f.suffix.lower() in valid_extensions
    ]

    if not image_files:
        print("\n" + "=" * 65)
        print("  ❌ NO IMAGES FOUND IN GIFT FOLDER")
        print("=" * 65)
        print(f"  Folder location: {gift_folder.absolute()}")
        print("  Please place your numbered images (e.g. 1.jpeg, 2.png, 3.jpg...)")
        print("  in the gift folder and select Option 24 again.\n")
        return False

    # 3. Sort images numerically / naturally
    def sort_key(p: Path):
        m = re.match(r"^(\d+)", p.stem)
        if m:
            return (0, int(m.group(1)), p.name.lower())
        all_num = re.findall(r"\d+", p.stem)
        if all_num:
            return (1, int(all_num[0]), p.name.lower())
        return (2, 0, p.name.lower())

    sorted_images = sorted(image_files, key=sort_key)

    print("\n" + "=" * 65)
    print("  🎁 GIFT UPLOAD SETUP — CONNECTING TO PORTAL")
    print("=" * 65)
    print(f"  Found {len(sorted_images)} images in: {gift_folder.name}/")
    for i, img in enumerate(sorted_images, 1):
        print(f"    {i}. {img.name}")
    print("-" * 65)
    print("  Connecting to portal to fetch available User Types / Target Audiences...")

    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed")
                return False

            time.sleep(2)
            gift_auto = GiftManagementAutomation(auto.driver)

            if not gift_auto.navigate():
                logger.error("✗ Failed to navigate to Gift Management")
                return False

            # Fetch dynamic user types
            available_user_types, is_multiple = gift_auto.get_available_user_types()
            if not available_user_types:
                logger.warning("Could not automatically retrieve user types from dropdown. Providing standard fallback.")
                available_user_types = ["Architect", "Gypsum Contractor", "Tile Applicator", "Painter"]

            print("\n" + "=" * 65)
            print("  📋 CONFIGURE GIFT DETAILS")
            print("=" * 65)
            print(f"  Available Target Audiences (Dynamic User Types):")
            print("    0. ALL User Types")
            for idx, ut in enumerate(available_user_types, 1):
                print(f"    {idx}. {ut}")
            print("-" * 65)
            print("  Please enter details for each gift image:\n")

            gifts_data = []
            for idx, img_path in enumerate(sorted_images, 1):
                print(f"  [{idx}/{len(sorted_images)}] ── Image: {img_path.name}")
                
                # 1. Gift Label (#Gift_name)
                while True:
                    label = input(f"    Enter Gift Label for '{img_path.name}': ").strip()
                    if label:
                        break
                    print("    ⚠️ Gift Label cannot be empty. Please enter a valid label.")
                    
                # 2. Gift Description (#Gift_desc)
                desc = input(f"    Enter Gift Description (press Enter for '{label}'): ").strip()
                if not desc:
                    desc = label

                # 3. Redeem Points (#Gift_point)
                while True:
                    pts_input = input(f"    Enter Redeem Points (e.g. 1000): ").strip()
                    if not pts_input:
                        print("    ⚠️ Redeem points cannot be empty.")
                        continue
                    pts_clean = pts_input.replace(",", "").strip()
                    if pts_clean.isdigit():
                        points = pts_clean
                        break
                    print("    ⚠️ Please enter a valid numeric value for redeem points.")

                # 4. Market Value (#Gift_value)
                val_input = input(f"    Enter Market Value (e.g. 500, press Enter for 0): ").strip()
                if not val_input:
                    market_val = "0"
                else:
                    market_val = val_input.replace(",", "").strip()

                # 5. Target Audience (#UserType)
                while True:
                    print("    Target Audience Options:")
                    print("      0. ALL User Types")
                    for u_i, ut in enumerate(available_user_types, 1):
                        print(f"      {u_i}. {ut}")
                    target_in = input(f"    Select Target Audience for '{label}' (e.g. 0 for All, or 1,4): ").strip()
                    
                    if not target_in or target_in == "0" or target_in.lower() == "all":
                        selected_user_types = list(available_user_types)
                        break
                    
                    tokens = [t.strip() for t in target_in.replace(",", " ").split() if t.strip()]
                    valid = True
                    chosen = []
                    for tok in tokens:
                        if tok.isdigit():
                            idx_val = int(tok)
                            if 1 <= idx_val <= len(available_user_types):
                                chosen.append(available_user_types[idx_val - 1])
                            else:
                                valid = False
                                break
                        else:
                            matched = [u for u in available_user_types if tok.lower() == u.lower()]
                            if matched:
                                chosen.append(matched[0])
                            else:
                                valid = False
                                break
                    if valid and chosen:
                        selected_user_types = list(dict.fromkeys(chosen))
                        break
                    print(f"    ⚠️ Invalid selection. Please enter numbers between 1 and {len(available_user_types)} or 0 for All.\n")

                gifts_data.append({
                    "name": label,
                    "description": desc,
                    "points": points,
                    "value": market_val,
                    "target_user_types": selected_user_types,
                    "image_path": str(img_path.absolute()),
                    "image_name": img_path.name
                })
                print()

            # 4. Review Summary
            print("=" * 65)
            print("  📋 FINAL REVIEW — GIFTS TO UPLOAD")
            print("=" * 65)
            for idx, g in enumerate(gifts_data, 1):
                print(f"  {idx}. Image           : {g['image_name']}")
                print(f"     Gift Label      : {g['name']}")
                print(f"     Description     : {g['description']}")
                print(f"     Redeem Points   : {g['points']}")
                print(f"     Market Value    : {g['value']}")
                print(f"     Target Audience : {', '.join(g['target_user_types'])}")
                print("-" * 65)
            
            # 5. Final confirmation submit
            print()
            confirm = input("  Ready to submit and start automation? (Y/n): ").strip().lower()
            if confirm not in ("", "y", "yes"):
                print("\n  ❌ Upload cancelled by user.\n")
                return False

            print("\n  🚀 Starting Gift Upload Automation...\n")

            successful = 0
            failed = 0

            if is_multiple:
                total = len(gifts_data)
                for idx, gift in enumerate(gifts_data, 1):
                    logger.info(f"\n[{idx}/{total}] Uploading Gift: '{gift['name']}' ({gift['image_name']})")
                    print(f"  [{idx}/{total}] Uploading: '{gift['name']}' ({gift['image_name']}) for {gift['target_user_types']}...")
                    
                    if gift_auto.add_new_gift(gift, target_user_types=gift["target_user_types"]):
                        successful += 1
                        print(f"  ✓ Uploaded successfully: '{gift['name']}'")
                    else:
                        failed += 1
                        print(f"  ✗ Failed to upload: '{gift['name']}'")
                    time.sleep(1.5)
            else:
                total_ops = sum(len(g["target_user_types"]) for g in gifts_data)
                current_op = 0
                for gift in gifts_data:
                    for utype in gift["target_user_types"]:
                        current_op += 1
                        logger.info(f"\n[{current_op}/{total_ops}] Uploading Gift: '{gift['name']}' for '{utype}'")
                        print(f"  [{current_op}/{total_ops}] Uploading: '{gift['name']}' ({gift['image_name']}) for '{utype}'...")
                        
                        if gift_auto.add_new_gift(gift, target_user_types=[utype]):
                            successful += 1
                            print(f"  ✓ Uploaded successfully: '{gift['name']}' for '{utype}'")
                        else:
                            failed += 1
                            print(f"  ✗ Failed to upload: '{gift['name']}' for '{utype}'")
                        time.sleep(1.5)

            print("\n" + "=" * 65)
            print("  🎁 GIFT UPLOAD SUMMARY")
            print("=" * 65)
            print(f"  Total Gift Operations : {successful + failed}")
            print(f"  ✓ Successful Uploads  : {successful}")
            print(f"  ✗ Failed Uploads      : {failed}")
            print("=" * 65 + "\n")

            return failed == 0

    except Exception as e:
        logger.error(f"Unexpected error in interactive gifts upload: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_narmada_gifts(email, password):
    from dashboard_automation import VendorPortalAutomation
    
    narmada_folder = Path(__file__).resolve().parent.parent / "narmada"
    if not narmada_folder.exists():
        logger.error(f"Narmada images folder not found at: {narmada_folder.absolute()}")
        return False
        
    gifts_data = [
        {"name": "Aristocrat Trolley Bag", "description": "Aristocrat Trolley Bag", "points": "150000", "image_name": "Aristocrat Trolley Bag.jpg"},
        {"name": "48” Havells Fan", "description": "48” Havells Fan", "points": "200000", "image_name": "48” Havells Fan.jpg"},
        {"name": "Pure Silk Saree (Made in Surat)", "description": "Pure Silk Saree (Made in Surat)", "points": "250000", "image_name": "Pure Silk Saree.jpg"},
        {"name": "Ladies Purse / Bangle Box / Makeup Kit", "description": "Ladies Purse / Bangle Box / Makeup Kit", "points": "300000", "image_name": "Ladies Purse.jpeg"},
        {"name": "Raymond Brand Shirt / Pant Clothes", "description": "Raymond Brand Shirt / Pant Clothes", "points": "400000", "image_name": "Raymond Brand Shirt.jpg"},
        {"name": "Faber Juicer Mixer", "description": "Faber Juicer Mixer", "points": "500000", "image_name": "Faber Juicer Mixer.jpg"},
        {"name": "Jaquar Geyser (5 Star Rating)", "description": "Jaquar Geyser (5 Star Rating)", "points": "750000", "image_name": "Jaquar Geyser.jpg"},
        {"name": "Sony LED TV", "description": "Sony LED TV", "points": "1000000", "image_name": "Sony LED TV.jpg"},
        {"name": "Kelvinator Freezer", "description": "Kelvinator Freezer", "points": "1500000", "image_name": "Kelvinator Freezer.jpg"},
        {"name": "Samsung Touch Screen Mobile", "description": "Samsung Touch Screen Mobile", "points": "2000000", "image_name": "Samsung Touch Screen Mobile.jpg"},
        {"name": "Goa Trip ✈️", "description": "Goa Trip ✈️", "points": "2500000", "image_name": "Goa Trip.jpg"},
        {"name": "Couple Goa Trip ✈️", "description": "Couple Goa Trip ✈️", "points": "5000000", "image_name": "Couple Goa Trip.jpg"},
    ]
    
    # Resolve absolute image paths
    for g in gifts_data:
        g["image_path"] = str((narmada_folder / g["image_name"]).absolute())
        
    target_user_types = ["Karpenter", "building contractor", "Electrician", "site supervisor", "plumber", "tile applicator"]
    
    try:
        with VendorPortalAutomation(email, password, headless=False) as auto:
            if not auto.login():
                logger.error("✗ Login failed")
                return False
                
            time.sleep(2)
            gift_auto = GiftManagementAutomation(auto.driver)
            
            if not gift_auto.navigate():
                logger.error("✗ Failed to navigate to Gift Management")
                return False
                
            # Detect dropdown type (multi vs single)
            # Open Add New Gift modal once to check
            logger.info("Opening Add New Gift modal to detect dropdown select type...")
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
            
            select_el = gift_auto.driver.find_element(By.ID, "UserType")
            select_obj = Select(select_el)
            is_multiple = select_obj.is_multiple
            logger.info(f"Dropdown 'is_multiple' detected as: {is_multiple}")
            
            # Close/discard modal
            cancel_btn = gift_auto.driver.find_element(By.XPATH, "//button[contains(., 'Cancel') or contains(., 'Discard')]")
            cancel_btn.click()
            time.sleep(2)
            
            successful_uploads = 0
            failed_uploads = 0
            
            if is_multiple:
                logger.info("Proceeding with multi-select upload flow (one upload per gift)...")
                for idx, gift in enumerate(gifts_data, 1):
                    logger.info(f"Uploading Narmada Gift {idx} of {len(gifts_data)}: {gift['name']}")
                    if gift_auto.add_new_gift(gift, target_user_types):
                        successful_uploads += 1
                    else:
                        failed_uploads += 1
                    time.sleep(1)
            else:
                logger.info("Proceeding with single-select sequential upload flow (each gift added once per user type)...")
                # Expand the list of offerings: 12 gifts * 6 user types = 72 total operations
                total_ops = len(gifts_data) * len(target_user_types)
                current_op = 0
                for gift in gifts_data:
                    for utype in target_user_types:
                        current_op += 1
                        logger.info(f"[{current_op}/{total_ops}] Uploading: '{gift['name']}' for '{utype}'")
                        if gift_auto.add_new_gift(gift, [utype]):
                            successful_uploads += 1
                        else:
                            failed_uploads += 1
                        time.sleep(1)
                        
            logger.info("\n" + "=" * 60)
            logger.info("NARMADA GIFTS AUTOMATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ Successful: {successful_uploads}")
            logger.info(f"✗ Failed: {failed_uploads}")
            logger.info("=" * 60)
            
            return failed_uploads == 0
            
    except Exception as e:
        logger.error(f"Unexpected error in Narmada gifts automation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
