import os
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

# --- YOUR DATA CABINET ---
# The bot uses these to answer questions positively
MY_PROFILE_DATA = {
    "current_ctc": "3,00,000",      
    "expected_ctc": "5,00,000",     
    "notice_period": "15",          # Number of days
    "experience": "2",
    "relocation": "Yes"             # Always says 'Yes' to stay in the running
}

def handle_questions(driver):
    """Detects and fills manual questions like CTC, Notice Period, etc."""
    try:
        time.sleep(3) # Wait for the popup animation
        
        # 1. Identify all input fields on the current view
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        page_source = driver.page_source.lower()

        for field in inputs:
            # Get the parent text or placeholder to know what the question is
            parent_text = ""
            try:
                parent_text = field.find_element(By.XPATH, "./..").text.lower()
                placeholder = field.get_attribute("placeholder").lower()
                combined_context = parent_text + " " + placeholder
            except:
                combined_context = ""

            # Respond to specific questions
            if any(k in combined_context for k in ["current ctc", "fixed ctc"]):
                field.send_keys(MY_PROFILE_DATA["current_ctc"])
            elif any(k in combined_context for k in ["expected ctc", "salary expectation"]):
                field.send_keys(MY_PROFILE_DATA["expected_ctc"])
            elif any(k in combined_context for k in ["notice period", "how soon"]):
                field.send_keys(MY_PROFILE_DATA["notice_period"])
            elif any(k in combined_context for k in ["experience", "years"]):
                field.send_keys(MY_PROFILE_DATA["experience"])

        # 2. Handle Relocation (Radio Buttons)
        if "reloc" in page_source:
            yes_radios = driver.find_elements(By.XPATH, "//input[@type='radio' and (contains(@value, 'Yes') or contains(@value, '1'))]")
            for radio in yes_radios:
                driver.execute_script("arguments[0].click();", radio)

        # 3. Finalize - Look for the Submit/Apply button inside the popup
        submit_selectors = [
            "//button[text()='Submit']", 
            "//button[contains(text(), 'Submit')]",
            "//button[contains(text(), 'Save')]",
            "//button[contains(text(), 'Apply and')]"
        ]
        
        for s in submit_selectors:
            submit_btn = driver.find_elements(By.XPATH, s)
            if submit_btn and submit_btn[0].is_displayed():
                driver.execute_script("arguments[0].click();", submit_btn[0])
                print("✅ Questionnaire filled and submitted.")
                time.sleep(3)
                return True
                
    except Exception as e:
        print(f"⚠️ Questionnaire handler skipped: {str(e)[:50]}")
    return False

def run_automation():
    print("🚀 Starting Stealth Java Apply + Auto-Question Filler...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Handshake
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # Step 2: Search
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)
        
        # Extract direct links to prevent "stale" cards
        links = [el.get_attribute('href') for el in driver.find_elements(By.XPATH, "//a[@class='title ']")[:15]]
        print(f"Found {len(links)} jobs. Starting targeted applications...")

        applied_count = 0
        for idx, link in enumerate(links):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))

                # Handle Access Denied
                if "access denied" in driver.page_source.lower():
                    driver.refresh()
                    time.sleep(10)

                # Find Main Apply Button
                apply_xpath = "//button[text()='Apply'] | //button[contains(text(), 'Apply')] | //button[@id='apply-button']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"⏳ Clicked Apply on Job {idx+1}. Checking for popups...")
                    
                    # RUN QUESTION HANDLER
                    handle_questions(driver)
                    
                    driver.save_screenshot(f"applied_job_{idx+1}.png")
                    applied_count += 1
                
                if applied_count >= 5: break
                time.sleep(random.uniform(4, 7))

            except Exception:
                continue

        print(f"🏁 Final Status: {applied_count} jobs applied with auto-answers.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
