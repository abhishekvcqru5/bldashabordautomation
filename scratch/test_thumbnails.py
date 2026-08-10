import sys
from pathlib import Path
import logging
import time

# Add automation folder to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automation"))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dashboard_automation import VendorPortalAutomation
from product_management_upload import is_row_thumbnail_broken, navigate_to_product_mgmt

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
            logger.error("Login failed!")
            return
            
        time.sleep(2)
        logger.info("Navigating to Product Management...")
        if not navigate_to_product_mgmt(automation, wait):
            logger.error("Navigation failed!")
            return
            
        logger.info("Scanning page 1...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table > tbody > tr")))
        time.sleep(3)
        
        rows = driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")
        logger.info(f"Found {len(rows)} rows on page 1")
        
        for idx, row in enumerate(rows):
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 2:
                continue
            product_name = cols[1].text.replace("\n", " ").strip()
            
            # Find img element inside row
            img_src = "No Image Tag"
            imgs = row.find_elements(By.CSS_SELECTOR, "td img")
            if imgs:
                img_src = imgs[0].get_attribute("src") or "Empty Src"
                
            broken = is_row_thumbnail_broken(driver, row)
            logger.info(f"Row {idx+1}: {product_name} | Broken: {broken} | Src: {img_src[:120]}")

if __name__ == "__main__":
    main()
