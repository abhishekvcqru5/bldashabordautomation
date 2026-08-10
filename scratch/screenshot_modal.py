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
            logger.error("Login failed!")
            return
            
        time.sleep(2)
        logger.info("Navigating to Product Management...")
        if not navigate_to_product_mgmt(automation, wait):
            logger.error("Navigation failed!")
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
        
        logger.info("Taking modal screenshot...")
        # Make sure directory exists
        scratch_dir = Path("scratch")
        scratch_dir.mkdir(exist_ok=True)
        driver.save_screenshot("scratch/modal_screenshot.png")
        
        # Let's inspect the file inputs and their parent structure
        modal = driver.find_element(By.XPATH, "//div[contains(@class,'fixed') and contains(@class,'inset-0')]")
        inputs = modal.find_elements(By.XPATH, ".//input")
        logger.info(f"Found {len(inputs)} inputs in modal:")
        for idx, inp in enumerate(inputs):
            logger.info(f"Input {idx+1}: type={inp.get_attribute('type')}, id={inp.get_attribute('id')}, name={inp.get_attribute('name')}")
            
        # Get modal HTML for inspection
        modal_html = modal.get_attribute("outerHTML")
        Path("scratch/modal.html").write_text(modal_html, encoding="utf-8")
        logger.info("Saved modal HTML to scratch/modal.html")

if __name__ == "__main__":
    main()
