from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opts = Options()
opts.add_argument("--headless=new")
driver = webdriver.Chrome(options=opts)

try:
    driver.get("https://www.vcqru.com/loginVcqru.aspx")
    time.sleep(5)
    print("--- Page Source Snippet ---")
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        print(f"ID: {inp.get_attribute('id')}, Name: {inp.get_attribute('name')}, Type: {inp.get_attribute('type')}, Placeholder: {inp.get_attribute('placeholder')}")
    
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        print(f"Button Text: {btn.text}, ID: {btn.get_attribute('id')}")
    
    # Check for "Vendor" radio/button
    elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Vendor')]")
    for el in elements:
        print(f"Vendor Element: {el.tag_name}, ID: {el.get_attribute('id')}")

finally:
    driver.quit()
