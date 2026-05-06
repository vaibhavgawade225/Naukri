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
    try:
        found_anything = False
        
        # 1. HANDLE RADIO BUTTONS (Deep Search)
        # We look for the visible labels/spans that humans actually click
        labels = driver.find_elements(By.XPATH, "//label | //span[@class='label'] | //div[contains(@class, 'radio')]")
        for label in labels:
            if not label.is_displayed(): continue
            txt = label.text.lower()
            # Match common 'Yes' or 'Notice Period' answers
            if any(k in txt for k in ["15", "immediate", "yes", "willing", "relocate", "agree", "confirm"]):
                # Visual Debug: Draw a red box around what we click
                driver.execute_script("arguments[0].style.border='2px solid red';", label)
                driver.execute_script("arguments[0].click();", label)
                found_anything = True
                time.sleep(0.5)

        # 2. HANDLE TEXT BOXES (Already working, but adding a 'Pulse')
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
            
            # This "Pulse" tells React: "Hey! A human just typed here!"
            driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
            """, field)
            found_anything = True

        # 3. HANDLE SAVE BUTTON (The "Double Hammer")
        time.sleep(1)
        buttons = driver.find_elements(By.XPATH, "//button | //input[@type='submit'] | //span[contains(text(), 'Save')]")
        for btn in buttons:
            btn_text = (btn.text or "").lower()
            if any(word in btn_text for word in ["save", "submit", "next", "continue", "apply"]):
                print(f"   🎯 Attempting to click: {btn_text}")
                driver.execute_script("arguments[0].style.border='5px solid green';", btn)
                
                # Double Hammer: Remove 'disabled' and click via JS AND Physical Mouse
                driver.execute_script("""
                    arguments[0].removeAttribute('disabled');
                    arguments[0].classList.remove('disabled');
                    arguments[0].click();
                """, btn)
                
                try:
                    ActionChains(driver).move_to_element(btn).click().perform()
                except: pass
                
                return True # Move to next question
                
    except Exception as e:
        print(f"   [!] Error: {e}")
    
    return False
    
def handle_questionnaire(driver, job_idx):
    """The 'Human Loop': Fill one, Save one, Repeat."""
    # We allow up to 10 'steps' per job application
    for step in range(1, 11):
        time.sleep(3) # Wait for React to render the next question
        
        # Check Main Page
        driver.switch_to.default_content()
        success = process_single_step(driver)
        
        # If not found on main page, check iframes
        if not success:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                try:
                    driver.switch_to.frame(frame)
                    if process_single_step(driver):
                        success = True
                        break
                except: pass
                finally: driver.switch_to.default_content()
        
        # Capture progress for debugging
        driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}.png")
        
        if not success:
            print(f"   ✅ Job {job_idx}: No more 'Save' buttons or questions found.")
            break
        
        time.sleep(3)

def run_automation():
    print("🚀 Starting Selenium ActionChains Pro Bot...")
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
        fix_hairline=True,
    )

    try:
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
            driver.refresh()
            time.sleep(5)

        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(8)
        
        # Scrape Job Links
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
                time.sleep(random.uniform(6, 9))
                
                if "already applied" in driver.page_source.lower():
                    continue

                apply_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply') or text()='Apply']")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Starting Apply Process for Job {idx+1}...")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break 
            except Exception as e:
                print(f"   Error on job: {e}")
                continue

        print(f"🏁 Total Successful Cycles: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
