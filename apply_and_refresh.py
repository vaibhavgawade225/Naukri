import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

# --- YOUR DATA CABINET ---
MY_PROFILE_DATA = {
    "current_ctc": "3,00,000",      
    "expected_ctc": "5,00,000",     
    "notice_period": "7",          
    "experience": "2",
    "relocation": "Yes"
}

def inject_cookies(driver):
    """Safely injects cookies and verifies session."""
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    if not cookie_raw:
        print("❌ No NAUKRI_COOKIE found in Secrets!")
        return
    
    print("🍪 Injecting session cookies...")
    for item in cookie_raw.split(';'):
        if '=' in item:
            try:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({
                    'name': name, 
                    'value': value, 
                    'domain': '.naukri.com', 
                    'path': '/'
                })
            except Exception as e:
                continue
    time.sleep(2)

def handle_questions(driver, job_idx):
    """Auto-fills pop-up questions using context matching."""
    try:
        time.sleep(5)
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        for field in inputs:
            try:
                container_text = field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                if "current ctc" in container_text: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected ctc" in container_text: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice period" in container_text: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in container_text: field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        radio_names = set([r.get_attribute("name") for r in radios if r.get_attribute("name")])
        for name in radio_names:
            try:
                btns = driver.find_elements(By.NAME, name)
                driver.execute_script("arguments[0].click();", btns[0])
            except: continue

        for path in ["//button[contains(text(), 'Submit')]", "//button[contains(text(), 'Save')]", "//button[text()='Apply']"]:
            btns = driver.find_elements(By.XPATH, path)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
    except: pass

def run_automation():
    print("🚀 Initializing Session-Guard Mode...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Initial Login
        driver.get("https://www.naukri.com/recruiters-in-india") 
        time.sleep(5)
        inject_cookies(driver)

        # Step 2: Search with Access Denied Recovery
        search_url = "https://www.naukri.com/java-developer-jobs-in-india?experience=1&sort=f"
        driver.get(search_url)
        time.sleep(10)
        
        # Check if blocked or logged out
        if "access denied" in driver.page_source.lower() or "login" in driver.current_url.lower():
            print("⚠️ Session lost or blocked. Re-initializing...")
            driver.delete_all_cookies()
            driver.get("https://www.naukri.com/recruiters-in-india")
            time.sleep(5)
            inject_cookies(driver) # Re-inject cookies after clear
            driver.get(search_url)
            time.sleep(15)

        driver.execute_script("window.scrollTo(0, 1000);")
        driver.save_screenshot("search_page_debug.png")

        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(8, 12))
                
                # Verify we are still logged in on the job page
                if "login" in driver.current_url.lower():
                    print(f"🔄 Logged out on Job {idx+1}. Re-injecting...")
                    inject_cookies(driver)
                    driver.refresh()
                    time.sleep(8)

                apply_xpath = "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Job {idx+1}: Applied.")
                    handle_questions(driver, idx+1)
                    driver.save_screenshot(f"applied_job_{idx+1}.png")
                    applied += 1
                
                if applied >= 5: break
            except: continue

        print(f"🏁 Final Status: {applied} processed.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
