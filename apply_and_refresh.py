import os
import time
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

def run_automation():
    print("Starting Java Developer Auto-Apply (Sort: Latest)...")
    
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    if not cookie_raw:
        print("CRITICAL: NAUKRI_COOKIE missing!")
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
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # ADDED &sort=f to get Fresh/Latest jobs
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        print(f"Searching latest jobs at: {search_url}")
        driver.get(search_url)
        time.sleep(10)

        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        print(f"Found {len(job_cards)} jobs.")

        applied_count = 0
        for i, card in enumerate(job_cards[:7]): # Checked top 7 latest jobs
            try:
                title_link = card.find_element(By.XPATH, ".//a[@class='title ']")
                title_link.click()
                time.sleep(5)
                
                driver.switch_to.window(driver.window_handles[-1])
                
                # Try multiple button variations
                try:
                    # Look for standard Apply or Company Site Apply
                    apply_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']"))
                    )
                    
                    btn_text = apply_btn.text.lower()
                    apply_btn.click()
                    
                    if "company site" in btn_text:
                        print(f"Job {i+1}: Clicked 'Apply on Company Site' (External)")
                    else:
                        print(f"Job {i+1}: Applied successfully (Internal)")
                    
                    applied_count += 1
                    time.sleep(3)
                except:
                    print(f"Job {i+1}: No apply button found or already applied.")

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        # Final Profile Refresh
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(5)
        driver.refresh()
        print(f"FINISHED: Total actions taken: {applied_count}")

    except Exception as e:
        print(f"FATAL: {str(e)}")
        driver.save_screenshot("fatal_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
