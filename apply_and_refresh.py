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
    """Fills questions and clicks the Save button without strict visibility checks."""
    try:
        found_anything = False
        
        # 1. FILL TEXT/NUMBER BOXES (Bypassing Visibility Check)
        inputs = driver.find_elements(By.XPATH, "//input[not(@type='hidden') and not(@type='submit') and not(@type='radio') and not(@type='checkbox')] | //textarea")
        for field in inputs:
            try:
                html_ctx = driver.execute_script("return arguments[0].outerHTML + (arguments[0].parentElement ? arguments[0].parentElement.innerText : '');", field).lower()
                
                val = "Yes"
                if "current" in html_ctx: val = MY_PROFILE_DATA["current_ctc"]
                elif "expected" in html_ctx: val = MY_PROFILE_DATA["expected_ctc"]
                elif "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]
                elif "experience" in html_ctx: val = MY_PROFILE_DATA["experience"]

                # Use pure JS to bypass "Element Not Interactable" errors on hidden React boxes
                driver.execute_script("""
                    arguments[0].style.border='2px solid blue';
                    arguments[0].focus();
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                """, field, str(val))
                found_anything = True
            except:
                continue

        # 2. CLICK RADIO BUTTONS (Bypassing Visibility Check)
        options = driver.find_elements(By.XPATH, "//label | //span | //li")
        for opt in options:
            try:
                txt = opt.text.strip().lower()
                # Skip empty text elements to save time
                if not txt: continue 
                
                if any(k == txt or f" {k} " in f" {txt} " for k in ["15", "immediate", "yes", "willing", "relocate", "agree", "confirm"]):
                    driver.execute_script("arguments[0].style.border='2px solid red'; arguments[0].click();", opt)
                    found_anything = True
            except:
                continue

        # 3. CLICK THE CORRECT SAVE BUTTON
        time.sleep(1.5) # Wait a moment for React to register the typing/clicking
        form_buttons = driver.find_elements(By.XPATH, "//button | //input[@type='submit'] | //input[@type='button']")

        for btn in form_buttons:
            try:
                btn_text = (btn.text or btn.get_attribute("value") or "").lower()
                
                # Check if it is a relevant button
                if any(word in btn_text for word in ["save", "next", "continue", "submit"]):
                    
                    # CRITICAL CHECK: Ignore the button if it is part of the JD Header (Top of the page)
                    is_main_page_save = driver.execute_script("""
                        let el = arguments[0];
                        return !!el.closest('.jd-header-comp') || !!el.closest('.jd-header');
                    """, btn)
                    
                    if is_main_page_save:
                        continue # Skip the wrong button!

                    print(f"   🎯 Questionnaire Button Found: {btn_text}")
                    driver.execute_script("""
                        arguments[0].style.border='5px solid green'; 
                        arguments[0].removeAttribute('disabled');
                        arguments[0].click();
                    """, btn)
                    return True # Clicked successfully, exit the step
            except:
                continue
                
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
