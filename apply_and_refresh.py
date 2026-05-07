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
wait = WebDriverWait(driver, 5) # Reduced from 10 to 5 for speed

stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

def save_screenshot(name):
    if not os.path.exists("logs"): os.makedirs("logs")
    driver.save_screenshot(f"logs/{name}_{int(time.time())}.png")

def inject_cookies():
    driver.get("https://www.naukri.com/")
    time.sleep(2) # Reduced
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    if not cookies_raw: return
    try:
        cookies = json.loads(cookies_raw) if cookies_raw.startswith('[') else []
        for c in cookies: driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.naukri.com'})
        driver.refresh()
    except: pass

def get_job_links():
    """Fast search using your preferred query and backup."""
    try:
        # Use the specific Pune/Mumbai query directly for speed
        url = "https://www.naukri.com/developer-jobs?experience=0&experience=1&experience=2"
        driver.get(url)
    except:
        driver.get("https://www.naukri.com/java-developer-jobs-in-mumbai-pune?k=java%20developer&l=mumbai%2C%20pune&experience=0&sort=d")
    
    time.sleep(3) # Reduced from 5
    links = [el.get_attribute("href") for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if "/job-listings" in el.get_attribute("href")]
    return links[:15] # Limit to 15 to stay under 3 mins

# --- START ---
inject_cookies()
job_links = get_job_links()

for job_url in job_links:
    if applied_count >= MAX_APPLIES: break
    driver.get(job_url)
    time.sleep(2) # Reduced

    try:
        # Fast Checks
        page_text = driver.page_source.lower()
        if "already applied" in page_text or driver.find_elements(By.ID, "company-site-button"):
            continue

        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Apply']")))
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(3)

        # --- CHATBOT: NO REPEAT LOGIC ---
        last_question = ""
        loop_guard = 0
        
        while loop_guard < 6: # Fewer steps to save time
            loop_guard += 1
            if "successfully applied" in driver.page_source.lower():
                applied_count += 1
                save_screenshot(f"success_{applied_count}")
                print(f"🎉 Success {applied_count}")
                break

            # Identify current question to prevent repeats
            try:
                current_q = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]").text
                if current_q == last_question:
                    print("🛑 Question hasn't changed. Skipping to avoid loop.")
                    break
                last_question = current_q
            except: pass

            try:
                # 1. Radios
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    driver.execute_script("arguments[0].click();", radios[0].find_element(By.TAG_NAME, "input"))
                
                # 2. Text
                elif driver.find_elements(By.CLASS_NAME, "textArea"):
                    txt = driver.find_element(By.CLASS_NAME, "textArea")
                    ans = "2" if "experience" in driver.page_source.lower() else "yes"
                    txt.send_keys(ans)
                    txt.send_keys(Keys.ENTER)

                # Click Save (Precise XPath)
                save_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'sendMsg')] | //div[text()='Save']")
                driver.execute_script("arguments[0].click();", save_btn)
                time.sleep(2) 
            except: break
            
    except: continue

driver.quit()
