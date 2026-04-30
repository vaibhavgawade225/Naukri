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

def handle_questionnaire(driver, job_idx):
    """
    Highly aggressive handler:
    1. Answers 'Yes' to relocation/willingness questions.
    2. Fills numbers for CTC/Notice.
    3. Selects the first non-placeholder option in dropdowns.
    """
    try:
        time.sleep(5) 
        driver.save_screenshot(f"debug_02_job_{job_idx}_BEFORE.png")
        print(f"📝 Handling Questionnaire for Job {job_idx}...")

        # 1. HANDLE RADIO BUTTONS (Relocation/Yes-No Priority)
        # We group them to make sure we answer each question once
        radio_groups = {}
        for r in driver.find_elements(By.XPATH, "//input[@type='radio']"):
            name = r.get_attribute("name")
            if name not in radio_groups: radio_groups[name] = []
            radio_groups[name].append(r)

        for name, buttons in radio_groups.items():
            try:
                selected = False
                # Search for a 'Positive' button in this group (Yes, Ready, Willing)
                for btn in buttons:
                    label_text = ""
                    try:
                        # Try finding label by 'for' attribute or parent text
                        btn_id = btn.get_attribute("id")
                        if btn_id:
                            label = driver.find_elements(By.XPATH, f"//label[@for='{btn_id}']")
                            if label: label_text = label[0].text.lower()
                        if not label_text:
                            label_text = btn.find_element(By.XPATH, "./..").text.lower()
                    except: pass

                    if any(pos in label_text for pos in ["yes", "ready", "willing", "relocate", "agree"]):
                        driver.execute_script("arguments[0].click();", btn)
                        selected = True
                        break
                
                # Fallback: If no 'Yes' found, click the first one
                if not selected:
                    driver.execute_script("arguments[0].click();", buttons[0])
            except: continue

        # 2. HANDLE TEXT/NUMBER INPUTS
        for field in driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea"):
            try:
                # Find context from label or parent div
                context = (field.get_attribute("placeholder") or "").lower()
                try:
                    context += " " + field.find_element(By.XPATH, "./ancestor::div[contains(@class, 'ques') or contains(@class, 'form')][1]").text.lower()
                except: pass

                if "current" in context and "ctc" in context:
                    field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected" in context and "ctc" in context:
                    field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice" in context:
                    field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in context or "years" in context:
                    field.send_keys(MY_PROFILE_DATA["experience"])
                else:
                    # Fallback for unknown mandatory fields: provide a positive number
                    if not field.get_attribute("value"):
                        field.send_keys("2")
            except: continue

        # 3. HANDLE DROPDOWNS (Select the first real option)
        for select_box in driver.find_elements(By.XPATH, "//select"):
            try:
                driver.execute_script("arguments[0].selectedIndex = 1; arguments[0].dispatchEvent(new Event('change'));", select_box)
            except: continue

        # 📸 PRE-SUBMIT CHECK
        driver.save_screenshot(f"debug_03_job_{job_idx}_FILLED.png")

        # 4. AGGRESSIVE SUBMIT
        submit_selectors = [
            "//button[contains(text(), 'Submit')]", 
            "//button[contains(text(), 'Save')]", 
            "//button[text()='Apply']",
            "//div[contains(@class, 'footer')]//button",
            "//span[contains(text(), 'Submit')]/ancestor::button"
        ]
        
        for xpath in submit_selectors:
            btns = driver.find_elements(By.XPATH, xpath)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"✅ Clicked Submit for Job {job_idx}")
                    time.sleep(3)
                    return True
    except Exception as e:
        print(f"⚠️ Handler failed: {str(e)[:50]}")
    return False

# --- MAIN RUNNER (Optimized for Login persistence) ---
def run_automation():
    print("🚀 Starting Refined Question-Handling Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Establish Session
        driver.get("https://www.naukri.com/recruiters-in-india")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})
        
        driver.get("https://www.naukri.com/java-developer-jobs-in-india?experience=1&sort=f")
        time.sleep(10)
        driver.save_screenshot("debug_01_search_page.png")

        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"⏳ Processing Job {idx+1}...")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break
                time.sleep(random.uniform(4, 6))
            except: continue

        print(f"🏁 Done. Applied to {applied} jobs.")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
