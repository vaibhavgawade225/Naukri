import os
import time
import csv
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from gemini_api import bard_flash_response

# --- CONFIGURATION ---
MAX_APPLIES = 10  # Your requested limit
applied_count = 0
csv_file = "jobs.csv"
RUNNING_IN_GITHUB = os.environ.get('GITHUB_ACTIONS') == 'true'

# --- FAST CHROME SETUP ---
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

# Use ChromeDriverManager to avoid manual geckodriver "time wasting"
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

# --- STEALTH MODE ---
stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True)

def inject_cookies():
    """Smarter cookie injection that handles both JSON and raw text formats."""
    print("🔄 Attempting to inject cookies...")
    driver.get("https://www.naukri.com/")
    time.sleep(3)
    
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    
    if not cookies_raw:
        print("❌ No cookies found in GitHub Secrets (NAUKRI_COOKIE is empty).")
        return

    try:
        cookies_raw = cookies_raw.strip()
        
        # LOGIC 1: If it looks like a JSON array (e.g., from EditThisCookie)
        if cookies_raw.startswith('['):
            cookies = json.loads(cookies_raw)
            for cookie in cookies:
                # Safely extract only what Selenium needs
                cookie_dict = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain', '.naukri.com'),
                    'path': cookie.get('path', '/')
                }
                driver.add_cookie(cookie_dict)
                
        # LOGIC 2: If it's a raw header string (e.g., "NID=123; session=abc")
        else:
            print("⚠️ Cookies are not in JSON format. Parsing as raw text...")
            cookie_pairs = cookies_raw.split(';')
            for pair in cookie_pairs:
                if '=' in pair:
                    name, value = pair.strip().split('=', 1)
                    driver.add_cookie({
                        'name': name.strip(), 
                        'value': value.strip(), 
                        'domain': '.naukri.com'
                    })
                    
        driver.refresh()
        time.sleep(3)
        
        # Verify if login was successful by checking for a common logged-in element
        if "login" not in driver.current_url.lower():
            print("🍪 Cookies injected and login verified successfully!")
        else:
            print("⚠️ Cookies injected, but Naukri still shows the login page. They might be expired.")

    except Exception as e:
        print(f"❌ Cookie Logic Error: {e}")

def force_save_click():
    """Precision click for the 'Save' button."""
    try:
        save_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'sendMsg') and text()='Save']")
        ))
        driver.execute_script("""
            arguments[0].classList.remove('disabled');
            arguments[0].click();
        """, save_btn)
        return True
    except:
        return False

# --- MAIN LOOP ---
inject_cookies()

if not os.path.exists(csv_file):
    print(f"❌ Error: {csv_file} not found!")
    exit()

with open(csv_file, 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        # 🛑 THE LIMIT CHECK
        if applied_count >= MAX_APPLIES:
            print(f"🎯 Reached limit of {MAX_APPLIES} applies. Mission accomplished.")
            break
        
        if not row: continue
        job_url = f"https://www.naukri.com{row[0]}"
        print(f"🔍 Checking Job: {row[0]}")
        driver.get(job_url)
        time.sleep(3)

        try:
            if driver.find_elements(By.ID, "already-applied"):
                print("⏩ Already applied. Skipping...")
                continue

            driver.find_element(By.XPATH, "//*[text()='Apply']").click()
            time.sleep(4)

            # Chatbot Questionnaire
            status = True
            while status:
                if "successfully applied" in driver.page_source.lower():
                    print(f"✅ Applied! Total: {applied_count + 1}")
                    applied_count += 1
                    status = False
                    break

                # Handle Radios
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    q_text = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]").text
                    ans_idx = int(bard_flash_response(f"Q: {q_text} Options: {[r.text for r in radios]}"))
                    driver.execute_script("arguments[0].click();", radios[ans_idx-1].find_element(By.TAG_NAME, "input"))
                    force_save_click()
                    time.sleep(2)
                
                # Handle Text
                elif driver.find_elements(By.CLASS_NAME, "textArea"):
                    q_text = driver.find_elements(By.TAG_NAME, "li")[-1].text
                    ans = bard_flash_response(q_text)
                    driver.find_element(By.CLASS_NAME, "textArea").send_keys(ans)
                    force_save_click()
                    time.sleep(2)
                else:
                    status = False # End loop if no interaction found

        except Exception as e:
            print(f"❌ Failed: {row[0]}")

driver.quit()
