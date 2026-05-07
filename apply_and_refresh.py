import os
import time
import json
import warnings
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
wait = WebDriverWait(driver, 5)

stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

def save_screenshot(name):
    log_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_dir): os.makedirs(log_dir)
    path = os.path.join(log_dir, f"{name}_{int(time.time())}.png")
    driver.save_screenshot(path)
    print(f"📸 Saved: {path}")

def inject_cookies():
    print("🔄 Injecting cookies...")
    driver.get("https://www.naukri.com/")
    time.sleep(3)
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    
    if not cookies_raw: 
        print("❌ No cookies found in secrets.")
        return
        
    try:
        # FIX: Restored robust cookie parsing for both JSON and Raw Text
        if cookies_raw.strip().startswith('['):
            cookies = json.loads(cookies_raw)
            for c in cookies: driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.naukri.com'})
        else:
            for pair in cookies_raw.split(';'):
                if '=' in pair:
                    n, v = pair.strip().split('=', 1)
                    driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com'})
        
        driver.refresh()
        time.sleep(3)
        print("✅ Cookie injection finished.")
    except Exception as e: 
        print(f"❌ Cookie Error: {e}")

def get_job_links():
    print("🔍 Searching Jobs (Sorted by Date)...")
    try:
        # Main Search: Ensure &sort=d is present
        url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?k=java%20developer&l=mumbai%2C%20pune&experience=0&sort=d"
        driver.get(url)
    except:
        # Fallback Search: Added &sort=d here too!
        driver.get("https://www.naukri.com/developer-jobs?experience=0&sort=d")
    
    time.sleep(4)
    # Take a screenshot to verify login state and sorting
    save_screenshot("search_results") 
    
    links = []
    elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
    for el in elements:
        href = el.get_attribute("href")
        if href and isinstance(href, str) and "/job-listings" in href:
            links.append(href)
    
    print(f"🎯 Found {len(links)} valid links.")
    return links[:15]

# --- START ---
inject_cookies()
job_links = get_job_links()

for job_url in job_links:
    if applied_count >= MAX_APPLIES: break
    print(f"🚀 Visiting Job...")
    driver.get(job_url)
    time.sleep(2)

    try:
        if "already applied" in driver.page_source.lower() or driver.find_elements(By.ID, "company-site-button"):
            print("⏩ Skipping (Already Applied or External)")
            continue

        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Apply']")))
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(3)

        # --- CHATBOT: ANTI-REPEAT LOGIC ---
        last_q_text = ""
        for _ in range(6): 
            if "successfully applied" in driver.page_source.lower():
                applied_count += 1
                save_screenshot(f"success_{applied_count}")
                print(f"🎉 Applied to Job {applied_count}")
                break

            try:
                current_q = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]").text
                if current_q == last_q_text: break
                last_q_text = current_q
            except: pass

            try:
                # 1. Radio Buttons
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    driver.execute_script("arguments[0].click();", radios[0].find_element(By.TAG_NAME, "input"))
                
                # 2. Text Areas
                elif driver.find_elements(By.CLASS_NAME, "textArea"):
                    txt = driver.find_element(By.CLASS_NAME, "textArea")
                    ans = "2" if "experience" in driver.page_source.lower() else "yes"
                    txt.send_keys(ans)
                    txt.send_keys(Keys.ENTER)

                # Save Button
                save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div | //div[contains(@class, 'sendMsg')]")
                driver.execute_script("arguments[0].click();", save_btn)
                time.sleep(2) 
            except: break
            
    except: continue

driver.quit()
