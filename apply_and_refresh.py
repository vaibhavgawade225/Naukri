import os
import time
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# --- YOUR DATA CABINET ---
MY_PROFILE_DATA = {
    "experience": "2",            
    "current_ctc": "3,00,000",      
    "expected_ctc": "5,00,000",     
    "notice_period": "7",          
    "current_location": "Pune",
    "relocation": "Yes"
}

def handle_access_denied(driver):
    """Detects Access Denied page and refreshes to bypass."""
    for i in range(2): # Try refreshing twice
        if "access denied" in driver.page_source.lower() or "403" in driver.title:
            print(f"Access Denied detected. Refresh attempt {i+1}...")
            time.sleep(random.uniform(5, 8))
            driver.refresh()
            time.sleep(10)
        else:
            return True
    return False

def answer_questions(driver):
    """Smart-answer logic for questionnaires."""
    try:
        wrappers = driver.find_elements(By.XPATH, "//div[contains(@class, 'question')] | //li[contains(@class, 'item')]")
        for wrapper in wrappers:
            text = wrapper.text.lower()
            inputs = wrapper.find_elements(By.XPATH, ".//input | .//select | .//textarea")
            if not inputs: continue
            
            if "current ctc" in text: inputs[0].send_keys(MY_PROFILE_DATA["current_ctc"])
            elif "expected ctc" in text: inputs[0].send_keys(MY_PROFILE_DATA["expected_ctc"])
            elif "notice period" in text: inputs[0].send_keys(MY_PROFILE_DATA["notice_period"])
            elif "relocate" in text:
                choice = MY_PROFILE_DATA["relocation"].lower()
                for rb in wrapper.find_elements(By.XPATH, ".//input[@type='radio']"):
                    if choice in rb.get_attribute("value").lower() or choice in rb.find_element(By.XPATH, "..").text.lower():
                        driver.execute_script("arguments[0].click();", rb)
                        break
        
        submit = driver.find_elements(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Save')]")
        if submit: submit[0].click()
    except: pass

def run_automation():
    print("Starting Smart-Apply with Access Bypass...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # Sort by latest (Freshness)
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)
        
        # Check if search page is blocked
        handle_access_denied(driver)

        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        applied_count = 0

        for i, card in enumerate(job_cards[:7]):
            try:
                # Randomized human delay before opening each job
                time.sleep(random.uniform(3, 6))
                
                title_link = card.find_element(By.XPATH, ".//a[@class='title ']")
                title_link.click()
                time.sleep(6)
                
                driver.switch_to.window(driver.window_handles[-1])
                
                # CRITICAL: Check for Access Denied on the Job Page
                if not handle_access_denied(driver):
                    print(f"Skipping Job {i+1}: Blocked by Access Denied.")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

                driver.save_screenshot(f"job_{i+1}_loaded.png")
                
                apply_btn = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']"))
                )
                apply_btn.click()
                time.sleep(5)

                # Handle questionnaire
                if "question" in driver.page_source.lower():
                    answer_questions(driver)
                    time.sleep(3)

                print(f"Job {i+1}: Success.")
                applied_count += 1
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                print(f"Job {i+1} Failed: {str(e)[:40]}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        print(f"FINISHED: Total Applied: {applied_count}")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
