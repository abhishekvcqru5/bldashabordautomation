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
        
        # Click action button on first row
        row = driver.find_elements(By.CSS_SELECTOR, "table > tbody > tr")[0]
        cols = row.find_elements(By.TAG_NAME, "td")
        product_name = cols[1].text.replace("\n", " ").strip()
        logger.info(f"Clicking Action for row: {product_name}")
        
        action_btn = cols[-1].find_element(By.TAG_NAME, "button")
        driver.execute_script("arguments[0].click();", action_btn)
        time.sleep(1.5)
        
        # Find all dropdown links/spans
        # Usually they are inside a menu container
        menu_items = driver.find_elements(By.XPATH, "//div[contains(@class,'absolute') or contains(@class,'dropdown')]//button | //div[contains(@class,'absolute') or contains(@class,'dropdown')]//a | //div[contains(@class,'absolute') or contains(@class,'dropdown')]//span")
        logger.info(f"Found {len(menu_items)} potential menu elements:")
        for idx, item in enumerate(menu_items):
            text = item.text.strip()
            if text:
                logger.info(f"Menu Item {idx+1}: tag={item.tag_name}, text={text}")

if __name__ == "__main__":
    main()
