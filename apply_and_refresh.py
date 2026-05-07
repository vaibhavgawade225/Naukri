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
    if not os.path.exists("logs"): os.makedirs("logs")
    driver.save_screenshot(f"logs/{name}_{int(time.time())}.png")

def inject_cookies():
    driver.get("https://www.naukri.com/")
    time.sleep(2)
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    if not cookies_raw: return
    try:
        cookies = json.loads(cookies_raw) if cookies_raw.startswith('[') else []
        for c in cookies: driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.naukri.com'})
        driver.refresh()
    except: pass

def get_job_links():
    """Fixed link scraping logic to avoid TypeError."""
    try:
        url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?k=java%20developer&l=mumbai%2C%20pune&experience=0&sort=d"
        driver.get(url)
    except:
        driver.get("https://www.naukri.com/developer-jobs?experience=0&experience=1&experience=2")
    
    time.sleep(3)
    links = []
    elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
    for el in elements:
        href = el.get_attribute("href")
        # FIXED: Added check for 'if href' to prevent NoneType error
        if href and "/job-listings" in href:
            links.append(href)
    
    print(f"🎯 Found {len(links)} links.")
    return links[:15]

# --- START ---
inject_cookies()
job_links = get_job_links()

for job_url in job_links:
    if applied_count >= MAX_APPLIES: break
    driver.get(job_url)
    time.sleep(2)

    try:
        if "already applied" in driver.page_source.lower() or driver.find_elements(By.ID, "company-site-button"):
            continue

        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Apply']")))
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(3)

        # --- CHATBOT LOGIC ---
        last_q_text = ""
        for _ in range(6): # Fast loop limit
            if "successfully applied" in driver.page_source.lower():
                applied_count += 1
                save_screenshot(f"success_{applied_count}")
                break

            # Prevent repeat answers
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
                
                # 2. Text Area
                elif driver.find_elements(By.CLASS_NAME, "textArea"):
                    txt = driver.find_element(By.CLASS_NAME, "textArea")
                    ans = "2" if "experience" in driver.page_source.lower() else "yes"
                    txt.send_keys(ans)
                    txt.send_keys(Keys.ENTER)

                # Save Button (JobSailor style)
                save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")
                driver.execute_script("arguments[0].click();", save_btn)
                time.sleep(2) # Cooldown
            except: break
            
    except: continue

driver.quit()
