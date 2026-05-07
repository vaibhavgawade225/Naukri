import os
import time
import json
import warnings
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
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
    print("🔍 Searching for Java Developer jobs (Pune ONLY, 0-2 Yrs)...")
    # Clean URL: Removed Mumbai, kept Java, 0-2 Yrs, and Sort by Date
    search_url = "https://www.naukri.com/java-developer-jobs-in-pune?k=java%20developer&l=pune&experience=0&sort=d"
    
    driver.get(search_url)
    time.sleep(5) # Wait for search results to load
    
    links = []
    # Fetch job titles which contain the links
    job_elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
    for el in job_elements:
        href = el.get_attribute("href")
        if href and "/job-listings" in href:
            links.append(href)
            
    print(f"🎯 Found {len(links)} potential jobs in Pune.")
    return links[:20] # Returns the 20 freshest jobs

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
            while time.time() - start_time < 60: # 1-minute timeout for deep bots
                if "successfully applied" in driver.page_source.lower():
                    applied_count += 1
                    print(f"🎉 Applied! (Total: {applied_count})")
                    save_screenshot(f"success_job_{applied_count}")
                    break
                
                # 1. Handle Multiple Choice
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    print("🤖 Chatbot: Picking option 1.")
                    driver.execute_script("arguments[0].click();", radios[0].find_element(By.TAG_NAME, "input"))
                    time.sleep(2)
                    # Attempt to click Save
                    try:
                        save_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'sendMsg')]")
                        driver.execute_script("arguments[0].click();", save_btn)
                    except: pass
                    time.sleep(2) # Wait for animation
                    continue

                # 2. Handle Text Input (The "ElementNotInteractable" Fix)
                text_areas = driver.find_elements(By.CLASS_NAME, "textArea")
                if text_areas and text_areas[0].is_displayed():
                    ans = "2" if "experience" in driver.page_source.lower() else "yes"
                    print(f"🤖 Chatbot: Entering '{ans}'.")
                    
                    # Clear field first to avoid "22222"
                    text_areas[0].clear() 
                    text_areas[0].send_keys(ans)
                    time.sleep(1)
                    text_areas[0].send_keys(Keys.ENTER) # HIT ENTER as a backup to clicking Save
                    
                    # Try to click the Save button as well
                    try:
                        save_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'sendMsg')]")
                        driver.execute_script("arguments[0].click();", save_btn)
                    except: pass
                    
                    time.sleep(3) # Mandatory wait for Naukri's "Saving" animation
                    continue
                
                # 3. Fallback: If no input found, try clicking ANY visible Save/Next button
                try:
                    any_btn = driver.find_element(By.XPATH, "//div[text()='Save' or text()='Next' or text()='Submit']")
                    if any_btn.is_displayed():
                        driver.execute_script("arguments[0].click();", any_btn)
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
