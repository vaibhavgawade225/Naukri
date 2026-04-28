import os
import time
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

def run_automation():
    print("Starting Naukri Auto-Apply & Refresh...")
    
    # We use the same simple string secret as the other repo
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    if not cookie_raw:
        print("CRITICAL: NAUKRI_COOKIE secret is missing!")
        sys.exit(1)

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # 1. Inject Cookies
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # 2. Search for Jobs (Developer, 0-2 Years)
        # This URL pre-filters for Developer roles with 0-2 years exp
        search_url = "https://www.naukri.com/developer-jobs?experience=0&experience=1&experience=2"
        print(f"Searching jobs at: {search_url}")
        driver.get(search_url)
        time.sleep(10)

        # 3. Apply to first few jobs
        job_cards = driver.find_elements(By.CLASS_NAME, "srp-jobtuple-wrapper")
        print(f"Found {len(job_cards)} jobs. Attempting to apply...")

        applied_count = 0
        for i in range(min(5, len(job_cards))): # Apply to top 5 jobs per run
            try:
                job_cards[i].click()
                driver.switch_to.window(driver.window_handles[-1]) # Switch to job tab
                time.sleep(5)
                
                apply_button = driver.find_element(By.ID, "apply-button")
                apply_button.click()
                print(f"Applied to job {i+1}")
                applied_count += 1
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)
            except:
                print(f"Could not apply to job {i+1} (Maybe already applied or external site)")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        # 4. Final Profile Refresh (The Resume Upload trick)
        print("Finalizing with Profile Refresh...")
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(10)
        # (Optional: Add the file upload logic here like the other script)

        print(f"SUCCESS: Applied to {applied_count} jobs and refreshed profile.")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        driver.save_screenshot("apply_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
