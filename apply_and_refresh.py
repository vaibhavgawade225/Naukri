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
    Specifically targets the inner 'sendMsg' div within the chatbot container.
    """
    try:
        # 1. Fill Textbox / Select Radio
        # (Assuming the answering logic from previous steps is working)
        active_inputs = driver.find_elements(By.XPATH, "//div[contains(@class, 'chatbot')]//input")
        for field in active_inputs:
            if field.is_displayed():
                val = MY_PROFILE_DATA["experience"]
                driver.execute_script("arguments[0].value = arguments[1];", field, str(val))
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
        
        time.sleep(1) # Wait for the Save button to become active

        # 2. THE SAVE BUTTON FIX
        # We target the specific inner div you provided: <div class="sendMsg">Save</div>
        # We use a path that finds the 'sendMsg' class inside the 'send' container.
        save_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'send')]//div[contains(@class, 'sendMsg')]")
        
        for el in save_elements:
            if el.text.strip() == "Save":
                print(f"   🚀 Found inner Save div. Triggering Deep Click...")
                
                # Visual Debug
                driver.execute_script("arguments[0].style.border='5px solid green';", el)
                
                # We click the inner element and then the outer one just to be safe
                driver.execute_script("""
                    let inner = arguments[0];
                    let outer = inner.parentElement;
                    
                    // Remove any 'disabled' classes from both
                    inner.classList.remove('disabled');
                    if(outer) outer.classList.remove('disabled');
                    
                    // Trigger the click on the interactive element
                    inner.click();
                    
                    // Dispatch 'Enter' key event as a backup (common for chatbots)
                    inner.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}));
                """, el)
                
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
