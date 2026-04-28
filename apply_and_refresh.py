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
    print("Starting Naukri Java Developer Auto-Apply & Refresh...")
    
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
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # 1. Open Home and Inject Cookies
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        print("Injecting cookies...")
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # 2. Targeted Job Search: Java Developer, 0-2 Years
        # Filtered URL for Java Developer roles specifically for Freshers/Junior (0-2 Yrs)
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2"
        print(f"Navigating to job search: {search_url}")
        driver.get(search_url)
        time.sleep(10)
        driver.save_screenshot("search_results.png")

        # 3. Locate Job Cards
        wait = WebDriverWait(driver, 20)
        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        print(f"Found {len(job_cards)} potential jobs.")

        applied_count = 0
        # Limit to 5 applications per run to stay under the radar
        for i, card in enumerate(job_cards[:5]):
            try:
                # Click the job title to open in a new tab
                job_title_link = card.find_element(By.XPATH, ".//a[@class='title ']")
                job_title_link.click()
                time.sleep(5)
                
                # Switch to the newly opened tab
                driver.switch_to.window(driver.window_handles[-1])
                print(f"Checking Job {i+1}: {driver.title}")
                driver.save_screenshot(f"job_page_{i+1}.png")

                # Look for the 'Apply' button
                # Supports both 'Apply' and 'Apply on Company Site' (though the latter is skipped)
                apply_button_xpath = "//button[text()='Apply' or text()='Apply on company site' or @id='apply-button']"
                
                try:
                    apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, apply_button_xpath)))
                    
                    if "company site" in apply_btn.text.lower():
                        print(f"Skipping Job {i+1}: Redirects to company site.")
                    else:
                        apply_btn.click()
                        print(f"Successfully applied to Job {i+1}")
                        applied_count += 1
                        time.sleep(3)
                except Exception as e:
                    print(f"Job {i+1}: Could not find or click Apply button.")

                # Close job tab and switch back to search
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(2)

            except Exception as e:
                print(f"Error processing Job {i+1}: {str(e)}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        # 4. Final Profile Update (To keep profile 'Recently Updated')
        print("Finalizing with profile refresh...")
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(5)
        # We perform a refresh to trigger the 'last updated' date change on Naukri
        driver.refresh()
        time.sleep(5)
        driver.save_screenshot("final_profile_state.png")

        print(f"COMPLETED: Applied to {applied_count} Java Developer jobs.")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        driver.save_screenshot("fatal_error_apply.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
