import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3",      
    "expected_ctc": "5",     
    "notice_period": "15",          
    "experience": "2",
    "relocation": "Yes"
}

def inject_cookies_and_verify(driver):
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    if not cookie_raw:
        print("❌ CRITICAL: NAUKRI_COOKIE secret is missing.")
        return False
    for item in cookie_raw.split(';'):
        if '=' in item:
            try:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})
            except: continue
    time.sleep(3)
    driver.refresh()
    time.sleep(5)
    if "login" in driver.current_url.lower():
        print("❌ CRITICAL: Cookie expired.")
        return False
    return True

def handle_questionnaire(driver, job_idx):
    """Ironclad logic for all input types with visual debugging."""
    try:
        time.sleep(5) # Let the popup fully load
        
        # 📸 DEBUG 1: Take a picture of the blank form
        driver.save_screenshot(f"02_job_{job_idx}_quest_BLANK.png")
        print(f"📝 Questionnaire detected for Job {job_idx}. Processing...")

        # 1. Text & Number Fields
        for field in driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea"):
            try:
                context = (field.get_attribute("placeholder") or field.find_element(By.XPATH, "./ancestor::div[1]").text).lower()
                if "current" in context and "ctc" in context: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected" in context and "ctc" in context: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice" in context: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in context or "years" in context: field.send_keys(MY_PROFILE_DATA["experience"])
                else: field.send_keys("2") # Safe fallback for unknown number fields
            except: continue

        # 2. Dropdowns (<select>) - NEW!
        for select_box in driver.find_elements(By.XPATH, "//select"):
            try:
                # Force select the second option (index 1) to avoid the "Select..." placeholder
                driver.execute_script("arguments[0].selectedIndex = 1; arguments[0].dispatchEvent(new Event('change'));", select_box)
            except: continue

        # 3. Radio Buttons (First Option)
        radio_names = set([r.get_attribute("name") for r in driver.find_elements(By.XPATH, "//input[@type='radio']") if r.get_attribute("name")])
        for name in radio_names:
            try:
                btns = driver.find_elements(By.NAME, name)
                driver.execute_script("arguments[0].click();", btns[0])
            except: continue

        # 4. Checkboxes - NEW!
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        if checkboxes:
            try:
                # Just click the first checkbox available (often used for 'Skills')
                if not checkboxes[0].is_selected():
                    driver.execute_script("arguments[0].click();", checkboxes[0])
            except: pass

        # 📸 DEBUG 2: Take a picture of the filled form BEFORE clicking submit
        driver.save_screenshot(f"03_job_{job_idx}_quest_FILLED.png")

        # 5. Aggressive Submit 
        for xpath in [
            "//button[contains(text(), 'Submit')]", 
            "//button[contains(text(), 'Save')]", 
            "//button[text()='Apply']",
            "//span[contains(text(), 'Submit')]/ancestor::button"
        ]:
            for btn in driver.find_elements(By.XPATH, xpath):
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(4)
                    print(f"✅ Questionnaire for Job {job_idx} submitted.")
                    return
    except Exception as e:
        print(f"⚠️ Questionnaire handler issue: {str(e)[:50]}")

def run_automation():
    print("🚀 Starting Clean Slate Automation...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        driver.get("https://www.naukri.com/recruiters-in-india") 
        time.sleep(5)
        
        if not inject_cookies_and_verify(driver): return

        search_url = "https://www.naukri.com/java-developer-jobs-in-india?experience=1&sort=f"
        driver.get(search_url)
        time.sleep(12)
        driver.save_screenshot("01_search_page_status.png")

        if "access denied" in driver.page_source.lower() or "403" in driver.title: return

        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        applied_count = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']")
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"⏳ Clicked Apply on Job {idx+1}")
                    
                    # Passed idx+1 so screenshots are numbered correctly
                    handle_questionnaire(driver, idx+1)
                    
                    driver.save_screenshot(f"04_applied_job_FINAL_{idx+1}.png")
                    applied_count += 1

                if applied_count >= 5: break
                time.sleep(random.uniform(4, 7)) 
                
            except Exception as e: continue

        print(f"🏁 Execution Complete. Total applied: {applied_count}")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
