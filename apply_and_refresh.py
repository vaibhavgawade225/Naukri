import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

# --- PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", "expected_ctc": "5", "notice_period": "15", "experience": "2"
}

def handle_questionnaire(driver, job_idx):
    """
    Handles multi-step questionnaires. 
    Answers 'Yes' to text-based willingness questions.
    """
    try:
        # Loop up to 6 times to handle multiple consecutive questions
        for step in range(1, 7):
            time.sleep(4) 
            
            # 1. Identify the 'Save' or 'Submit' button for this step
            save_button = None
            for xpath in ["//button[text()='Save']", "//button[contains(text(), 'Save')]", "//button[contains(text(), 'Submit')]"]:
                btns = driver.find_elements(By.XPATH, xpath)
                for b in btns:
                    if b.is_displayed():
                        save_button = b; break
                if save_button: break

            if not save_button:
                print(f"✅ Job {job_idx}: No more questions found.")
                break

            # 📸 Debug: What does the bot see at this step?
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_START.png")

            # 2. Handle Text Boxes / Textareas (Specifically for 'Yes' type answers)
            inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
            for field in inputs:
                try:
                    # Get context from placeholder or parent text
                    ctx = (field.get_attribute("placeholder") or "").lower()
                    try:
                        ctx += " " + field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                    except: pass

                    if "current" in ctx and "ctc" in ctx:
                        field.send_keys(MY_PROFILE_DATA["current_ctc"])
                    elif "expected" in ctx and "ctc" in ctx:
                        field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                    elif "notice" in ctx:
                        field.send_keys(MY_PROFILE_DATA["notice_period"])
                    elif "experience" in ctx or "years" in ctx:
                        field.send_keys(MY_PROFILE_DATA["experience"])
                    # --- NEW FIX FOR JOB 8 ---
                    elif any(word in ctx for word in ["willing", "relocate", "yes", "message", "type"]):
                        field.send_keys("Yes")
                    else:
                        # Safety fallback for other text fields
                        if not field.get_attribute("value"):
                            field.send_keys("Yes")
                except: continue

            # 3. Handle Radio Buttons (Standard Priority)
            radio_groups = {}
            for r in driver.find_elements(By.XPATH, "//input[@type='radio']"):
                name = r.get_attribute("name")
                if name:
                    if name not in radio_groups: radio_groups[name] = []
                    radio_groups[name].append(r)

            for name, buttons in radio_groups.items():
                selected = False
                for btn in buttons:
                    try:
                        text = btn.find_element(By.XPATH, "./ancestor::label | ./..").text.lower()
                        if any(pos in text for pos in ["15", "immediate", "yes", "willing", "relocate"]):
                            driver.execute_script("arguments[0].click();", btn)
                            selected = True; break
                    except: pass
                if not selected:
                    driver.execute_script("arguments[0].click();", buttons[0])

            # 📸 Debug: Show filled state
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_FILLED.png")

            # 4. Click Save and Wait
            driver.execute_script("arguments[0].click();", save_button)
            print(f"🚀 Job {job_idx}: Clicked Save for step {step}")
            time.sleep(4)

        return True
    except Exception as e:
        print(f"⚠️ Error handling questionnaire: {e}")
        return False

def run_automation():
    print("🚀 Starting Latest Jobs Bot with Multi-Step Logic...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Establish session
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        driver.refresh()
        time.sleep(5)

        # Search Query (Mumbai/Pune, Latest, 0-2 yrs)
        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)

        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(links)} jobs.")

        applied = 0
        for idx, link in enumerate(links[:40]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                # Check for "Already Applied" or "External Site"
                page_source = driver.page_source.lower()
                if "already applied" in page_source or "apply on company site" in page_source:
                    continue

                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Applying to Job {idx+1}...")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 10: break
            except: continue

        print(f"🏁 Final Apply Count: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
