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
    The main logic: Target ONLY the chatbot area and the specific 'sendMsg' Save button.
    """
    try:
        # 1. Fill Textbox (Notice Period/CTC/Exp)
        # Using the specific 'example' placeholder check from your screenshot
        inputs = driver.find_elements(By.XPATH, "//div[contains(@class, 'chatbot')]//input | //input[contains(@placeholder, 'example')]")
        for field in inputs:
            if not field.is_displayed(): continue
            val = MY_PROFILE_DATA["experience"] # Default
            # Context-aware values
            html_ctx = (field.get_attribute("placeholder") or "").lower()
            if "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]
            
            driver.execute_script("""
                arguments[0].focus();
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, field, str(val))
            time.sleep(0.5)

        # 2. Click Radio/Choice (Yes/No)
        choices = driver.find_elements(By.XPATH, "//div[contains(@class, 'chatbot')]//label | //div[contains(@class, 'chatbot')]//span[contains(@class, 'text')]")
        for opt in choices:
            txt = opt.text.strip().lower()
            if txt in ["yes", "immediate", "willing", "agree", "confirm"]:
                driver.execute_script("arguments[0].click();", opt)
                time.sleep(1) # Wait for Save button to enable

        # 3. CLICK THE SPECIFIC SAVE BUTTON (The id/class you provided)
        # We target the 'sendMsg' div and ensure it only contains the word 'Save'
        # This prevents clicking 'Send me jobs like this'
        save_btn = None
        btns = driver.find_elements(By.XPATH, "//div[contains(@class, 'sendMsg')] | //div[contains(@id, 'sendMsg')]")
        
        for b in btns:
            if b.text.strip() == "Save":
                save_btn = b
                break
        
        if save_btn:
            print(f"   🚀 Clicking the verified 'Save' div.")
            driver.execute_script("""
                arguments[0].style.border = '5px solid green';
                arguments[0].classList.remove('disabled');
                arguments[0].click();
            """, save_btn)
            return True

    except Exception as e:
        print(f"   [!] Interaction error: {e}")
    
    return False
    
def handle_questionnaire(driver, job_idx):
    """
    Sequence: 
    1. Wait for chatbot to load after Apply is clicked.
    2. Loop: Fill one answer -> Click the specific 'Save' div.
    """
    print(f"   ⏳ Job {job_idx}: Waiting for chatbot/questionnaire to initialize...")
    time.sleep(5) # Give the chatbot time to slide in after the Apply click
    
    for step in range(1, 15): # Support up to 15 questions
        driver.switch_to.default_content()
        
        # Take a screenshot BEFORE interacting to see the question
        driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_BEFORE.png")
        
        # Try to process the step (Fill Answer + Click the 'Save' div)
        success = process_single_step(driver)
        
        # If not found in main content, check iframes (rare for chatbot but safe to keep)
        if not success:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                try:
                    driver.switch_to.frame(frame)
                    if process_single_step(driver):
                        success = True
                        break
                except:
                    pass
                finally:
                    driver.switch_to.default_content()
        
        # Take a screenshot AFTER to verify the click/fill
        driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_AFTER.png")
        
        if success:
            print(f"   ✅ Step {step}: Answered and Clicked Save.")
            time.sleep(3.5) # Wait for the next chatbot message to appear
        else:
            # If process_single_step returns False, it means no 'Save' button was found.
            # This usually means the application is finished.
            print(f"   🏁 Step {step}: No 'Save' button detected. Questionnaire likely finished.")
            break

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
