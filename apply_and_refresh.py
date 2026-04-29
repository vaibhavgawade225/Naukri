import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

def run_automation():
    print("Starting Naukri Auto-Apply...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    # Added real browser user agent to prevent Access Denied
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # 1. Land on Home Page first (Important for session handshake)
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        
        # 2. Inject Cookies
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # 3. Go to search and REFRESH if blocked
        search_url = "https://www.naukri.com/developer-jobs?experience=0&experience=1&experience=2"
        driver.get(search_url)
        time.sleep(8)
        
        if "access denied" in driver.page_source.lower():
            print("Access Denied detected. Retrying with forced refresh...")
            driver.refresh()
            time.sleep(10)

        # 4. Find Job Cards
        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        print(f"Found {len(job_cards)} jobs.")

        applied_count = 0
        # Only try first 5 to keep it simple and safe
        for i in range(len(job_cards[:5])):
            try:
                # Re-fetch cards every loop to avoid 'Stale' errors
                cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
                title = cards[i].find_element(By.CSS_SELECTOR, "a.title")
                
                # Use JavaScript to click to bypass transparent overlays
                driver.execute_script("arguments[0].click();", title)
                time.sleep(6)
                
                # Switch to new tab
                driver.switch_to.window(driver.window_handles[-1])
                
                # Look for ANY apply button
                apply_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']")
                if apply_btn:
                    driver.execute_script("arguments[0].click();", apply_btn[0])
                    print(f"✅ Applied to job {i+1}")
                    applied_count += 1
                    time.sleep(3)
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)
            except Exception:
                print(f"❌ Skipping job {i+1}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        print(f"SUCCESS: Applied to {applied_count} jobs.")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
