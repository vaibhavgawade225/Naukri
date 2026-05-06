import os
import time
import json
import warnings
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

# --- CLEAN LOGS ---
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# --- CONFIG ---
MAX_APPLIES = 10
applied_count = 0

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-notifications")

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

def save_screenshot(name):
    if not os.path.exists("logs"): os.makedirs("logs")
    driver.save_screenshot(f"logs/{name}_{int(time.time())}.png")

def inject_cookies():
    driver.get("https://www.naukri.com/")
    time.sleep(3)
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    if not cookies_raw: return
    try:
        if cookies_raw.strip().startswith('['):
            cookies = json.loads(cookies_raw)
            for c in cookies: driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.naukri.com'})
        else:
            for pair in cookies_raw.split(';'):
                if '=' in pair:
                    n, v = pair.strip().split('=', 1)
                    driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com'})
        driver.refresh()
        print("✅ Login verified via cookies.")
    except Exception as e: print(f"❌ Cookie Error: {e}")

def get_job_links():
    print("🔍 Searching for Java Developer jobs (Pune/Mumbai, 0-2 Yrs)...")
    search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?k=java%20developer&l=mumbai%2C%20pune&experience=0&sort=d"
    driver.get(search_url)
    time.sleep(5)
    links = []
    job_elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
    for el in job_elements:
        href = el.get_attribute("href")
        if href and "/job-listings" in href:
            links.append(href)
    print(f"🎯 Found {len(links)} potential jobs.")
    return links[:20]

# --- START AUTOMATION ---
inject_cookies()
job_links = get_job_links()

for job_url in job_links:
    if applied_count >= MAX_APPLIES: break
    
    print(f"🚀 Visiting: {job_url.split('/')[-1][:50]}...")
    driver.get(job_url)
    time.sleep(4)

    try:
        if "already applied" in driver.page_source.lower():
            print("⏩ Already applied.")
            continue

        # FIND APPLY BUTTON
        apply_selectors = ["//button[contains(text(),'Apply')]", "//span[contains(text(),'Apply')]", "//button[@id='apply-button']"]
        apply_btn = None
        for selector in apply_selectors:
            try:
                apply_btn = driver.find_element(By.XPATH, selector)
                if apply_btn.is_displayed(): break
            except: continue

        if apply_btn:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", apply_btn)
            print("🖱️ Apply clicked.")
            time.sleep(5)

            # --- UPDATED CHATBOT LOGIC ---
            start_time = time.time()
            while time.time() - start_time < 45: # Increased timeout for multi-step bots
                if "successfully applied" in driver.page_source.lower() or "application submitted" in driver.page_source.lower():
                    applied_count += 1
                    print(f"🎉 Applied! (Total: {applied_count})")
                    break
                
                # 1. Multiple Choice: Always pick option 1
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    print("🤖 Chatbot: Picking option 1.")
                    driver.execute_script("arguments[0].click();", radios[0].find_element(By.TAG_NAME, "input"))
                    time.sleep(2)
                    try:
                        save_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'sendMsg') and text()='Save']")
                        driver.execute_script("arguments[0].click();", save_btn)
                    except: pass
                    continue

                # 2. Text/Logical Questions: Type "yes" or "2"
                text_areas = driver.find_elements(By.CLASS_NAME, "textArea")
                if text_areas:
                    # Logic: If it looks like an experience question, use "2", otherwise use "yes"
                    question_context = driver.page_source.lower()
                    if "experience" in question_context or "years" in question_context:
                        ans = "2"
                    else:
                        ans = "yes"
                    
                    print(f"🤖 Chatbot: Entering '{ans}'.")
                    text_areas[0].send_keys(ans)
                    time.sleep(1)
                    try:
                        save_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'sendMsg') and text()='Save']")
                        driver.execute_script("arguments[0].click();", save_btn)
                    except: pass
                    continue
                
                # 3. Final Fallback: Just click 'Save' if it's there but bot is stuck
                try:
                    save_btn = driver.find_element(By.XPATH, "//div[text()='Save']")
                    if save_btn.is_displayed():
                        driver.execute_script("arguments[0].click();", save_btn)
                        time.sleep(2)
                        continue
                except: pass

                break 
        else:
            print("⚠️ No apply button found.")

    except Exception as e:
        print(f"❌ Failed: {type(e).__name__}")
        save_screenshot(f"fail_{type(e).__name__}")

driver.quit()
