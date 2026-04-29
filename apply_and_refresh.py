import os
import time
import sys
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
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        search_url = "https://www.naukri.com/developer-jobs?experience=0&experience=1&experience=2"
        driver.get(search_url)
        time.sleep(10)
        driver.save_screenshot("search_results.png") # See if jobs loaded

        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        print(f"Found {len(job_cards)} jobs.")

        applied_count = 0
        for i, card in enumerate(job_cards[:5]):
            try:
                # Try clicking the job title specifically
                title = card.find_element(By.CLASS_NAME, "title")
                title.click()
                time.sleep(5)
                
                driver.switch_to.window(driver.window_handles[-1])
                driver.save_screenshot(f"job_page_{i}.png") # See the actual job page
                
                # Check for various apply button types
                apply_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']")
                if apply_buttons:
                    apply_buttons[0].click()
                    print(f"Applied to job {i+1}")
                    applied_count += 1
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                print(f"Skipping job {i+1}: Element not found")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        print(f"SUCCESS: Applied to {applied_count} jobs.")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        driver.save_screenshot("fatal_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
