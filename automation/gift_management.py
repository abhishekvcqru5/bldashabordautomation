
import logging
import time
from datetime import datetime
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select

logger = logging.getLogger(__name__)

APP_SETTINGS = "https://app.vcqru.com/vendor/app-settings"

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
            self.driver.get(APP_SETTINGS)
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

    def add_new_gift(self, gift_data, target_user_types):
        """
        Add a single new gift offering.
        gift_data keys:
            name         - Name of the gift
            description  - Description of the gift
            points       - Redemption points (string of digits)
            image_path   - Absolute path to the gift image
        target_user_types - List of user type names to select
        """
        name = gift_data.get("name", "Unnamed Gift")
        logger.info(f"  Adding new gift: '{name}' for {target_user_types}")

        try:
            # 1. Click "Add New Gift" button
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
                logger.error("    ✗ Could not find 'Add New Gift' button.")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
            time.sleep(0.5)
            add_btn.click()
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

            # 4. Upload Image
            image_path = gift_data.get("image_path")
            if image_path and Path(image_path).exists():
                file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                file_input.send_keys(str(Path(image_path).absolute()))
                time.sleep(2)
                logger.info(f"    → Image uploaded: {Path(image_path).name}")
            else:
                logger.warning(f"    ⚠ Image path not found: {image_path}")

            # 5. Enter Redemption Point
            gift_point_field = self.driver.find_element(By.ID, "Gift_point")
            gift_point_field.clear()
            gift_point_field.send_keys(str(gift_data.get("points")))
            logger.info(f"    → Entered points: {gift_data.get('points')}")

            # 6. Interact with User Type dropdown
            select_el = self.driver.find_element(By.ID, "UserType")
            select_obj = Select(select_el)
            
            # Match options case-insensitively
            targets_lower = [t.lower().strip() for t in target_user_types]
            matched_option_texts = []
            
            for option in select_obj.options:
                opt_text = option.text.strip().lower()
                opt_val = option.get_attribute("value").strip().lower()
                for target in targets_lower:
                    if target == opt_text or target == opt_val:
                        matched_option_texts.append(option.text)
                        break

            if not matched_option_texts:
                logger.warning(f"    ⚠ No matching user types found in dropdown for: {target_user_types}")
            else:
                # If it supports multi-select:
                if select_obj.is_multiple:
                    select_obj.deselect_all()
                    for opt_text in matched_option_texts:
                        select_obj.select_by_visible_text(opt_text)
                    logger.info(f"    → Selected user types: {matched_option_texts}")
                else:
                    # Single select dropdown.
                    # We select the first matched option (or standard text match)
                    first_match = matched_option_texts[0]
                    select_obj.select_by_visible_text(first_match)
                    logger.info(f"    → Selected user type (single-select): {first_match}")

            # 7. Submit / Click "Create Offering"
            submit_btn = None
            submit_selectors = [
                "div.fixed.inset-0 div.p-5.border-t button.bg-indigo-600",
                "//button[contains(., 'Create Offering') or contains(., 'Create') or contains(., 'Add') or contains(@class, 'bg-indigo-600')]"
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
            submit_btn.click()
            time.sleep(3)
            logger.info(f"  ✓ Offering created for '{name}'")

            # Wait for modal to disappear/table to reload
            self.wait.until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.fixed.inset-0"))
            )
            time.sleep(1)
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

def run_narmada_gifts(email, password):
    from dashboard_automation import VendorPortalAutomation
    
    narmada_folder = Path("narmada")
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
