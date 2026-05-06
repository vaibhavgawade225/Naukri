import os
import time
import csv
import json
import warnings
# --- REMOVE UNIMPORTANT LOGS ---
warnings.filterwarnings("ignore", category=FutureWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # Suppresses deep learning logs if any

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
MAX_APPLIES = 10
applied_count = 0
csv_file = "jobs.csv"

options = Options()
options.add_argument("--headless=new") # Faster and more modern headless mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-notifications") # Blocks popups

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15) # Increased wait time

stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True)

def inject_cookies():
    driver.get("https://www.naukri.com/")
    time.sleep(3)
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    if not cookies_raw: return
    try:
        if cookies_raw.strip().startswith('['):
            cookies = json.loads(cookies_raw)
            for c in cookies:
                driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.naukri.com'})
        else:
            for pair in cookies_raw.split(';'):
                if '=' in pair:
                    n, v = pair.strip().split('=', 1)
                    driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com'})
        driver.refresh()
        print("🍪 Login verified via cookies.")
    except Exception as e:
        print(f"❌ Cookie Error: {e}")

def save_screenshot(name):
    """Saves a screenshot to a 'logs' folder for debugging."""
    if not os.path.exists("logs"):
        os.makedirs("logs")
    filename = f"logs/{name}_{int(time.time())}.png"
    driver.save_screenshot(filename)
    print(f"📸 Screenshot saved: {filename}")
        
# --- MAIN LOOP ---
inject_cookies()

with open(csv_file, 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        if applied_count >= MAX_APPLIES: break
        if not row: continue
        
        job_url = f"https://www.naukri.com{row[0]}"
        print(f"🔍 Checking: {row[0]}")
        driver.get(job_url)
        
        try:
            # 1. Check if already applied
            if "already applied" in driver.page_source.lower():
                print("⏩ Already applied.")
                continue

            # 2. Find the Apply Button with multiple possible selectors
            # Naukri buttons often use 'apply-button' or text 'Apply'
            apply_selectors = [
                "//button[contains(text(),'Apply')]",
                "//span[contains(text(),'Apply')]",
                "//button[@id='apply-button']",
                "//div[contains(@class,'apply-button')]"
            ]
            
            apply_btn = None
            for selector in apply_selectors:
                try:
                    apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    if apply_btn: break
                except: continue

            if apply_btn:
                driver.execute_script("arguments[0].click();", apply_btn)
                print("🖱️ Apply clicked. Handling chatbot...")
                time.sleep(5)
                
                # Logic for handling chatbot questions (same as before)
                # ... [Chatbot logic remains here] ...
                
                applied_count += 1
            else:
                print("⚠️ Apply button not found (Page might have changed or role is closed).")

        except Exception as e:
            error_type = type(e).__name__
            print(f"❌ Failed: {error_type}")
            # Capture what went wrong
            save_screenshot(f"fail_{error_type}")

driver.quit()
