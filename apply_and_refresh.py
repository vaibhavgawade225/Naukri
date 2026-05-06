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
    Fills questions and clicks ONLY the Save button inside the questionnaire.
    It explicitly ignores the 'Save Job' button next to the Apply button.
    """
    try:
        found_anything = False
        
        # 1. FILL TEXT/NUMBER BOXES
        inputs = driver.find_elements(By.XPATH, "//input[@type='text'] | //input[@type='number'] | //textarea")
        for field in inputs:
            if not field.is_displayed(): continue
            html_ctx = driver.execute_script("return arguments[0].outerHTML + arguments[0].parentElement.innerText;", field).lower()
            
            val = "Yes"
            if "current" in html_ctx: val = MY_PROFILE_DATA["current_ctc"]
            elif "expected" in html_ctx: val = MY_PROFILE_DATA["expected_ctc"]
            elif "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]
            elif "experience" in html_ctx: val = MY_PROFILE_DATA["experience"]

            driver.execute_script("arguments[0].style.border='2px solid blue';", field)
            driver.execute_script("arguments[0].focus(); arguments[0].value = '';", field)
            ActionChains(driver).move_to_element(field).click().send_keys(str(val)).perform()
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
            found_anything = True

        # 2. CLICK RADIO BUTTONS (Text-Based Search)
        # We look for labels/spans containing the target answers
        options = driver.find_elements(By.XPATH, "//label | //span | //li[contains(@class, 'list')]")
        for opt in options:
            if not opt.is_displayed(): continue
            txt = opt.text.strip().lower()
            if any(k == txt or k in txt for k in ["15", "immediate", "yes", "willing", "relocate", "agree", "confirm"]):
                driver.execute_script("arguments[0].style.border='2px solid red';", opt)
                driver.execute_script("arguments[0].click();", opt)
                found_anything = True
                time.sleep(0.5)

        # 3. CLICK THE CORRECT SAVE BUTTON
        time.sleep(1)
        # Targeted XPATH: Find buttons ONLY inside the application popup/chatbot container
        # This skips the 'Save Job' button in the main header
        form_buttons = driver.find_elements(By.XPATH, """
            //div[contains(@class, 'bot-footer')]//button | 
            //div[contains(@class, 'drawer')]//button | 
            //div[contains(@class, 'footer')]//button[not(contains(@class, 'save-job'))] |
            //button[contains(@class, 'save-and-continue')] |
            //button[contains(text(), 'Next')] |
            //button[contains(text(), 'Submit')]
        """)

        for btn in form_buttons:
            if not btn.is_displayed(): continue
            
            # CRITICAL CHECK: Ignore the button if it is part of the JD Header
            is_main_page_save = driver.execute_script("""
                let el = arguments[0];
                return !!el.closest('.jd-header-comp') || !!el.closest('.jd-header');
            """, btn)
            
            if is_main_page_save:
                continue # Skip this button! It's the wrong one.

            btn_text = btn.text.lower()
            if any(word in btn_text for word in ["save", "next", "continue", "submit"]):
                print(f"   🎯 Questionnaire Button Found: {btn_text}")
                driver.execute_script("arguments[0].style.border='5px solid green'; arguments[0].click();", btn)
                return True
                
    except Exception as e:
        print(f"   [!] Step Error: {e}")
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
