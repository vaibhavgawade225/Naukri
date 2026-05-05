import os
import time
import random
import glob
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
    Enhanced Multi-Step Handler:
    1. Guarantees a screenshot immediately.
    2. Scans for Save/Submit buttons using multiple XPaths.
    3. Handles nested iframes.
    """
    try:
        # Loop for multi-part questions (Steps)
        for step in range(1, 6):
            time.sleep(6) # Wait for popup/animation
            
            # --- CRITICAL: CAPTURE STATE IMMEDIATELY ---
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_INITIAL_VIEW.png")
            
            # --- IFRAME SCAN ---
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i in iframes:
                try:
                    driver.switch_to.frame(i)
                    if len(driver.find_elements(By.XPATH, "//button | //input")) > 0:
                        print(f"   (Inside Iframe for Job {job_idx})")
                        break 
                except: 
                    driver.switch_to.default_content()

            # 1. Identify ANY Save/Submit/Apply/Next button
            save_button = None
            button_xpaths = [
                "//button[contains(translate(text(), 'SAVE', 'save'), 'save')]",
                "//button[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]",
                "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]",
                "//button[@id='submit-btn']",
                "//button[contains(@class, 'save')]",
                "//div[contains(@class, 'footer')]//button"
            ]
            
            for xpath in button_xpaths:
                btns = driver.find_elements(By.XPATH, xpath)
                for b in btns:
                    if b.is_displayed():
                        save_button = b; break
                if save_button: break

            if not save_button:
                # If we can't find a button, check if the job was already applied successfully
                if "application sent" in driver.page_source.lower() or "applied" in driver.page_source.lower():
                    print(f"✅ Job {job_idx}: Application Successful.")
                else:
                    print(f"⚠️ Job {job_idx}: No Save button found at Step {step}.")
                driver.switch_to.default_content()
                break

            # 2. FILL FIELDS (JS Force-Fill)
            # Textboxes/Textareas
            inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
            for field in inputs:
                try:
                    ctx = (field.get_attribute("placeholder") or "").lower()
                    parent_text = ""
                    try: parent_text = field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                    except: pass
                    ctx += " " + parent_text

                    val = "Yes" 
                    if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                    elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                    elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                    elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]

                    driver.execute_script("arguments[0].value = arguments[1];", field, val)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
                except: pass

            # Radio Buttons
            radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
            radio_names = set([r.get_attribute('name') for r in radios if r.get_attribute('name')])
            for name in radio_names:
                group = driver.find_elements(By.XPATH, f"//input[@name='{name}']")
                selected = False
                for btn in group:
                    try:
                        lbl = btn.find_element(By.XPATH, "./ancestor::label | ./..").text.lower()
                        if any(k in lbl for k in ["15", "immediate", "yes", "willing", "relocate"]):
                            driver.execute_script("arguments[0].click();", btn)
                            selected = True; break
                    except: pass
                if not selected and group: driver.execute_script("arguments[0].click();", group[0])

            # 3. CLICK SAVE
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_READY_TO_CLICK.png")
            driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
            driver.execute_script("arguments[0].click();", save_button)
            print(f"🚀 Job {job_idx}: Clicked Save for step {step}")
            
            driver.switch_to.default_content()
            time.sleep(4)

        return True
    except Exception as e:
        print(f"❌ Error in questionnaire: {e}")
        driver.switch_to.default_content()
        return False

def run_automation():
    print("🚀 Starting Latest Jobs Bot with Visibility Fix...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        driver.refresh()
        time.sleep(5)

        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)
        driver.save_screenshot("SEARCH_RESULTS_VIEW.png")

        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(links)} jobs.")

        applied = 0
        for idx, link in enumerate(links[:20]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                # Check for "already applied" before clicking
                if "already applied" in driver.page_source.lower():
                    continue

                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    # 📸 Take screenshot BEFORE clicking apply
                    driver.save_screenshot(f"JOB_{idx+1}_BEFORE_APPLY_CLICK.png")
                    
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Applying to Job {idx+1}...")
                    
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break # Applied limit for testing
            except: continue

        print(f"🏁 Final Apply Count: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
