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
        driver.save_screenshot("0_search_results_check.png") 

        applied_count = 0
        for i in range(len(job_cards[:5])):
            try:
                cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
                title = cards[i].find_element(By.CSS_SELECTOR, "a.title")
                
                driver.execute_script("arguments[0].click();", title)
                time.sleep(6)
                
                driver.switch_to.window(driver.window_handles[-1])
                
                # --- VERIFICATION STEP ---
                apply_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']")
                
                if apply_btn:
                    # Capture page BEFORE clicking to see the button exists
                    driver.save_screenshot(f"job_{i+1}_BEFORE_click.png")
                    
                    driver.execute_script("arguments[0].click();", apply_btn[0])
                    print(f"✅ Clicked Apply for job {i+1}")
                    
                    time.sleep(4)
                    # Capture page AFTER clicking to see the 'Success' message
                    driver.save_screenshot(f"job_{i+1}_AFTER_click.png")
                    applied_count += 1
                else:
                    print(f"⚠️ No apply button found for job {i+1} (maybe already applied)")
                    driver.save_screenshot(f"job_{i+1}_not_found.png")
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)
            except Exception as e:
                print(f"❌ Error at job {i+1}: {str(e)[:50]}")
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
