import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

def run_automation():
    print("🚀 Starting Naukri Auto-Apply: Java Developer (0-2 Yrs)...")
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
        # 1. Establish session
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        
        # 2. Inject Cookies
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # 3. Updated Search Query: Java Developer, 0-2 Years, Sorted by Freshness
        # URL parameters: qry=java developer, experience=0,1,2, sort=f (freshness)
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        
        print(f"🔍 Searching: {search_url}")
        driver.get(search_url)
        time.sleep(8)
        
        if "access denied" in driver.page_source.lower():
            print("Access Denied detected. Retrying...")
            driver.refresh()
            time.sleep(10)

        # 4. Process Jobs
        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        print(f"Found {len(job_cards)} latest Java jobs.")
        driver.save_screenshot("search_results_java.png") 

        applied_count = 0
        # Applying to the first 5 freshest jobs
        for i in range(len(job_cards[:5])):
            try:
                cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
                title = cards[i].find_element(By.CSS_SELECTOR, "a.title")
                
                driver.execute_script("arguments[0].click();", title)
                time.sleep(6)
                
                driver.switch_to.window(driver.window_handles[-1])
                
                apply_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']")
                
                if apply_btn:
                    # Verification Screenshot
                    driver.save_screenshot(f"job_{i+1}_java_BEFORE.png")
                    
                    driver.execute_script("arguments[0].click();", apply_btn[0])
                    print(f"✅ Applied to Java Job {i+1}")
                    
                    time.sleep(4)
                    driver.save_screenshot(f"job_{i+1}_java_AFTER.png")
                    applied_count += 1
                else:
                    print(f"ℹ️ Skipping Job {i+1}: No apply button (Already applied or external).")
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)
            except Exception as e:
                print(f"❌ Skipping Job {i+1} due to error.")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        print(f"✨ SUCCESS: Applied to {applied_count} fresh Java jobs.")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
