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
    Overhauled:
    1. Switches to iframes if present.
    2. Uses JS to force fill text boxes (Fixes Job 8).
    3. Clicks any 'Save' button regardless of case (Fixes Job 10).
    """
    try:
        # Loop for multi-part questions (Steps)
        for step in range(1, 8):
            time.sleep(5) # Wait for animation/popup
            
            # --- IFRAME CHECK ---
            # If the questionnaire is in an iframe, we must switch to it.
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i in iframes:
                try:
                    driver.switch_to.frame(i)
                    if len(driver.find_elements(By.XPATH, "//button | //input")) > 0:
                        break # Found the right iframe
                except: driver.switch_to.default_content()

            # 1. Identify ANY button that looks like a 'Continue/Save/Submit'
            save_button = None
            button_selectors = [
                "//button[contains(translate(text(), 'SAVE', 'save'), 'save')]",
                "//button[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]",
                "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]",
                "//div[contains(@class, 'footer')]//button",
                "//button[@type='submit']"
            ]
            
            for xpath in button_selectors:
                btns = driver.find_elements(By.XPATH, xpath)
                for b in btns:
                    if b.is_displayed():
                        save_button = b; break
                if save_button: break

            if not save_button:
                print(f"✅ Job {job_idx}: Finished or No Save button found.")
                driver.switch_to.default_content()
                break

            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_DETECTED.png")

            # 2. FILL TEXT BOXES (The 'Job 8' fix)
            # We use JavaScript to set the value directly to ensure it works even if hidden
            inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
            for field in inputs:
                try:
                    ctx = (field.get_attribute("placeholder") or "").lower()
                    parent_text = ""
                    try: parent_text = field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                    except: pass
                    ctx += " " + parent_text

                    val = "Yes" # Default for 'Willingness' questions
                    if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                    elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                    elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                    elif "experience" in ctx or "years" in ctx: val = MY_PROFILE_DATA["experience"]

                    # Set value using JavaScript to bypass 'not interactable' errors
                    driver.execute_script("arguments[0].value = arguments[1];", field, val)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
                except: continue

            # 3. FILL RADIO BUTTONS
            # We look for the label text and click it directly
            radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
            radio_names = set([r.get_attribute("name") for r in radios if r.get_attribute("name")])
            
            for name in radio_names:
                group = driver.find_elements(By.XPATH, f"//input[@name='{name}']")
                selected = False
                for btn in group:
                    try:
                        # Try to find text in the button's parent label
                        label_text = btn.find_element(By.XPATH, "./ancestor::label | ./..").text.lower()
                        if any(pos in label_text for pos in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                            driver.execute_script("arguments[0].click();", btn)
                            selected = True; break
                    except: pass
                if not selected and group:
                    driver.execute_script("arguments[0].click();", group[0])

            driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_FILLED.png")

            # 4. CLICK THE SAVE BUTTON (The 'Job 10' fix)
            # Use JS click to bypass elements being covered by other elements
            driver.execute_script("arguments[0].scrollIntoView(true);", save_button)
            driver.execute_script("arguments[0].click();", save_button)
            print(f"🚀 Job {job_idx}: Clicked Save for step {step}")
            
            # Switch back to main content before the next loop iteration check
            driver.switch_to.default_content()
            time.sleep(3)

        return True
    except Exception as e:
        print(f"⚠️ Error: {str(e)[:50]}")
        driver.switch_to.default_content()
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
                
                if applied >= 5: break
            except: continue

        print(f"🏁 Final Apply Count: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
