import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

def process_single_step(driver):
    """
    Specifically designed for the Naukri Chatbot seen in your 'Saved Jobs' screenshot.
    """
    try:
        found_anything = False
        
        # 1. Look for the Chatbot Container
        # Naukri uses 'chatbot_main' for this floating window
        chatbot_container = driver.find_elements(By.XPATH, "//div[contains(@class, 'chatbot')] | //div[@id='chatbot_main']")
        
        # 2. Fill Textbox (Targeting the 'For example' placeholder from your screenshot)
        inputs = driver.find_elements(By.XPATH, "//input | //textarea")
        for field in inputs:
            placeholder = (field.get_attribute("placeholder") or "").lower()
            html_ctx = driver.execute_script("return arguments[0].outerHTML + (arguments[0].parentElement ? arguments[0].parentElement.innerText : '');", field).lower()
            
            # Match based on the specific Chatbot prompts
            if any(k in placeholder or k in html_ctx for k in ["experience", "years", "example", "ctc", "notice", "location"]):
                val = MY_PROFILE_DATA["experience"] # Default
                if "current" in html_ctx: val = MY_PROFILE_DATA["current_ctc"]
                elif "expected" in html_ctx: val = MY_PROFILE_DATA["expected_ctc"]
                elif "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]

                driver.execute_script("""
                    arguments[0].style.border='3px solid blue';
                    arguments[0].focus();
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                """, field, str(val))
                found_anything = True

        # 3. Handle Radio Buttons (Yes/No/Notice Period options)
        labels = driver.find_elements(By.XPATH, "//label | //span[contains(@class, 'text')] | //div[contains(@class, 'radio')]")
        for label in labels:
            txt = label.text.strip().lower()
            if txt and any(k == txt or f" {k} " in f" {txt} " for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                driver.execute_script("arguments[0].style.border='3px solid red'; arguments[0].click();", label)
                found_anything = True

        # 4. CLICK THE CHATBOT 'SAVE' BUTTON (The Big Blue Button)
        time.sleep(1.5)
        # Targeted XPATH for the button at the bottom of the chat window
        save_buttons = driver.find_elements(By.XPATH, """
            //div[contains(@class, 'chatbot')]//button[contains(text(), 'Save')] | 
            //div[contains(@class, 'chatbot')]//button[contains(text(), 'Next')] |
            //button[contains(@class, 'saveBtn')] |
            //div[@id='chatbot_main']//button
        """)

        for btn in save_buttons:
            try:
                # Ensure we only click the one that is visible and in the foreground
                if btn.is_displayed() and btn.size['width'] > 0:
                    btn_text = btn.text.strip().lower()
                    if any(word in btn_text for word in ["save", "next", "continue", "submit"]):
                        print(f"   🚀 Clicking Chatbot Button: {btn.text}")
                        driver.execute_script("""
                            arguments[0].style.border='5px solid green';
                            arguments[0].removeAttribute('disabled');
                            arguments[0].click();
                        """, btn)
                        return True # Exit step successfully
            except: continue
                
    except Exception as e:
        print(f"   [!] Chatbot Step Error: {e}")
        
    return False

def handle_questionnaire(driver, job_idx):
    for step in range(1, 11):
        time.sleep(4)
        driver.switch_to.default_content()
        success = process_single_step(driver)
        
        if not success:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                try:
                    driver.switch_to.frame(frame)
                    if process_single_step(driver):
                        success = True; break
                except: pass
                finally: driver.switch_to.default_content()
        
        driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}.png")
        if not success: break

def run_automation():
    print("🚀 Starting Selenium Full Script...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, 
            languages=["en-US", "en"], 
            vendor="Google Inc.", 
            platform="Win32", 
            webgl_vendor="Intel Inc.", 
            renderer="Intel Iris OpenGL Engine", 
            fix_hairline=True)

    try:
        driver.get("https://www.naukri.com/")
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com', 'path': '/'})
            driver.refresh()
            time.sleep(5)

        driver.get("https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f")
        time.sleep(8)
        
        job_links = []
        links = driver.find_elements(By.XPATH, "//a[contains(@href, 'job-listings-')]")
        for link in links:
            href = link.get_attribute('href')
            if href and href not in job_links:
                job_links.append(href)

        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(7)
                
                if "already applied" in driver.page_source.lower():
                    continue

                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(),'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    print(f"✅ Job {idx+1}: Clicking Apply...")
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break 
            except: continue

        print(f"🏁 Total Successful Cycles: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
