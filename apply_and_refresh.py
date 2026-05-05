import os
import time
import random
import glob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

def human_type(driver, element, text):
    """Simulates real human typing to trigger website validation logic."""
    try:
        # 1. Click and Focus
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        element.click()
        time.sleep(0.5)
        
        # 2. Clear existing content
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.BACKSPACE)
        
        # 3. Type character by character
        for char in str(text):
            element.send_keys(char)
            time.sleep(random.uniform(0.1, 0.2))
        
        # 4. Trigger Events to 'Wake Up' the Save button
        events = ['focus', 'input', 'change', 'blur']
        for event in events:
            driver.execute_script(f"arguments[0].dispatchEvent(new Event('{event}', {{ bubbles: true }}));", element)
        
        print(f"   Typed: '{text}' into field.")
    except Exception as e:
        print(f"   Typing failed: {e}")

def handle_questionnaire(driver, job_idx):
    """Handles multi-step popups by simulating real user interaction."""
    try:
        for step in range(1, 6):
            time.sleep(5)
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_START.png")
            
            # Switch to iframe if it exists
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i in iframes:
                try:
                    driver.switch_to.frame(i)
                    if len(driver.find_elements(By.XPATH, "//button | //input")) > 0: break
                except: driver.switch_to.default_content()

            # 1. Answer Text/Number fields first (Crucial for enabling the Save button)
            inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea | //div[@contenteditable='true']")
            for field in inputs:
                if not field.is_displayed(): continue
                
                ctx = (field.get_attribute("placeholder") or "").lower()
                try: ctx += " " + field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                except: pass
                
                val = "Yes" # Default answer for Job 8 type questions
                if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
                
                human_type(driver, field, val)

            # 2. Answer Radio Buttons
            radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
            radio_names = set([r.get_attribute('name') for r in radios if r.get_attribute('name')])
            for name in radio_names:
                group = driver.find_elements(By.XPATH, f"//input[@name='{name}']")
                selected = False
                for btn in group:
                    try:
                        lbl = btn.find_element(By.XPATH, "./ancestor::label | ./..").text.lower()
                        if any(k in lbl for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                            driver.execute_script("arguments[0].click();", btn)
                            selected = True; break
                    except: pass
                if not selected and group: driver.execute_script("arguments[0].click();", group[0])

            # 3. Find and Click the Save/Submit Button
            save_button = None
            button_selectors = [
                "//button[contains(translate(text(), 'SAVE', 'save'), 'save')]",
                "//button[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]",
                "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]",
                "//button[@type='submit']",
                "//div[contains(@class, 'footer')]//button"
            ]
            
            for xpath in button_selectors:
                btns = driver.find_elements(By.XPATH, xpath)
                for b in btns:
                    if b.is_displayed():
                        save_button = b; break
                if save_button: break

            if not save_button:
                print(f"✅ Job {job_idx}: Finished or No button visible at Step {step}.")
                driver.switch_to.default_content()
                break

            # 4. Final Click
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_BEFORE_CLICK.png")
            driver.execute_script("arguments[0].click();", save_button)
            print(f"🚀 Job {job_idx}: Clicked Save for Step {step}")
            
            driver.switch_to.default_content()
            time.sleep(4)

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        driver.switch_to.default_content()
        return False

def run_automation():
    print("🚀 Starting Bot with Human-Typing Simulation...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Login via Cookies
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        driver.refresh()
        time.sleep(5)

        # Search Latest Jobs (Pune/Mumbai, 0-2 Exp)
        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)

        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(links)} potential jobs.")

        applied = 0
        for idx, link in enumerate(links[:20]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                if "already applied" in driver.page_source.lower():
                    continue

                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Starting Apply Process for Job {idx+1}...")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break # Applied limit for testing
            except: continue

        print(f"🏁 Total Successful Cycles: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
