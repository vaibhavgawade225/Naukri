import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium_stealth import stealth

# --- PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", "expected_ctc": "5", "notice_period": "15", "experience": "2"
}

def handle_questionnaire(driver, job_idx):
    """Positive-First logic: specifically looks for 'Yes' and fills missing gaps."""
    try:
        time.sleep(5)
        # 1. Radio Buttons: Priority for 'Yes'
        radio_groups = {}
        for r in driver.find_elements(By.XPATH, "//input[@type='radio']"):
            name = r.get_attribute("name")
            if name:
                if name not in radio_groups: radio_groups[name] = []
                radio_groups[name].append(r)

        for name, buttons in radio_groups.items():
            selected = False
            for btn in buttons:
                # Check label text, ID, and Value for "Yes"
                btn_id = btn.get_attribute("id")
                label_text = ""
                try:
                    if btn_id: label_text = driver.find_element(By.XPATH, f"//label[@for='{btn_id}']").text.lower()
                    if not label_text: label_text = btn.find_element(By.XPATH, "./..").text.lower()
                except: pass
                
                if any(pos in label_text for pos in ["yes", "ready", "willing", "relocate", "agree"]):
                    driver.execute_script("arguments[0].click();", btn)
                    selected = True; break
            if not selected: driver.execute_script("arguments[0].click();", buttons[0])

        # 2. Text/Number Inputs: Multi-context search
        for field in driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea"):
            ctx = (field.get_attribute("placeholder") or "").lower()
            try: ctx += " " + field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
            except: pass
            
            if "current" in ctx and "ctc" in ctx: field.send_keys(MY_PROFILE_DATA["current_ctc"])
            elif "expected" in ctx and "ctc" in ctx: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
            elif "notice" in ctx: field.send_keys(MY_PROFILE_DATA["notice_period"])
            elif "experience" in ctx or "years" in ctx: field.send_keys(MY_PROFILE_DATA["experience"])
            elif not field.get_attribute("value"): field.send_keys("2") # Safety fallback

        # 3. Submit
        driver.save_screenshot(f"debug_quest_filled_{job_idx}.png")
        for btn_text in ["Submit", "Save", "Apply"]:
            btns = driver.find_elements(By.XPATH, f"//button[contains(text(), '{btn_text}')] | //span[text()='{btn_text}']/..")
            for b in btns:
                if b.is_displayed():
                    driver.execute_script("arguments[0].click();", b)
                    time.sleep(3); return True
    except: return False

def run_automation():
    print("🚀 Starting Human-Flow Stealth Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # STEP 1: Land on Home & Inject
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        driver.refresh()
        time.sleep(5)

        # STEP 2: UI-Based Search (Beats the direct-link Firewall)
        print("🔍 Searching via UI...")
        try:
            search_input = driver.find_element(By.CLASS_NAME, "suggestor-input")
            search_input.send_keys("Java Developer")
            search_input.send_keys(Keys.ENTER)
        except:
            # Fallback to direct search if UI fails, but with a referer
            driver.get("https://www.naukri.com/java-developer-jobs-in-india?experience=1")
            
        time.sleep(10)
        driver.save_screenshot("debug_01_search_results.png")

        # STEP 3: Extract & Apply
        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(links)} jobs.")

        applied = 0
        for idx, link in enumerate(links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                # Check for "Access Denied" on job page
                if "access denied" in driver.page_source.lower():
                    print(f"⚠️ Job {idx+1} blocked. Skipping...")
                    continue

                apply_btn = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btn and apply_btn[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btn[0])
                    print(f"✅ Applying to Job {idx+1}...")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break
            except: continue

        print(f"🏁 Done. Total: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
