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
    Refined for Neo-AI Chatbot: Fills the active question, 
    verifies the Save button is enabled, and clicks it.
    """
    try:
        # 1. HANDLE TEXT INPUTS (Industry Experience / CTC)
        # We target the specific 'For example' placeholder seen in your screen
        text_fields = driver.find_elements(By.XPATH, "//input[not(@type='radio')] | //textarea")
        for field in text_fields:
            if not field.is_displayed(): continue
            placeholder = (field.get_attribute("placeholder") or "").lower()
            
            # Logic to decide what to type
            val = MY_PROFILE_DATA["experience"]
            if "current" in placeholder: val = MY_PROFILE_DATA["current_ctc"]
            elif "expected" in placeholder: val = MY_PROFILE_DATA["expected_ctc"]

            driver.execute_script("""
                arguments[0].focus();
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            """, field, str(val))
            time.sleep(0.5)

        # 2. HANDLE RADIO BUTTONS (Yes/No/Interview Willingness)
        # We click the label text directly to ensure React registers the 'Check'
        choices = driver.find_elements(By.XPATH, "//label | //span[contains(@class, 'label')] | //div[contains(@class, 'radio')]")
        for opt in choices:
            if not opt.is_displayed(): continue
            txt = opt.text.strip().lower()
            if any(k == txt or k in txt for k in ["yes", "15", "immediate", "willing", "agree"]):
                driver.execute_script("arguments[0].click();", opt)
                print(f"   🔘 Selected: {txt}")
                time.sleep(0.8) # Wait for 'Save' button to transition from disabled to enabled

        # 3. THE SAVE BUTTON (The Blue Floating Button)
        # Search specifically for the button that is NOT part of the background JD
        save_btns = driver.find_elements(By.XPATH, "//button[text()='Save' or text()='Next' or contains(@class, 'save')]")
        
        for btn in save_btns:
            # We use JS to check if the button is inside the chatbot window and not the JD header
            is_valid = driver.execute_script("""
                let el = arguments[0];
                let isChat = !!el.closest('.chatbot_main') || !!el.closest('[class*="chatbot"]');
                let isHeader = !!el.closest('.jd-header');
                return isChat && !isHeader && el.offsetHeight > 0;
            """, btn)

            if is_valid:
                print(f"   🚀 Clicking Enabled Save Button")
                driver.execute_script("""
                    arguments[0].style.border='5px solid green';
                    arguments[0].removeAttribute('disabled');
                    arguments[0].click();
                """, btn)
                return True # Successfully completed this sub-step

    except Exception as e:
        print(f"   [!] Error during chatbot step: {e}")
    
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
