import os
import time
import random
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
    """Auto-answers questions using first-option logic for unknown fields."""
    try:
        time.sleep(4)
        # 1. Text Fields
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        for field in inputs:
            try:
                context = (field.find_element(By.XPATH, "./..").text + " " + (field.get_attribute("placeholder") or "")).lower()
                if "current ctc" in context: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected ctc" in context: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice period" in context: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in context: field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        # 2. Radio Groups (First Option/Relocation Logic)
        radio_groups = {}
        for r in driver.find_elements(By.XPATH, "//input[@type='radio']"):
            name = r.get_attribute("name")
            if name not in radio_groups: radio_groups[name] = []
            radio_groups[name].append(r)

        for name, buttons in radio_groups.items():
            try:
                group_text = buttons[0].find_element(By.XPATH, "./../../..").text.lower()
                if "reloc" in group_text:
                    for b in buttons:
                        if "yes" in b.get_attribute("value").lower() or "yes" in b.find_element(By.XPATH, "..").text.lower():
                            driver.execute_script("arguments[0].click();", b)
                            break
                else:
                    driver.execute_script("arguments[0].click();", buttons[0])
            except: continue

        # 3. Submit
        for s in ["//button[contains(text(), 'Submit')]", "//button[contains(text(), 'Save')]", "//button[contains(text(), 'Apply')]"]:
            btn = driver.find_elements(By.XPATH, s)
            if btn and btn[0].is_displayed():
                driver.execute_script("arguments[0].click();", btn[0])
                time.sleep(3)
                break
    except: pass

def run_automation():
    print("🚀 Initializing Ultra-Stealth Mode...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Rotating User Agent slightly
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # STEP 1: Land on a non-search page first to "Warm Up" the session
        print("🏠 Warming up on Home Page...")
        driver.get("https://www.naukri.com/recruiters-in-india") 
        time.sleep(random.uniform(5, 8))
        
        # Inject Cookies
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # STEP 2: Navigate to search with a "Human" Referrer
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        print(f"🔍 Navigating to Search via indirect link...")
        driver.get(search_url)
        
        # Mandatory Human-Simulated Wait
        time.sleep(random.uniform(15, 20))
        driver.execute_script("window.scrollTo(0, 400);")
        driver.save_screenshot("search_results_check.png")

        if "access denied" in driver.page_source.lower():
            print("🚫 Firewall block still active. Attempting one hard refresh...")
            driver.refresh()
            time.sleep(15)

        # STEP 3: Process Jobs
        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:15]):
            try:
                driver.get(link)
                time.sleep(random.uniform(10, 15))
                
                if "access denied" in driver.page_source.lower():
                    print(f"⚠️ Job {idx+1} blocked. Skipping...")
                    continue

                apply_btn = driver.find_elements(By.XPATH, "//button[text()='Apply'] | //button[contains(text(), 'Apply')]")
                if apply_btn and apply_btn[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btn[0])
                    print(f"✅ Clicked Apply on Job {idx+1}")
                    handle_questions(driver)
                    driver.save_screenshot(f"job_{idx+1}_applied.png")
                    applied += 1
                
                if applied >= 5: break
                time.sleep(random.uniform(5, 10))
            except: continue

        print(f"🏁 Final Status: {applied} jobs applied.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
