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

def handle_questions(driver, job_idx):
    try:
        time.sleep(5)
        # 1. Fill Text Inputs (CTC, NP, etc.)
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        for field in inputs:
            try:
                container_text = field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                if "current ctc" in container_text: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected ctc" in container_text: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice period" in container_text: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in container_text: field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        # 2. Click first radio option for everything else
        radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        radio_names = set([r.get_attribute("name") for r in radios])
        for name in radio_names:
            try:
                btns = driver.find_elements(By.NAME, name)
                driver.execute_script("arguments[0].click();", btns[0])
            except: continue

        # 3. Aggressive Submit
        for path in ["//button[contains(text(), 'Submit')]", "//button[contains(text(), 'Save')]", "//button[text()='Apply']"]:
            btns = driver.find_elements(By.XPATH, path)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
    except: pass

def run_automation():
    print("🚀 Starting Ultra-Stealth Fix...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Login
        driver.get("https://www.naukri.com/recruiters-in-india") 
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # Step 2: Search with forced delay and scroll
        search_url = "https://www.naukri.com/java-developer-jobs-in-india?experience=1&sort=f"
        driver.get(search_url)
        time.sleep(15) # Wait for anti-bot check
        
        # Human behavior: Scroll down and up
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        
        # ALWAYS take a screenshot of the search results (even if 0 jobs)
        driver.save_screenshot("search_page_debug.png")
        print("📸 Search page screenshot taken.")

        # Step 3: Extract & Apply
        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(8, 12))
                
                # Check for Apply button
                apply_xpath = "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Job {idx+1}: Applied.")
                    handle_questions(driver, idx+1)
                    driver.save_screenshot(f"applied_job_{idx+1}.png")
                    applied += 1
                
                if applied >= 5: break
                time.sleep(random.uniform(5, 8))
            except: continue

        print(f"🏁 Final Status: {applied} jobs processed.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
