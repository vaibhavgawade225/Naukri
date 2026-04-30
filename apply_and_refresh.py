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

def handle_questions(driver):
    """Deep-scan for any question fields and fill them with profile data."""
    try:
        time.sleep(5) 
        # Handle Text/Number inputs
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='number'] | //textarea")
        for field in inputs:
            try:
                container_text = field.find_element(By.XPATH, "./ancestor::div[1]").text.lower()
                if "current ctc" in container_text: field.send_keys(MY_PROFILE_DATA["current_ctc"])
                elif "expected ctc" in container_text: field.send_keys(MY_PROFILE_DATA["expected_ctc"])
                elif "notice period" in container_text: field.send_keys(MY_PROFILE_DATA["notice_period"])
                elif "experience" in container_text: field.send_keys(MY_PROFILE_DATA["experience"])
            except: continue

        # Handle Radio Buttons (Random selection + Relocation logic)
        radio_groups = {}
        for r in driver.find_elements(By.XPATH, "//input[@type='radio']"):
            name = r.get_attribute("name")
            if name not in radio_groups: radio_groups[name] = []
            radio_groups[name].append(r)

        for name, buttons in radio_groups.items():
            try:
                group_context = buttons[0].find_element(By.XPATH, "./ancestor::div[contains(@class, 'question')]").text.lower()
                if "reloc" in group_context:
                    for b in buttons:
                        if "yes" in b.get_attribute("value").lower() or "yes" in b.find_element(By.XPATH, "..").text.lower():
                            driver.execute_script("arguments[0].click();", b)
                            break
                else:
                    driver.execute_script("arguments[0].click();", buttons[0])
            except: 
                driver.execute_script("arguments[0].click();", buttons[0])

        # Find and click EVERY possible Submit button
        for path in ["//button[contains(text(), 'Submit')]", "//button[contains(text(), 'Save')]", "//button[contains(text(), 'Apply')]"]:
            btns = driver.find_elements(By.XPATH, path)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(3)
    except: pass

def run_automation():
    print("🚀 Starting Permanent Stealth Fix...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Login via Cookies
        driver.get("https://www.naukri.com/recruiters-in-india") 
        time.sleep(random.uniform(5, 7))
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # Step 2: Search with Random Scroll (Bypass Firewall)
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(15)
        driver.execute_script("window.scrollTo(0, 600);") # Fake human scrolling
        time.sleep(2)
        driver.save_screenshot("search_results.png")

        # Step 3: Extract links and visit them DIRECTLY
        job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(job_links)} jobs.")

        if not job_links:
            print("🚫 Access Denied detected. Refreshing once...")
            driver.refresh()
            time.sleep(15)
            job_links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]

        applied = 0
        for idx, link in enumerate(job_links[:15]):
            try:
                driver.get(link)
                time.sleep(random.uniform(10, 15))
                
                # Look for ANY apply button (button, div, or span)
                apply_xpath = "//button[text()='Apply' or contains(text(), 'Apply')] | //span[text()='Apply']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Job {idx+1}: Clicked Apply.")
                    
                    # Handle all cross-questions and radio buttons
                    handle_questions(driver)
                    
                    driver.save_screenshot(f"applied_job_{idx+1}.png")
                    applied += 1
                
                if applied >= 5: break
                time.sleep(random.uniform(5, 10))
            except: continue

        print(f"🏁 Final Status: {applied} jobs successfully applied.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
