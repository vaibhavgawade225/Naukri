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
    "notice_period": "15",          
    "experience": "2",
    "relocation": "Yes"
}

def handle_questions(driver, job_idx):
    """Auto-fills all pop-up questions."""
    try:
        time.sleep(5)
        # 1. Fill Text Inputs
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        for field in inputs:
            try:
                container_text = field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                if "current ctc" in container_text: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected ctc" in container_text: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice period" in container_text: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in container_text: field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        # 2. Force click radio buttons
        radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        radio_names = set([r.get_attribute("name") for r in radios if r.get_attribute("name")])
        for name in radio_names:
            try:
                btns = driver.find_elements(By.NAME, name)
                if btns: driver.execute_script("arguments[0].click();", btns[0])
            except: continue

        # 3. Submit
        for path in ["//button[contains(text(), 'Submit')]", "//button[contains(text(), 'Save')]", "//button[text()='Apply']"]:
            btns = driver.find_elements(By.XPATH, path)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
    except: pass

def run_automation():
    print("🚀 Initializing Ultra-Stealth Mode...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # We use a newer User-Agent to look like a modern Windows PC
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Handshake (Recruiter page is less guarded than home page)
        driver.get("https://www.naukri.com/recruiters-in-india") 
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # Step 2: Search with Access Denied Recovery
        search_url = "https://www.naukri.com/java-developer-jobs-in-india?experience=1&sort=f"
        driver.get(search_url)
        time.sleep(10)
        
        # IF BLOCKED: Try a human-like refresh
        if "access denied" in driver.page_source.lower() or "403" in driver.title:
            print("⚠️ Access Denied detected. Retrying with stealth bypass...")
            driver.delete_all_cookies() # Clear traces
            time.sleep(5)
            driver.get("https://www.naukri.com/") # Go home first
            time.sleep(5)
            driver.get(search_url) # Return to search
            time.sleep(15)

        driver.execute_script("window.scrollTo(0, 1000);") # Scroll to trigger content
        driver.save_screenshot("search_page_debug.png")

        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(10, 15)) # Slow, human-like speed
                
                apply_xpath = "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Applied to Job {idx+1}")
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
