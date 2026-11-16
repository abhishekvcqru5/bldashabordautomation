import os
import sys
import json
from pathlib import Path
from selenium.webdriver.common.by import By

from dashboard_automation import VendorPortalAutomation
from brand_setting import BrandSettingAutomation

email = os.getenv("VENDOR_EMAIL", "ambicacableco1985@gmail.com")
pwd = os.getenv("VENDOR_PASSWORD", "Ambica123@")

print(f"Logging in with {email}...")
with VendorPortalAutomation(email, pwd, headless=True) as auto:
    if auto.login():
        brand = BrandSettingAutomation(auto.driver)
        if brand.navigate():
            print("Modal opened successfully!")
            
            # Inspect inputs
            data = auto.driver.execute_script("""
                var res = { inputs: [], modalHtml: "" };
                var comp = document.querySelector('input[name="CompanyName"]');
                var modal = comp ? (comp.closest('form') || comp.closest('div.fixed') || comp.parentElement.parentElement) : document.body;
                
                res.modalHtml = modal.outerHTML.substring(0, 4000);
                
                var fileInputs = modal.querySelectorAll('input[type="file"]');
                for (var i = 0; i < fileInputs.length; i++) {
                    var fi = fileInputs[i];
                    res.inputs.push({
                        idx: i,
                        accept: fi.accept,
                        name: fi.name,
                        id: fi.id,
                        display: window.getComputedStyle(fi).display,
                        visibility: window.getComputedStyle(fi).visibility,
                        parentText: fi.parentElement ? fi.parentElement.innerText.substring(0, 100).replace(/\\s+/g, ' ') : ''
                    });
                }
                return res;
            """)
            
            print("File inputs in modal:", json.dumps(data["inputs"], indent=2))
            with open("modal_inspect.html", "w", encoding="utf-8") as f:
                f.write(data["modalHtml"])
            print("Saved modal HTML to modal_inspect.html")
        else:
            print("Failed to navigate to modal")
    else:
        print("Login failed")
