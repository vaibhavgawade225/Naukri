import os
import time
import csv
import json
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth # Ensure you have pip install selenium-stealth
from gemini_api import bard_flash_response

# --- CONFIGURATION ---
RUNNING_IN_GITHUB = os.environ.get('GITHUB_ACTIONS') == 'true'

options = Options()
if RUNNING_IN_GITHUB:
    options.add_argument("--headless")
    # For GitHub Actions, we use the default environment driver
    driver = webdriver.Firefox(options=options)
else:
    # LOCAL PATHS
    driver_path = "Specify your geckodriver path" 
    options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    service = Service(driver_path)
    driver = webdriver.Firefox(service=service, options=options)

# --- APPLY STEALTH ---
stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True)

wait = WebDriverWait(driver, 10)
csv_file = "jobs.csv"
applied_count = 0

def inject_cookies():
    """Injects cookies to bypass login. Uses 'NAUKRI_COOKIE' secret in GitHub."""
    driver.get("https://www.naukri.com/")
    time.sleep(2)
    
    # Expects cookies in JSON format: [{"name": "...", "value": "..."}, ...]
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    if cookies_raw:
        cookies = json.loads(cookies_raw)
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error adding cookie: {e}")
        driver.refresh()
        print("🍪 Cookies injected and session refreshed.")

def capture_result(name, job_url):
    """Captures a screenshot for success or failure."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    clean_url = job_url.split('/')[-1][:20]
    filename = f"{name}_{clean_url}_{timestamp}.png"
    driver.save_screenshot(filename)
    print(f"📸 Screenshot saved: {filename}")

def force_save_click():
    """Human-like click on the sendMsg div you identified."""
    try:
        # Targeting the specific div you inspected: <div class="sendMsg">Save</div>
        save_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class, 'sendMsg') and text()='Save']")
        ))
        
        driver.execute_script("""
            let target = arguments[0];
            let wrapper = target.closest('.send') || target.parentElement;
            if (wrapper) wrapper.classList.remove('disabled');
            target.classList.remove('disabled');

            ['mousedown', 'mouseup', 'click'].forEach(name => {
                target.dispatchEvent(new MouseEvent(name, {bubbles: true, view: window}));
            });
        """, save_btn)
        return True
    except Exception:
        return False

# --- MAIN WORKFLOW ---
inject_cookies()

with open(csv_file, 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        job_url = f"https://www.naukri.com{row[0]}"
        driver.get(job_url)
        time.sleep(3)
        
        try:
            # Check if already applied
            if driver.find_elements(By.ID, "already-applied"):
                print(f"⏩ Already applied for {row[0]}")
                continue

            # Hit the main Apply button
            driver.find_element(By.XPATH, "//*[text()='Apply']").click()
            time.sleep(4)

            # Chatbot Questionnaire Loop
            status = True
            while status:
                # 1. Handle Radios
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    q_text = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]").text
                    ans_idx = int(bard_flash_response(f"Question: {q_text}\nOptions: {[r.text for r in radios]}"))
                    driver.execute_script("arguments[0].click();", radios[ans_idx-1].find_element(By.TAG_NAME, "input"))
                    force_save_click()
                    time.sleep(2)
                
                # 2. Handle Text Input
                elif driver.find_elements(By.CLASS_NAME, "textArea"):
                    q_text = driver.find_elements(By.TAG_NAME, "li")[-1].text
                    ans = bard_flash_response(q_text)
                    driver.find_element(By.CLASS_NAME, "textArea").send_keys(ans)
                    force_save_click()
                    time.sleep(2)

                # Check Success
                if "successfully applied" in driver.page_source.lower():
                    print(f"✅ Successfully applied: {row[0]}")
                    capture_result("SUCCESS", job_url)
                    applied_count += 1
                    status = False
                
                # Safety break for loops
                if "error" in driver.page_source.lower():
                    capture_result("ERROR", job_url)
                    status = False

        except Exception as e:
            print(f"❌ Error applying for {row[0]}: {e}")
            capture_result("EXCEPTION", job_url)

driver.quit()
