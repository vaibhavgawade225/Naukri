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
    """Deep-scans for questions and takes a debug screenshot of the popup."""
    try:
        time.sleep(5) 
        # TAKE DEBUG SCREENSHOT OF THE QUESTIONS
        driver.save_screenshot(f"debug_questions_job_{job_idx}.png")
        print(f"📸 Captured question popup for Job {job_idx}")

        # 1. Handle Text/Number inputs
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        for field in inputs:
            try:
                # Find the label text anywhere near the input
                container_text = field.find_element(By.XPATH, "./ancestor::div[contains(@class, 'form') or contains(@class, 'ques')][1]").text.lower()
                if "current ctc" in container_text: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected ctc" in container_text: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice period" in container_text: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in container_text: field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        # 2. Handle Radio Buttons (Force selection of first option)
        radio_groups = {}
        for r in driver.find_elements(By.XPATH, "//input[@type='radio']"):
            name = r.get_attribute("name")
            if name not in radio_groups: radio_groups[name] = []
            radio_groups[name].append(r)

        for name, buttons in radio_groups.items():
            try:
                # Click the first radio button in every group found
                driver.execute_script("arguments[0].click();", buttons[0])
            except: continue

        # 3. Find and click EVERY possible Submit/Apply button in the popup
        submit_paths = [
            "//button[contains(text(), 'Submit')]",
            "//button[contains(text(), 'Save')]",
            "//button[text()='Apply']",
            "//div[contains(@class, 'footer')]//button"
        ]
        for path in submit_paths:
            btns = driver.find_elements(By.XPATH, path)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
                    print(f"🚀 Sent answers for Job {job_idx}")
    except Exception as e:
        print(f"⚠️ Error handling questions: {str(e)[:50]}")

def run_automation():
    print("🚀 Starting Deep Vision Fix...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
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

        # Step 2: Search
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(15)

        # Step 3: Visit Jobs Directly
        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(8, 12))
                
                apply_xpath = "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Job {idx+1}: Clicked primary apply.")
                    
                    # PROCESS QUESTIONS + DEBUG SCREENSHOT
                    handle_questions(driver, idx+1)
                    
                    driver.save_screenshot(f"final_state_job_{idx+1}.png")
                    applied += 1
                
                if applied >= 5: break
                time.sleep(random.uniform(5, 8))
            except: continue

        print(f"🏁 Final Status: {applied} jobs processed.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
