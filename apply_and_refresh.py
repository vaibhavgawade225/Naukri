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
        # 1. FILL INPUTS (Experience/CTC)
        inputs = driver.find_elements(By.XPATH, "//input | //textarea")
        for field in inputs:
            if not field.is_displayed(): continue
            val = MY_PROFILE_DATA["experience"] 
            # Force the value and trigger React's 'onchange'
            driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, field, str(val))

        # 2. SELECT RADIO OPTIONS (Yes/No)
        # We click the first visible label that matches our 'Yes' keywords
        options = driver.find_elements(By.XPATH, "//label | //span[contains(@class,'label')]")
        for opt in options:
            if opt.is_displayed() and any(k in opt.text.lower() for k in ["yes", "immediate", "willing"]):
                driver.execute_script("arguments[0].click();", opt)
                time.sleep(1) # CRITICAL: Wait for Save button to wake up

        # 3. THE "HAMMER" SAVE CLICK
        # We look for the button inside the chatbot footer specifically
        save_btns = driver.find_elements(By.XPATH, "//div[contains(@class,'chatbot')]//button | //div[contains(@class,'footer')]//button")
        
        for btn in save_btns:
            btn_text = (btn.text or "").lower()
            if any(word in btn_text for word in ["save", "next", "continue"]):
                print(f"   🎯 Target Found: {btn_text}. Forcing Click...")
                
                # We use a 3-layer click approach:
                # Layer 1: Remove disabled state
                driver.execute_script("arguments[0].removeAttribute('disabled');", btn)
                driver.execute_script("arguments[0].classList.remove('disabled');", btn)
                
                # Layer 2: JavaScript Click (Bypasses overlays)
                driver.execute_script("arguments[0].click();", btn)
                
                # Layer 3: Physical Click (Simulates real mouse)
                try:
                    ActionChains(driver).move_to_element(btn).click().perform()
                except: pass
                
                return True # If we clicked a Save button, we successfully finished this step

    except Exception as e:
        print(f"   [!] Error: {e}")
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
