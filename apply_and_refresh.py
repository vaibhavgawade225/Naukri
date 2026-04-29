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

# --- YOUR DATA CABINET ---
MY_PROFILE_DATA = {
    "experience": "2",            
    "current_ctc": "3,00,000",      
    "expected_ctc": "5,00,000",     
    "notice_period": "7",          
    "current_location": "Pune",
    "relocation": "Yes"
}

def handle_access_denied(driver):
    """Detects Access Denied page and refreshes to bypass."""
    for i in range(2): 
        if "access denied" in driver.page_source.lower() or "403" in driver.title:
            print(f"Access Denied detected. Refresh attempt {i+1}...")
            time.sleep(random.uniform(5, 8))
            driver.refresh()
            time.sleep(10)
        else:
            return True
    return False

def clear_overlays(driver):
    """Forcefully removes any popups or loading layers that block clicks."""
    try:
        driver.execute_script("""
            let overlays = document.querySelectorAll('.layers, .modal, .gnb-overlay, .crossIcon, [class*="close"]');
            overlays.forEach(el => el.click());
        """)
    except:
        pass

def answer_questions(driver):
    """Smart-answer logic for questionnaires."""
    try:
        wrappers = driver.find_elements(By.XPATH, "//div[contains(@class, 'question')] | //li[contains(@class, 'item')]")
        for wrapper in wrappers:
            text = wrapper.text.lower()
            inputs = wrapper.find_elements(By.XPATH, ".//input | .//select | .//textarea")
            if not inputs: continue
            
            if "current ctc" in text: inputs[0].send_keys(MY_PROFILE_DATA["current_ctc"])
            elif "expected ctc" in text: inputs[0].send_keys(MY_PROFILE_DATA["expected_ctc"])
            elif "notice period" in text: inputs[0].send_keys(MY_PROFILE_DATA["notice_period"])
            elif "relocate" in text:
                choice = MY_PROFILE_DATA["relocation"].lower()
                for rb in wrapper.find_elements(By.XPATH, ".//input[@type='radio']"):
                    if choice in rb.get_attribute("value").lower() or choice in rb.find_element(By.XPATH, "..").text.lower():
                        driver.execute_script("arguments[0].click();", rb)
                        break
        
        submit = driver.find_elements(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Save')]")
        if submit: 
            driver.execute_script("arguments[0].click();", submit[0])
    except: pass

def run_automation():
    print("Starting Smart-Apply with Robust Tab Management...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # Freshness Sort
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)
        handle_access_denied(driver)

        applied_count = 0
        
        # Main Loop: Refetch job cards every time to avoid stale elements
        for i in range(7):
            try:
                # 1. Back to main tab and clear junk
                driver.switch_to.window(driver.window_handles[0])
                clear_overlays(driver)
                
                # 2. Refetch cards
                job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
                if i >= len(job_cards): break
                
                card = job_cards[i]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                time.sleep(2)

                # 3. Open job in new tab
                title_link = card.find_element(By.XPATH, ".//a[@class='title ']")
                driver.execute_script("arguments[0].click();", title_link)
                time.sleep(5)
                
                # Switch to new tab
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                else:
                    continue

                # 4. Check for blocking content on job page
                if not handle_access_denied(driver):
                    print(f"Job {i+1}: Blocked by Access Denied.")
                else:
                    driver.save_screenshot(f"job_{i+1}_loaded.png")
                    
                    # 5. Robust Apply Click
                    apply_btn = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']"))
                    )
                    driver.execute_script("arguments[0].click();", apply_btn)
                    print(f"Job {i+1}: Clicked Apply.")
                    time.sleep(5)

                    # 6. Handle Questions
                    if "question" in driver.page_source.lower():
                        answer_questions(driver)
                        time.sleep(3)
                    
                    applied_count += 1
                    print(f"Job {i+1}: Processed.")

            except Exception as e:
                print(f"Job {i+1} Failed: {str(e)[:50]}")
                driver.save_screenshot(f"job_{i+1}_error.png")
            
            finally:
                # 7. Safety: Close all tabs except the main search page
                while len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])

        print(f"FINISHED: Total Processed: {applied_count}")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
