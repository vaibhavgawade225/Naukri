import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)
        
        # Check for Access Denied on search results
        if "access denied" in driver.page_source.lower():
            print("Access Denied on Search. Refreshing...")
            driver.refresh()
            time.sleep(10)

        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        print(f"Found {len(job_cards)} latest jobs.")

        applied_count = 0
        # Loop through up to 10 jobs to find 5 valid ones
        for i in range(min(len(job_cards), 10)):
            try:
                driver.switch_to.window(driver.window_handles[0])
                cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
                title = cards[i].find_element(By.CSS_SELECTOR, "a.title")
                
                driver.execute_script("arguments[0].click();", title)
                time.sleep(random.uniform(8, 12)) # Longer wait for Job Page
                
                driver.switch_to.window(driver.window_handles[-1])
                
                # --- CRITICAL FIX: Check Access Denied on JOB PAGE ---
                if "access denied" in driver.page_source.lower() or "403" in driver.title:
                    print(f"⚠️ Access Denied on Job {i+1}. Retrying Refresh...")
                    driver.refresh()
                    time.sleep(10)

                # Try to find Apply button
                apply_xpath = "//button[text()='Apply'] | //button[contains(text(), 'Apply')] | //button[@id='apply-button']"
                apply_btns = driver.find_elements(By.XPATH, apply_xpath)
                
                if apply_btns:
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Applied to Job {i+1}")
                    time.sleep(5)
                    driver.save_screenshot(f"applied_job_{i+1}_SUCCESS.png")
                    applied_count += 1
                else:
                    # Capture why it failed
                    print(f"ℹ️ Job {i+1} failed to show Apply button.")
                    driver.save_screenshot(f"job_{i+1}_FAILED_state.png")
                
                if applied_count >= 5: break

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(random.uniform(3, 5))

            except Exception as e:
                print(f"❌ Error at Job {i+1}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        print(f"SUCCESS: Total Processed: {applied_count}")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
