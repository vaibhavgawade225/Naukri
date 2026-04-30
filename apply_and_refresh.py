import os
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

# --- YOUR DATA CABINET ---
MY_PROFILE_DATA = {
    "current_ctc": "3,00,000",      
    "expected_ctc": "5,00,000",     
    "notice_period": "15",          
    "experience": "2",
    "relocation": "Yes"
}

def handle_questions(driver):
    """Detects and fills questions. Defaults to first option for unknown radio buttons."""
    try:
        time.sleep(3)
        # 1. Handle Text Inputs
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        for field in inputs:
            try:
                context = field.find_element(By.XPATH, "./..").text.lower() + " " + (field.get_attribute("placeholder") or "").lower()
                
                if any(k in context for k in ["current ctc", "fixed ctc"]):
                    field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif any(k in context for k in ["expected ctc", "salary"]):
                    field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif any(k in context for k in ["notice period", "how soon"]):
                    field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif any(k in context for k in ["experience", "years"]):
                    field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        # 2. Handle Radio Buttons (Relocation + Random/First Option)
        # Group radio buttons by their 'name' attribute to select one per question
        radio_groups = {}
        all_radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        
        for radio in all_radios:
            name = radio.get_attribute("name")
            if name not in radio_groups:
                radio_groups[name] = []
            radio_groups[name].append(radio)

        for name, buttons in radio_groups.items():
            try:
                # Check if this group is about relocation
                group_context = buttons[0].find_element(By.XPATH, "./../../..").text.lower()
                
                if "reloc" in group_context:
                    # Select 'Yes' if available
                    for b in buttons:
                        if "yes" in b.get_attribute("value").lower() or "yes" in b.find_element(By.XPATH, "..").text.lower():
                            driver.execute_script("arguments[0].click();", b)
                            break
                else:
                    # Positive fallback: Select the first radio button for any other random question
                    driver.execute_script("arguments[0].click();", buttons[0])
            except: continue

        # 3. Submit the questionnaire
        submit_selectors = ["//button[contains(text(), 'Submit')]", "//button[contains(text(), 'Save')]", "//button[contains(text(), 'Apply and')]"]
        for s in submit_selectors:
            submit_btn = driver.find_elements(By.XPATH, s)
            if submit_btn and submit_btn[0].is_displayed():
                driver.execute_script("arguments[0].click();", submit_btn[0])
                print("✅ Filled questions (including random fallbacks) and submitted.")
                time.sleep(3)
                break
    except Exception as e:
        print(f"⚠️ Question handler error: {str(e)[:50]}")

def run_automation():
    print("🚀 Starting Stealth Java Apply with Random-Question Logic...")
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

        # Step 2: Search with Stealth
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(random.uniform(12, 15)) 
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        driver.save_screenshot("search_results_check.png") 

        job_elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
        links = [el.get_attribute('href') for el in job_elements if el.get_attribute('href')]
        
        if not links:
            print("⚠️ No jobs found. Checking if page is blocked...")
            if "access denied" in driver.page_source.lower(): print("🚫 Blocked by Naukri Firewall.")
            return

        print(f"Found {len(links)} jobs. Applying...")

        applied_count = 0
        for idx, link in enumerate(links[:15]):
            try:
                driver.get(link)
                time.sleep(random.uniform(8, 12))

                if "access denied" in driver.page_source.lower():
                    driver.refresh()
                    time.sleep(10)

                apply_xpath = "//button[text()='Apply'] | //button[contains(text(), 'Apply')] | //button[@id='apply-button']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"⏳ Applied to Job {idx+1}. Filling questions...")
                    handle_questions(driver)
                    driver.save_screenshot(f"applied_job_{idx+1}.png")
                    applied_count += 1
                
                if applied_count >= 5: break
                time.sleep(random.uniform(5, 8))
            except: continue

        print(f"🏁 Final Status: {applied_count} jobs processed.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
