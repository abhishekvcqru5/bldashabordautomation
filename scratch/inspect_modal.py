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
        time.sleep(1)
        
        edit_span = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[text()='Edit Profile' or contains(text(), 'Edit Profile')]")
        ))
        driver.execute_script("arguments[0].click();", edit_span)
        time.sleep(2)
        
        # Find all divs containing file inputs
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        logger.info(f"Found {len(file_inputs)} file inputs on page")
        for idx, inp in enumerate(file_inputs):
            parent = inp.find_element(By.XPATH, "..")
            logger.info(f"File Input {idx+1}: outerHTML={inp.get_attribute('outerHTML')}")
            logger.info(f"File Input {idx+1} Parent: outerHTML={parent.get_attribute('outerHTML')[:300]}")
            
        # Let's see if there are any other inputs or text fields in the modal
        modal_container = driver.find_element(By.XPATH, "//div[contains(@class,'fixed') and .//input[@type='file']]")
        logger.info(f"Modal Container tag: {modal_container.tag_name}, class: {modal_container.get_attribute('class')}")
        Path("scratch/real_modal.html").write_text(modal_container.get_attribute("outerHTML"), encoding="utf-8")
        logger.info("Saved real modal HTML to scratch/real_modal.html")

if __name__ == "__main__":
    main()
