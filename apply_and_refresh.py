import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3,00,000",      
    "expected_ctc": "5,00,000",     
    "notice_period": "15",          
    "experience": "2",
    "relocation": "Yes"
}

def inject_cookies_and_verify(driver):
    """Injects cookies and verifies we aren't stuck on a login page."""
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    if not cookie_raw:
        print("❌ CRITICAL: NAUKRI_COOKIE secret is missing or empty.")
        return False
    
    print("🍪 Injecting session cookies...")
    for item in cookie_raw.split(';'):
        if '=' in item:
            try:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})
            except: continue
    
    time.sleep(3)
    driver.refresh()
    time.sleep(5)
    
    # Verify we are logged in by checking if "login" is still in the URL or page source
    if "login" in driver.current_url.lower():
        print("❌ CRITICAL: Cookie is expired or invalid. You have been logged out.")
        driver.save_screenshot("cookie_failure.png")
        return False
    return True

def handle_questionnaire(driver):
    """Context-aware question handler that brute-forces submission."""
    try:
        time.sleep(4) # Let the popup render
        
        # 1. Text Fields (Context Matching)
        for field in driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea"):
            try:
                context = field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                if "current ctc" in context: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected ctc" in context: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice period" in context: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in context: field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        # 2. Radio Buttons (First Option Fallback)
        radio_names = set([r.get_attribute("name") for r in driver.find_elements(By.XPATH, "//input[@type='radio']") if r.get_attribute("name")])
        for name in radio_names:
            try:
                btns = driver.find_elements(By.NAME, name)
                driver.execute_script("arguments[0].click();", btns[0]) # Always click the first option
            except: continue

        # 3. Submit 
        for xpath in ["//button[contains(text(), 'Submit')]", "//button[contains(text(), 'Save')]", "//button[text()='Apply']"]:
            for btn in driver.find_elements(By.XPATH, xpath):
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    print("✅ Questionnaire successfully submitted.")
                    return
    except Exception as e:
        print(f"⚠️ Questionnaire handler issue: {str(e)[:50]}")

def run_automation():
    print("🚀 Starting Clean Slate Automation...")
    
    # --- ADVANCED BROWSER DISGUISE ---
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Hide automation flags heavily monitored by Akamai
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    # Execute CDP command to remove webdriver property
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Safe Landing & Cookie Injection
        print("🏠 Landing on safe page to establish session...")
        driver.get("https://www.naukri.com/recruiters-in-india") 
        time.sleep(5)
        
        if not inject_cookies_and_verify(driver):
            return # Stop execution if cookies are dead

        # Step 2: Search Page
        print("🔍 Navigating to Search...")
        search_url = "https://www.naukri.com/java-developer-jobs-in-india?experience=1&sort=f"
        driver.get(search_url)
        time.sleep(12)
        
        # Always screenshot the search page to verify we beat the firewall
        driver.save_screenshot("01_search_page_status.png")

        if "access denied" in driver.page_source.lower() or "403" in driver.title:
            print("🚫 CRITICAL: Firewall blocked the search page. The GitHub IP is burned.")
            return

        # Step 3: Extract Links
        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs. Beginning application sequence...")

        # Step 4: Apply Loop
        applied_count = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                # Look for the primary apply button
                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']")
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"⏳ Clicked Apply on Job {idx+1}")
                    
                    handle_questionnaire(driver)
                    
                    driver.save_screenshot(f"02_applied_job_{idx+1}.png")
                    applied_count += 1
                else:
                    print(f"ℹ️ Skipped Job {idx+1} (Already applied or external link).")

                if applied_count >= 5: 
                    break
                
                time.sleep(random.uniform(4, 7)) # Pause between jobs
                
            except Exception as e:
                print(f"❌ Failed processing Job {idx+1}: {str(e)[:50]}")
                continue

        print(f"🏁 Execution Complete. Total applied: {applied_count}")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
