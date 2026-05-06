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
    Precision targeting for the 'sendMsg' chatbot button found in manual inspection.
    """
    try:
        # 1. FILL THE TEXT BOX (Like the '7' for notice period in your screenshot)
        # We target inputs specifically inside the chatbot/neo-agent container
        inputs = driver.find_elements(By.XPATH, "//div[contains(@class, 'chatbot')]//input | //div[contains(@id, 'chatbot')]//input | //input[contains(@placeholder, 'example')]")
        
        for field in inputs:
            if not field.is_displayed(): continue
            
            # Get specific value based on context
            html_ctx = driver.execute_script("return (arguments[0].outerHTML + arguments[0].parentElement.innerText).toLowerCase();", field)
            val = MY_PROFILE_DATA["experience"]
            if "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]
            elif "current" in html_ctx: val = MY_PROFILE_DATA["current_ctc"]
            elif "expected" in html_ctx: val = MY_PROFILE_DATA["expected_ctc"]

            # Use JS to set value and 'wake up' the Save button
            driver.execute_script("""
                arguments[0].focus();
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, field, str(val))
            time.sleep(0.5)

        # 2. SELECT RADIOS (Yes/No)
        labels = driver.find_elements(By.XPATH, "//div[contains(@class, 'chatbot')]//label | //div[contains(@class, 'chatbot')]//span")
        for label in labels:
            txt = label.text.strip().lower()
            if txt in ["yes", "immediate", "willing", "agree"]:
                driver.execute_script("arguments[0].click();", label)
                time.sleep(1)

        # 3. THE FIX: Click the 'sendMsg' Button
        # We target the exact class you found in the inspector
        save_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'sendMsg')] | //div[contains(@class, 'send')]")
        
        for el in save_elements:
            if "save" in el.text.lower() or "send" in el.text.lower() or el.get_attribute("tabindex") == "0":
                print(f"   🚀 Found Chatbot Button: {el.text}. Triggering Click...")
                
                # Highlight for the screenshot debug
                driver.execute_script("arguments[0].style.border='5px solid green';", el)
                
                # FORCE ENABLE & CLICK
                driver.execute_script("""
                    let btn = arguments[0];
                    // Remove 'disabled' from the button or any of its children
                    btn.classList.remove('disabled');
                    let inner = btn.querySelector('.disabled');
                    if(inner) inner.classList.remove('disabled');
                    
                    // Force the click
                    btn.click();
                """, el)
                
                # Backup physical click
                try:
                    ActionChains(driver).move_to_element(el).click().perform()
                except: pass
                
                return True # Successfully finished this interaction

    except Exception as e:
        print(f"   [!] Chatbot Error: {e}")
        
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
