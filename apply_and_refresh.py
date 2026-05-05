import os
import time
import random
import glob
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

def handle_questionnaire(driver, job_idx):
    """Handles multi-step popups safely without getting trapped in ad iframes."""
    try:
        for step in range(1, 6):
            time.sleep(5)
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_START.png")
            
            # Smart Iframe Check: ONLY switch if we can't find any inputs on the main page
            inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea | //input[@type='radio']")
            if not inputs:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i in iframes:
                    try:
                        driver.switch_to.frame(i)
                        if driver.find_elements(By.XPATH, "//input"): break
                    except: driver.switch_to.default_content()
            
            # Re-fetch inputs in case we switched frames
            text_inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
            
            # 1. Answer Text/Number fields (The hybrid approach)
            for field in text_inputs:
                if not field.is_displayed(): continue
                try:
                    ctx = (field.get_attribute("placeholder") or "").lower()
                    try: ctx += " " + field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                    except: pass
                    
                    val = "Yes" 
                    if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                    elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                    elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                    elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
                    
                    # Attempt 1: Standard Selenium typing
                    try:
                        field.clear()
                        field.send_keys(val)
                    except:
                        pass # If blocked, move to fallback
                        
                    # Attempt 2: JS Force + Events (Ensures the 'Save' button wakes up)
                    driver.execute_script("arguments[0].value = arguments[1];", field, val)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", field)
                except: pass

            # 2. Answer Radio Buttons (Reverted to the proven working logic)
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

            # 3. Find and Click Save 
            # (Fixed XPath: using '.' instead of 'text()' to find text hidden inside <span> tags)
            save_button = None
            button_selectors = [
                "//button[contains(translate(., 'SAVE', 'save'), 'save')]",
                "//button[contains(translate(., 'SUBMIT', 'submit'), 'submit')]",
                "//button[contains(translate(., 'NEXT', 'next'), 'next')]",
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
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_FILLED.png")
            driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
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
    print("🚀 Starting Bot with Reliable Field Logic...")
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
