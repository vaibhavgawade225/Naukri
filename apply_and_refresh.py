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
    "experience": "2"
}

def get_shadow_root(driver, element):
    """Accesses elements hidden inside Shadow DOM."""
    return driver.execute_script('return arguments[0].shadowRoot', element)

def cdp_type(driver, element, text):
    """
    PRO TECH: Uses Chrome DevTools Protocol to insert text.
    This bypasses React/Vue event listeners by simulating hardware-level input.
    """
    try:
        driver.execute_script("arguments[0].focus();", element)
        time.sleep(0.2)
        # Clear field first
        driver.execute_script("arguments[0].value = '';", element)
        # Hardware-level text insertion
        driver.execute_cdp_cmd('Input.insertText', {'text': str(text)})
        # Trigger validation events
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """, element)
        print(f"   [CDP] Successfully typed: {text}")
    except Exception as e:
        print(f"   [CDP Error] {e}")

def find_all_inputs(driver):
    """Finds all inputs, including those hidden in Shadow DOM."""
    all_inputs = driver.find_elements(By.XPATH, "//input | //textarea | //select")
    # Shadow DOM piercing (Experimental but powerful)
    hosts = driver.find_elements(By.XPATH, "//*[contains(@class, 'naukri')]") # Common Naukri shadow hosts
    for host in hosts:
        try:
            shadow = get_shadow_root(driver, host)
            if shadow:
                all_inputs.extend(shadow.find_elements(By.CSS_SELECTOR, "input, textarea, select"))
        except: continue
    return all_inputs

def handle_questionnaire(driver, job_idx):
    """Looping questionnaire handler using CDP tech."""
    try:
        for step in range(1, 6):
            time.sleep(6) # Wait for popup/next question
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_START.png")

            # 1. FIND INPUTS (Piercing Shadow DOM if needed)
            inputs = find_all_inputs(driver)
            if not inputs:
                print(f"   Step {step}: No inputs found. Checking if job is already applied...")
                break

            for field in inputs:
                if not field.is_displayed(): continue
                
                # Context identification
                try:
                    attr_text = f"{field.get_attribute('placeholder')} {field.get_attribute('name')} {field.get_attribute('id')}".lower()
                    parent_text = driver.execute_script("return arguments[0].parentElement.innerText;", field).lower()
                    ctx = attr_text + " " + parent_text
                except: ctx = ""

                # RADIO BUTTONS
                if field.get_attribute("type") == "radio":
                    if any(k in ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                        driver.execute_script("arguments[0].click();", field)
                
                # TEXT / NUMBER FIELDS
                elif field.tag_name in ["input", "textarea"]:
                    val = "Yes" 
                    if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                    elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                    elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                    elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
                    cdp_type(driver, field, val)

                # SELECT DROPDOWNS
                elif field.tag_name == "select":
                    driver.execute_script("arguments[0].selectedIndex = 1; arguments[0].dispatchEvent(new Event('change'));", field)

            # 2. CLICK SAVE/SUBMIT (Ultra-broad search)
            save_button = None
            selectors = [
                "//button[contains(translate(., 'SAVE', 'save'), 'save')]",
                "//button[contains(translate(., 'SUBMIT', 'submit'), 'submit')]",
                "//button[contains(translate(., 'NEXT', 'next'), 'next')]",
                "//div[contains(@class, 'footer')]//button",
                "//button[@type='submit']"
            ]
            for sel in selectors:
                btns = driver.find_elements(By.XPATH, sel)
                for b in btns:
                    if b.is_displayed(): save_button = b; break
                if save_button: break

            if save_button:
                driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_READY.png")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", save_button)
                print(f"🚀 Job {job_idx}: Step {step} Submitted.")
            else:
                print(f"✅ Job {job_idx}: Application likely complete.")
                break

        return True
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        return False

def run_automation():
    print("🚀 Starting Advanced CDP-Based Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
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

        driver.get("https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f")
        time.sleep(10)

        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(links)} jobs.")

        applied = 0
        for idx, link in enumerate(links[:15]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                if "already applied" in driver.page_source.lower(): continue

                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Applying to Job {idx+1}")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break 
            except: continue

        print(f"🏁 Final Applied Count: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
