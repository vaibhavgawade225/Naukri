import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

def run_automation():
    print("🚀 Starting Stealth Java Apply (0-2 Yrs)...")
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
        # 1. Login Handshake
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # 2. Search Page
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)
        
        if "access denied" in driver.page_source.lower():
            print("⚠️ Search blocked. Hard refreshing...")
            driver.refresh()
            time.sleep(12)

        # Get job links directly
        job_links = []
        cards = driver.find_elements(By.XPATH, "//a[@class='title ']")
        for link in cards[:15]:
            job_links.append(link.get_attribute('href'))
        
        print(f"Found {len(job_links)} potential jobs. Starting application...")

        applied_count = 0
        for idx, link in enumerate(job_links):
            try:
                print(f"⏳ Processing Job {idx+1}...")
                # Open in SAME tab to avoid multi-window detection
                driver.get(link)
                time.sleep(random.uniform(8, 12))

                # Handle Access Denied on Job Page
                if "access denied" in driver.page_source.lower() or "403" in driver.title:
                    print(f"🚫 Blocked on Job {idx+1}. Refreshing...")
                    driver.refresh()
                    time.sleep(10)

                # Try to find Apply button
                # Using multiple XPATHs for different Naukri layouts
                apply_selectors = [
                    "//button[text()='Apply']",
                    "//button[contains(text(), 'Apply')]",
                    "//button[@id='apply-button']",
                    "//span[text()='Apply']"
                ]
                
                apply_btn = None
                for selector in apply_selectors:
                    found = driver.find_elements(By.XPATH, selector)
                    if found and found[0].is_displayed():
                        apply_btn = found[0]
                        break

                if apply_btn:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_btn)
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();", apply_btn)
                    print(f"✅ SUCCESS: Applied to Job {idx+1}")
                    time.sleep(5)
                    driver.save_screenshot(f"applied_{idx+1}.png")
                    applied_count += 1
                else:
                    # Logic to explain WHY it failed
                    page_text = driver.page_source.lower()
                    if "already applied" in page_text:
                        print(f"ℹ️ Job {idx+1}: Already applied.")
                    elif "login" in page_text:
                        print(f"❌ Job {idx+1}: Logged out! Cookies might be expired.")
                    else:
                        print(f"⚠️ Job {idx+1}: Button missing (Check screenshot).")
                        driver.save_screenshot(f"error_job_{idx+1}.png")

                if applied_count >= 5:
                    break
                
                # Go back to search results or move to next link
                time.sleep(random.uniform(4, 7))

            except Exception as e:
                print(f"❌ Critical error at Job {idx+1}")

        print(f"🏁 Final Status: {applied_count} jobs applied.")

    except Exception as e:
        print(f"🔥 Fatal Error: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
