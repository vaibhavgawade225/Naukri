import os
import time
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# --- YOUR DATA CABINET ---
MY_PROFILE_DATA = {
    "experience": "2",            
    "current_ctc": "3,00,000",      
    "expected_ctc": "5,00,000",     
    "notice_period": "7",          
    "current_location": "Pune",
    "relocation": "Yes"
}

def handle_access_denied(driver, cookie_raw=None):
    """Detects Access Denied page and attempts bypass using cookies and refresh."""
    try:
        content = driver.page_source.lower()
        if "access denied" in content or "403" in driver.title:
            print("🚨 Access Denied detected. Attempting Anti-Bot Bypass...")
            time.sleep(random.uniform(5, 8))
            
            # If cookies are provided, try re-injecting them on the blocked page
            if cookie_raw:
                for item in cookie_raw.split(';'):
                    if '=' in item:
                        name, value = item.strip().split('=', 1)
                        driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})
            
            driver.refresh()
            time.sleep(10)
            return "access denied" not in driver.page_source.lower()
    except: pass
    return True

def clear_overlays(driver):
    """Forcefully removes any popups or loading layers."""
    try:
        driver.execute_script("""
            let selectors = ['.layers', '.modal', '.gnb-overlay', '.crossIcon', '[class*="close"]', '.drawer-wrapper', '#block'];
            selectors.forEach(s => {
                document.querySelectorAll(s).forEach(el => el.remove());
            });
        """)
    except: pass

def answer_questions(driver):
    """Smart-answer logic for questionnaires."""
    try:
        if len(driver.find_elements(By.TAG_NAME, "iframe")) > 0:
            driver.switch_to.frame(0)

        wrappers = driver.find_elements(By.XPATH, "//div[contains(@class, 'question')] | //li[contains(@class, 'item')]")
        for wrapper in wrappers:
            text = wrapper.text.lower()
            inputs = wrapper.find_elements(By.XPATH, ".//input | .//select | .//textarea")
            if not inputs: continue
            
            if "current ctc" in text: inputs[0].send_keys(MY_PROFILE_DATA["current_ctc"])
            elif "expected ctc" in text: inputs[0].send_keys(MY_PROFILE_DATA["expected_ctc"])
            elif "notice period" in text: inputs[0].send_keys(MY_PROFILE_DATA["notice_period"])
            elif "relocate" in text:
                choice = MY_PROFILE_DATA["relocation"].lower()
                for rb in wrapper.find_elements(By.XPATH, ".//input[@type='radio']"):
                    if choice in rb.get_attribute("value").lower() or choice in rb.find_element(By.XPATH, "..").text.lower():
                        driver.execute_script("arguments[0].click();", rb)
                        break
        
        submit = driver.find_elements(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Save')]")
        if submit: driver.execute_script("arguments[0].click();", submit[0])
        driver.switch_to.default_content()
    except: 
        try: driver.switch_to.default_content()
        except: pass

def run_automation():
    print("🚀 Starting Smart-Apply with Anti-Bot Bypass...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Using a high-reputation, non-generic User Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    
    # Enhanced Stealth Configuration
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        # STEP 1: Land on Home Page first to establish a "Human" entry point
        print("🏠 Loading Home Page...")
        driver.get("https://www.naukri.com/")
        time.sleep(random.uniform(5, 8))
        
        # Inject Cookies after landing
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # STEP 2: Navigate to search
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        print("🔍 Navigating to Job Search...")
        driver.get(search_url)
        time.sleep(10)
        
        # Immediate check for Access Denied on search results
        handle_access_denied(driver, cookie_raw)

        applied_count = 0
        for i in range(7):
            try:
                driver.switch_to.window(driver.window_handles[0])
                clear_overlays(driver)
                
                job_cards = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]"))
                )
                
                if i >= len(job_cards): break
                card = job_cards[i]
                
                title_link = card.find_element(By.XPATH, ".//a[@class='title ']")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", title_link)
                time.sleep(random.uniform(1, 3))
                
                old_handles = driver.window_handles
                driver.execute_script("arguments[0].click();", title_link)
                
                WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(old_handles))
                driver.switch_to.window(driver.window_handles[-1])
                
                # Check for Access Denied on the Job Detail Page
                time.sleep(6)
                handle_access_denied(driver, cookie_raw)
                driver.execute_script("window.scrollTo(0, 400);")
                
                # Apply Logic
                apply_xpath = "//button[text()='Apply'] | //button[contains(text(), 'Apply')] | //input[@value='Apply']"
                apply_btn = WebDriverWait(driver, 12).until(EC.element_to_be_clickable((By.XPATH, apply_xpath)))
                
                driver.execute_script("arguments[0].click();", apply_btn)
                print(f"✅ Job {i+1}: Apply Clicked.")
                time.sleep(random.uniform(4, 6))
                
                if "question" in driver.page_source.lower():
                    answer_questions(driver)
                
                applied_count += 1
                driver.save_screenshot(f"job_{i+1}_success.png")

            except Exception as e:
                print(f"⚠️ Job {i+1}: Could not apply. Capturing error state...")
                driver.save_screenshot(f"job_{i+1}_error.png")
            
            finally:
                while len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])

        print(f"🏁 FINISHED: Total Processed: {applied_count}")

    except Exception as e:
        print(f"❌ FATAL ERROR: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
