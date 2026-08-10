import sys
from pathlib import Path
import logging
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automation"))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dashboard_automation import VendorPortalAutomation
from product_management_upload import navigate_to_product_mgmt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    email = "ambicacableco1985@gmail.com"
    password = "Ambica123@"
    
    with VendorPortalAutomation(email, password, headless=True) as automation:
        driver = automation.driver
        wait = WebDriverWait(driver, 20)
        
        logger.info("Logging in...")
        if not automation.login():
            return
            
        time.sleep(2)
        logger.info("Navigating to Product Management...")
        if not navigate_to_product_mgmt(automation, wait):
            return
            
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr")))
        time.sleep(2)
        
        rows = driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
        logger.info(f"Found {len(rows)} rows")
        
        # Dump HTML of first 3 rows
        for idx in range(min(5, len(rows))):
            row = rows[idx]
            logger.info(f"\n--- ROW {idx+1} HTML ---")
            logger.info(row.get_attribute("outerHTML")[:2000])

if __name__ == "__main__":
    main()
