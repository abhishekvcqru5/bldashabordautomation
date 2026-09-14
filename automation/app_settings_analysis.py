import json
import logging
import re
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dashboard_automation import VendorPortalAutomation

logger = logging.getLogger(__name__)

def export_to_excel(results, filepath):
    """
    Export the extracted settings to a beautifully formatted multi-sheet Excel workbook.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    
    # Fonts and styles
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Segoe UI", size=10)
    title_font = Font(name="Segoe UI", size=14, bold=True, color="1F4E78")
    
    # Indigo header (matching app branding), light stripe
    header_fill = PatternFill(start_color="4F39F6", end_color="4F39F6", fill_type="solid")
    stripe_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )

    def style_sheet(ws, title, headers, data):
        ws.title = title
        
        # Title row
        ws.append([title.upper() + " CONFIGURATION"])
        ws.cell(row=1, column=1).font = title_font
        ws.append([]) # spacer
        
        # Headers row
        ws.append(headers)
        header_row = 3
        for col_idx, text in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
            
        # Data rows
        current_row = header_row + 1
        for item_idx, row_data in enumerate(data, 1):
            ws.append(row_data)
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                
                # Highlight active status fields in light green, inactive in light red
                val_lower = str(row_data[col_idx-1]).lower()
                if any(x in val_lower for x in ["active", "required", "live", "visible"]):
                    cell.fill = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")
                elif any(x in val_lower for x in ["inactive", "disabled", "hidden"]):
                    cell.fill = PatternFill(start_color="FCE8E6", end_color="FCE8E6", fill_type="solid")
                elif item_idx % 2 == 0:
                    cell.fill = stripe_fill
                    
                # Adjust alignment
                header_name = headers[col_idx-1].lower()
                if col_idx == 1 or "color" in header_name or "id" in header_name or "status" in header_name or "sequence" in header_name or "s.no" in header_name:
                    cell.alignment = Alignment(horizontal="center")
                else:
                    cell.alignment = Alignment(horizontal="left")
            current_row += 1
            
        # Autofit column widths
        for col in ws.columns:
            max_len = 0
            for cell in col:
                if cell.row > 2 and cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # Sheet 1: Branding
    ws = wb.active
    branding_headers = ["Setting Name", "Value"]
    branding_data = [
        ["App Name", results["branding"].get("company_name", "")],
        ["Header Color", results["branding"].get("header_color", "")],
        ["Footer Color", results["branding"].get("footer_color", "")],
        ["Body Color", results["branding"].get("body_color", "")],
        ["Background Color", results["branding"].get("background_color", "")],
        ["Logo URL", results["branding"].get("logo_url", "")],
        ["Splash URL", results["branding"].get("splash_url", "")]
    ]
    style_sheet(ws, "Branding", branding_headers, branding_data)

    # Sheet 2: Support
    ws = wb.create_sheet()
    support_headers = ["Setting Name", "Value"]
    support_data = [
        ["Email", results["support"].get("email", "")],
        ["Phone", results["support"].get("phone", "")],
        ["Office Address", results["support"].get("support_content", "")],
        ["Privacy Policy URL", results["support"].get("privacy_policy", "")],
        ["Terms & Conditions URL", results["support"].get("terms_conditions", "")],
        ["About Us URL", results["support"].get("website", "")]
    ]
    style_sheet(ws, "Support", support_headers, support_data)

    # Sheet 3: Dashboard Icons
    ws = wb.create_sheet()
    icons_headers = ["User Type", "Display Title", "Icon Identity", "Color", "Assigned User", "Sequence", "Visibility Mode", "Status", "Image URL"]
    icons_data = []
    for item in results["dashboard_icons"]:
        icons_data.append([
            item["user_type_section"],
            item["display_title"],
            item["icon_identity"],
            item["color"],
            item["assigned_user"],
            item["sequence"],
            item["visibility_mode"],
            item["status"],
            item["image_url"]
        ])
    style_sheet(ws, "Dashboard Icons", icons_headers, icons_data)

    # Sheet 4: Gifts
    ws = wb.create_sheet()
    gifts_headers = ["S.No", "Gift Name", "Gift ID", "Value", "Points", "Audience", "Status / Mode", "Image URL"]
    gifts_data = []
    for item in results["gifts"]:
        gifts_data.append([
            item["s_no"],
            item["gift_name"],
            item["gift_id"],
            item["value"],
            item["points"],
            item["audience"],
            item["status_mode"],
            item["image_url"]
        ])
    style_sheet(ws, "Gifts", gifts_headers, gifts_data)

    # Sheet 5: KYC & Verification
    ws = wb.create_sheet()
    kyc_headers = ["Document / Rule Name", "Policy Type", "Status"]
    kyc_data = []
    for item in results["kyc"]:
        kyc_data.append([
            item["rule_name"],
            item["policy_type"],
            item["status"]
        ])
    style_sheet(ws, "KYC Rules", kyc_headers, kyc_data)

    # Sheet 6: Claim Settings
    ws = wb.create_sheet()
    claims_headers = ["Channel", "Type", "Policy Name", "Status"]
    claims_data = []
    for item in results["claims"]:
        claims_data.append([
            item["channel"],
            item["type"],
            item["policy_name"],
            item["status"]
        ])
    style_sheet(ws, "Claim Settings", claims_headers, claims_data)

    wb.save(filepath)


def run_app_settings_analysis(email: str, password: str) -> bool:
    """
    Log into new dashboard, extract Identity & Branding, Support Network,
    Dashboard Icons, Gifts list, KYC rules, and Claim settings,
    print the summary to console, and save as JSON and native Excel (.xlsx).
    """
    logger.info("=" * 60)
    logger.info(f"APP SETTINGS ANALYSIS FOR USER: {email}")
    logger.info("=" * 60)

    try:
        with VendorPortalAutomation(email, password, headless=True) as auto:
            # 1. Login
            logger.info("→ Attempting login...")
            if not auto.login():
                logger.error("✗ Login failed. Aborting settings analysis.")
                return False
            
            time.sleep(2)
            results = {
                "user_email": email,
                "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "branding": {},
                "support": {},
                "dashboard_icons": [],
                "gifts": [],
                "kyc": [],
                "claims": []
            }

            # ── 2. Extract Identity & Branding ────────────────────────────────
            logger.info("\n→ Extracting Identity & Branding settings...")
            try:
                app_settings_url = getattr(auto, "app_settings_url", getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings"))
                auto.driver.get(f"{app_settings_url}?brand-setting")
                time.sleep(3)
                
                edit_btn = auto.driver.find_element(By.XPATH, "//button[contains(text(),'Edit Branding')]")
                auto.driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", edit_btn)
                time.sleep(2.5)
                
                results["branding"]["company_name"] = auto.driver.find_element(By.NAME, "CompanyName").get_attribute("value") or ""
                results["branding"]["header_color"] = auto.driver.find_element(By.NAME, "HeaderColor").get_attribute("value") or ""
                results["branding"]["footer_color"] = auto.driver.find_element(By.NAME, "FooterColor").get_attribute("value") or ""
                results["branding"]["body_color"] = auto.driver.find_element(By.NAME, "BodyColor").get_attribute("value") or ""
                results["branding"]["background_color"] = auto.driver.find_element(By.NAME, "BackgroundColor").get_attribute("value") or ""
                
                # Image previews
                modal_imgs = auto.driver.find_elements(By.XPATH, "//div[@role='dialog']//img | //div[contains(@class,'modal')]//img")
                img_srcs = [img.get_attribute("src") for img in modal_imgs if img.get_attribute("src")]
                
                if not img_srcs:
                    img_srcs = [img.get_attribute("src") for img in auto.driver.find_elements(By.TAG_NAME, "img") if img.get_attribute("src")]
                
                logo_candidate = ""
                splash_candidate = ""
                for src in img_srcs:
                    if "logo" in src.lower() or "processed" in src.lower():
                        if not logo_candidate: logo_candidate = src
                    elif "splash" in src.lower():
                        if not splash_candidate: splash_candidate = src
                
                if not logo_candidate and len(img_srcs) > 0:
                    logo_candidate = img_srcs[0]
                if not splash_candidate and len(img_srcs) > 1:
                    splash_candidate = img_srcs[1]
                    
                results["branding"]["logo_url"] = logo_candidate
                results["branding"]["splash_url"] = splash_candidate
                
                cancel_btn = auto.driver.find_element(By.XPATH, "//button[contains(text(),'Cancel') or contains(text(),'Discard')]")
                auto.driver.execute_script("arguments[0].click();", cancel_btn)
                time.sleep(1)
                logger.info("  ✓ Identity & Branding extracted successfully")
            except Exception as brand_err:
                logger.warning(f"  ⚠ Failed to extract branding settings: {brand_err}")

            # ── 3. Extract Support Network ────────────────────────────────────
            logger.info("\n→ Extracting Support Network settings...")
            try:
                app_settings_url = getattr(auto, "app_settings_url", getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings"))
                auto.driver.get(f"{app_settings_url}?support-network")
                time.sleep(3)
                
                edit_btn = auto.driver.find_element(By.XPATH, "//button[contains(normalize-space(.),'Edit Details') or contains(normalize-space(.),'Edit Support')]")
                auto.driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", edit_btn)
                time.sleep(2.5)
                
                field_selectors = {
                    "phone": (By.ID, "ContactNumber"),
                    "email": (By.ID, "ContactEmail"),
                    "support_content": (By.ID, "ContactContents"),
                    "privacy_policy": (By.ID, "PrivacyPolicyLink"),
                    "terms_conditions": (By.ID, "TermsConditionLink"),
                    "website": (By.ID, "AboutUsLink")
                }
                
                for key, sel in field_selectors.items():
                    try:
                        val = auto.driver.find_element(sel[0], sel[1]).get_attribute("value") or ""
                        results["support"][key] = val.strip()
                    except Exception as e:
                        results["support"][key] = ""
                
                cancel_btn = auto.driver.find_element(By.XPATH, "//button[contains(text(),'Cancel') or contains(text(),'Discard')]")
                auto.driver.execute_script("arguments[0].click();", cancel_btn)
                time.sleep(1)
                logger.info("  ✓ Support Network extracted successfully")
            except Exception as support_err:
                logger.warning(f"  ⚠ Failed to extract Support Network settings: {support_err}")

            # ── 4. Extract Dashboard Icons ───────────────────────────────────
            logger.info("\n→ Extracting Dashboard Icons...")
            try:
                app_settings_url = getattr(auto, "app_settings_url", getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings"))
                auto.driver.get(f"{app_settings_url}?dashboard-icons")
                time.sleep(4)
                
                table = auto.driver.find_element(By.TAG_NAME, "table")
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                current_user_type = "All"
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) == 1:
                        hdr_text = cells[0].text.strip()
                        match = re.search(r'^([a-zA-Z\s]+?)\s+\d+', hdr_text)
                        if match:
                            current_user_type = match.group(1).strip().title()
                        else:
                            current_user_type = hdr_text.title()
                        continue
                    
                    if len(cells) >= 6:
                        cell_1_text = cells[1].text.strip().replace("\n", " ")
                        color_match = re.search(r'(#[A-Fa-f0-9]{6})', cell_1_text)
                        id_match = re.search(r'ID:\s*([a-zA-Z0-9_\-]+)', cell_1_text)
                        
                        color = color_match.group(1) if color_match else ""
                        icon_id = id_match.group(1) if id_match else ""
                        
                        title = cell_1_text
                        if color:
                            title = title.split(color)[0].strip()
                        elif "ID:" in title:
                            title = title.split("ID:")[0].strip()
                        title = title.replace("", "").strip(" •-")
                        
                        img_url = ""
                        try:
                            img_el = cells[1].find_element(By.TAG_NAME, "img")
                            img_url = img_el.get_attribute("src") or ""
                        except:
                            pass
                            
                        assigned_user = cells[2].text.strip()
                        sequence = cells[3].text.strip()
                        visibility_mode = cells[4].text.strip()
                        status = cells[5].text.strip()
                        
                        results["dashboard_icons"].append({
                            "user_type_section": current_user_type,
                            "display_title": title,
                            "icon_identity": icon_id,
                            "color": color,
                            "assigned_user": assigned_user,
                            "sequence": sequence,
                            "visibility_mode": visibility_mode,
                            "status": status,
                            "image_url": img_url
                        })
                logger.info(f"  ✓ Extracted {len(results['dashboard_icons'])} dashboard icons successfully")
            except Exception as icons_err:
                logger.warning(f"  ⚠ Failed to extract Dashboard Icons: {icons_err}")

            # ── 5. Extract Gifts List (Gifts Management) ──────────────────────
            logger.info("\n→ Extracting Gift Management settings...")
            try:
                app_settings_url = getattr(auto, "app_settings_url", getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings"))
                auto.driver.get(f"{app_settings_url}?gift-management")
                time.sleep(4)
                
                table = auto.driver.find_element(By.TAG_NAME, "table")
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        s_no = cells[0].text.strip()
                        offering = cells[1].text.strip().replace("\n", " ")
                        val_points = cells[2].text.strip().replace("\n", " ")
                        audience = cells[3].text.strip().replace("\n", " ")
                        status_mode = cells[4].text.strip().replace("\n", " ")
                        
                        img_url = ""
                        try:
                            img_el = cells[1].find_element(By.TAG_NAME, "img")
                            img_url = img_el.get_attribute("src") or ""
                        except:
                            pass
                            
                        # Parse Gift Offering
                        gift_id = ""
                        gift_name = offering
                        id_match = re.search(r'#(\d+)', offering)
                        if id_match:
                            gift_id = id_match.group(1)
                            gift_name = offering.split("#" + gift_id)[0].strip()
                            if gift_name.endswith("NA"):
                                gift_name = gift_name[:-2].strip()
                                
                        # Parse Value and Points
                        val_str = val_points
                        points_str = ""
                        if "  " in val_points:
                            parts = val_points.split("  ")
                            val_str = parts[0].strip()
                            points_str = parts[1].strip()
                        elif "Points" in val_points:
                            match = re.search(r'(.*?)\s+(\d+\s+Points)', val_points)
                            if match:
                                val_str = match.group(1).strip()
                                points_str = match.group(2).strip()
                                
                        results["gifts"].append({
                            "s_no": s_no,
                            "gift_name": gift_name,
                            "gift_id": gift_id,
                            "value": val_str,
                            "points": points_str,
                            "audience": audience,
                            "status_mode": status_mode,
                            "image_url": img_url
                        })
                logger.info(f"  ✓ Extracted {len(results['gifts'])} gift offerings successfully")
            except Exception as gifts_err:
                logger.warning(f"  ⚠ Failed to extract Gifts settings: {gifts_err}")

            # ── 6. Extract KYC Rules ──────────────────────────────────────────
            logger.info("\n→ Extracting KYC rules...")
            try:
                app_settings_url = getattr(auto, "app_settings_url", getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings"))
                auto.driver.get(f"{app_settings_url}?kyc-setting")
                time.sleep(4)
                
                kyc_items = ["Aadhaar Card", "PAN Card", "Bank Account Details", "VPA/UPI Details", "QR Code Check", "Admin Approval", "Dashboard Access", "Claim Required"]
                for item in kyc_items:
                    try:
                        el = auto.driver.find_element(By.XPATH, f"//p[text()='{item}']")
                        parent = el.find_element(By.XPATH, "./..")
                        other_ps = [p.text.strip() for p in parent.find_elements(By.TAG_NAME, "p") if p.text.strip() != item]
                        status_text = other_ps[0] if other_ps else "Inactive"
                        badge_text = "DISABLED"
                        try:
                            badge_text = parent.find_element(By.TAG_NAME, "span").text.strip()
                        except:
                            pass
                        results["kyc"].append({
                            "rule_name": item,
                            "policy_type": status_text,
                            "status": badge_text
                        })
                    except Exception as item_err:
                        logger.debug(f"Could not parse KYC item '{item}': {item_err}")
                logger.info(f"  ✓ Extracted {len(results['kyc'])} KYC compliance rules successfully")
            except Exception as kyc_err:
                logger.warning(f"  ⚠ Failed to extract KYC settings: {kyc_err}")

            # ── 7. Extract Claim Settings ─────────────────────────────────────
            logger.info("\n→ Extracting Claim Settings policies...")
            try:
                app_settings_url = getattr(auto, "app_settings_url", getattr(VendorPortalAutomation, "APP_SETTINGS", "https://app.vcqru.com/vendor/app-settings"))
                auto.driver.get(f"{app_settings_url}?claim-setting")
                time.sleep(4)
                
                cbs = auto.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                for cb in cbs:
                    try:
                        card = cb.find_element(By.XPATH, "./ancestor::div[contains(@class,'bg-white') or contains(@class,'bg-card') or contains(@class,'border')][1]")
                        text_lines = [line.strip() for line in card.text.strip().split("\n") if line.strip()]
                        
                        if len(text_lines) >= 3:
                            channel = text_lines[0]
                            p_type = text_lines[1]
                            p_name = text_lines[2]
                        elif len(text_lines) == 2:
                            channel = ""
                            p_type = text_lines[0]
                            p_name = text_lines[1]
                        else:
                            continue
                            
                        is_active = cb.is_selected()
                        results["claims"].append({
                            "channel": channel,
                            "type": p_type,
                            "policy_name": p_name,
                            "status": "Active" if is_active else "Inactive"
                        })
                    except Exception as cb_err:
                        logger.debug(f"Could not parse claim item: {cb_err}")
                logger.info(f"  ✓ Extracted {len(results['claims'])} payout claim policies successfully")
            except Exception as claims_err:
                logger.warning(f"  ⚠ Failed to extract Claim settings: {claims_err}")

            # ── 8. Save Reports (JSON & Excel) ────────────────────────────────
            logs_dir = Path("automation/logs")
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            sanitized_email = re.sub(r'[^a-zA-Z0-9]', '_', email)
            app_name = re.sub(r'[^a-zA-Z0-9]', '_', results["branding"].get("company_name", "App")).strip()
            
            json_file = logs_dir / f"current_settings_{sanitized_email}_{app_name}.json"
            excel_file = logs_dir / f"current_settings_{sanitized_email}_{app_name}.xlsx"
            
            # Save JSON
            with open(json_file, "w", encoding="utf-8") as fh:
                json.dump(results, fh, indent=2)
            logger.info(f"\n✓ JSON report saved to: {json_file}")
            
            # Save Excel
            export_to_excel(results, excel_file)
            logger.info(f"✓ Formatted Excel report saved to: {excel_file}")
            
            # Console summary output
            print()
            print("=" * 60)
            print("          VCQRU VENDOR PORTAL - USER APP SETTINGS")
            print("=" * 60)
            print(f"User:           {results['user_email']}")
            print(f"App/Brand:      {results['branding'].get('company_name', 'N/A')}")
            print(f"Extracted At:   {results['extracted_at']}")
            print("-" * 60)
            print("Identity & Branding:")
            print(f"  App Name:     {results['branding'].get('company_name', 'N/A')}")
            print(f"  Colors:       Header: {results['branding'].get('header_color', 'N/A')}, Bg: {results['branding'].get('background_color', 'N/A')}")
            print("-" * 60)
            print("Support Network:")
            print(f"  Email:        {results['support'].get('email', 'N/A')}")
            print(f"  Phone:        {results['support'].get('phone', 'N/A')}")
            print(f"  Address:      {results['support'].get('support_content', 'N/A')}")
            print("-" * 60)
            print(f"Dashboard Icons ({len(results['dashboard_icons'])} total):")
            # Group icons
            grouped = {}
            for item in results["dashboard_icons"]:
                ut = item["user_type_section"]
                grouped.setdefault(ut, []).append(item)
            for ut, items in grouped.items():
                print(f"  {ut} ({len(items)} icons): {[item['display_title'] for item in items[:4]]} ...")
            print("-" * 60)
            print(f"Gifts ({len(results['gifts'])} offerings):")
            for gift in results["gifts"][:4]:
                print(f"  - {gift['gift_name']} (ID: {gift['gift_id']}, Val: {gift['value']}, Pts: {gift['points']}, Audience: {gift['audience']})")
            print("-" * 60)
            print("KYC & Verification compliance:")
            for k in results["kyc"]:
                print(f"  - {k['rule_name']}: {k['policy_type']} [{k['status']}]")
            print("-" * 60)
            print("Payout Claim Policies:")
            for cl in results["claims"]:
                print(f"  - {cl['policy_name']} ({cl['type']}): {cl['status']}")
            print("=" * 60)
            print()
            return True

    except Exception as e:
        logger.error(f"Settings analysis encountered a fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
