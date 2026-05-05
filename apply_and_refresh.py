import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

def force_react_input(driver, field, value):
    """
    PRO FIX: React ignores normal Selenium typing. 
    This uses JavaScript to bypass React's synthetic event wrappers
    and forces the Virtual DOM to recognize the input.
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
        time.sleep(0.5)
        
        # 1. The React DOM Injector
        react_injector = """
        let input = arguments[0];
        let value = arguments[1];
        let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
        let nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
        
        if (input.tagName === 'INPUT' && nativeInputValueSetter) {
            nativeInputValueSetter.set.call(input, value);
        } else if (input.tagName === 'TEXTAREA' && nativeTextAreaValueSetter) {
            nativeTextAreaValueSetter.set.call(input, value);
        } else {
            input.value = value;
        }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        """
        driver.execute_script(react_injector, field, value)
        
        # 2. Fallback ActionChains (Physical Simulation)
        ActionChains(driver).move_to_element(field).click().send_keys(Keys.END).send_keys(Keys.SPACE).send_keys(Keys.BACKSPACE).perform()
    except Exception as e:
        print(f"   [!] Failed to inject text: {e}")

def handle_questionnaire(driver, job_idx):
    try:
        for step in range(1, 6):
            time.sleep(5)
            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_START.png")
            
            # --- 1. FILL TEXT BOXES ---
            # Broadened XPath to catch hidden dynamic types like type="tel"
            text_xpaths = "//input[not(@type='radio') and not(@type='checkbox') and not(@type='hidden') and not(@type='file') and not(@type='submit')] | //textarea"
            text_inputs = driver.find_elements(By.XPATH, text_xpaths)
            
            for field in text_inputs:
                if not field.is_displayed(): continue
                
                # Safe Context Extraction (No silent breaking)
                ctx = ""
                try: ctx += str(field.get_attribute("placeholder") or "").lower()
                except: pass
                try: ctx += " " + str(field.get_attribute("name") or "").lower()
                except: pass
                try: ctx += " " + str(field.find_element(By.XPATH, "./..").text).lower()
                except: pass

                # Determine Answer
                val = "Yes" 
                if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                elif "experience" in ctx or "year" in ctx: val = MY_PROFILE_DATA["experience"]
                
                print(f"   -> Found text field (context: '{ctx[:30]}...'). Injecting: {val}")
                force_react_input(driver, field, val)

            # --- 2. FILL RADIO BUTTONS ---
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
                if not selected and group: 
                    driver.execute_script("arguments[0].click();", group[0])

            # --- 3. FIND & CLICK SAVE ---
            save_button = None
            button_selectors = [
                "//button[contains(translate(., 'SAVE', 'save'), 'save')]",
                "//button[contains(translate(., 'SUBMIT', 'submit'), 'submit')]",
                "//button[contains(translate(., 'NEXT', 'next'), 'next')]",
                "//button[contains(@class, 'save')]",
                "//div[contains(@class, 'footer')]//button"
            ]
            
            for xpath in button_selectors:
                btns = driver.find_elements(By.XPATH, xpath)
                for b in btns:
                    if b.is_displayed():
                        save_button = b; break
                if save_button: break

            if not save_button:
                print(f"✅ Job {job_idx}: Form finished or no extra questions at Step {step}.")
                break

            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_FILLED.png")
            
            # Click the Save button securely using JS
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", save_button)
            print(f"🚀 Job {job_idx}: Clicked Save for Step {step}")
            time.sleep(4)

        return True
    except Exception as e:
        print(f"❌ Critical Error in Questionnaire: {e}")
        return False

def run_automation():
    print("🚀 Starting Pro-Level React-Injector Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
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
                
                # Kept to 5 for fast testing
                if applied >= 5: break 
            except: continue

        print(f"🏁 Total Successful Cycles: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
