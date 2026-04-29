import os
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_automation():
    options = Options()
    options.add_argument("--headless") # Required for GitHub Actions
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    
    try:
        # 1. Load Naukri to set the domain
        driver.get("https://www.naukri.com/nlogin/login")
        
        # 2. Inject Cookies
        cookies = json.loads(os.getenv('NAUKRI_COOKIES'))
        for cookie in cookies:
            driver.add_cookie(cookie)
        
        # 3. Forced Refresh (Profile Update)
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(5)
        
        # Click Edit Headline
        edit_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(@class, 'editIcon')]")))
        edit_btn.click()
        
        # Add a space to the headline to trigger a "Change" and Save
        headline_field = driver.find_element(By.ID, "resumeHeadlineTxt")
        current_text = headline_field.get_attribute("value")
        headline_field.clear()
        # Toggle a dot at the end to force a refresh
        new_text = current_text.strip(".") + ("." if not current_text.endswith(".") else "")
        headline_field.send_keys(new_text)
        
        driver.find_element(By.XPATH, "//button[text()='Save']").click()
        print("✅ Forced Refresh: Resume Headline Updated.")
        time.sleep(3)

        # 4. Automate Job Applies (0-2 Years)
        search_url = "https://www.naukri.com/developer-jobs?experience=0&experience=1&experience=2"
        driver.get(search_url)
        time.sleep(5)
        
        job_cards = driver.find_elements(By.CLASS_NAME, "srp-jobtuple-wrapper")
        applied_count = 0
        
        for card in job_cards[:5]: # Apply to first 5 to stay safe
            try:
                apply_btn = card.find_element(By.XPATH, ".//button[text()='Apply' or text()='Easy Apply']")
                apply_btn.click()
                applied_count += 1
                time.sleep(random.uniform(2, 5)) # Human-like delay
                print(f"🚀 Applied to job {applied_count}")
            except:
                continue

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
