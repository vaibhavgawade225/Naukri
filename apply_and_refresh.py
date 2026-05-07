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
wait = WebDriverWait(driver, 10)

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
        print("✅ Login verified.")
    except Exception as e: print(f"❌ Cookie Error: {e}")

def get_job_links_via_query():
    print("🔍 Performing live search for 'Java Developer'...")
    driver.get("https://www.naukri.com/")
    time.sleep(3)
    try:
        role_input = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "suggestor-input")))
        role_input.send_keys("Java Developer")
        loc_input = driver.find_elements(By.CLASS_NAME, "suggestor-input")[1]
        loc_input.send_keys("Pune, Mumbai")
        search_btn = driver.find_element(By.CLASS_NAME, "qsbSubmit")
        driver.execute_script("arguments[0].click();", search_btn)
        time.sleep(5)
    except:
        driver.get("https://www.naukri.com/java-developer-jobs-in-mumbai-pune?k=java%20developer&l=mumbai%2C%20pune&experience=0&sort=d")
    
    links = []
    job_elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
    for el in job_elements:
        href = el.get_attribute("href")
        if href and "/job-listings" in href: links.append(href)
    return links[:20]

# --- START ---
inject_cookies()
job_links = get_job_links_via_query()

for job_url in job_links:
    if applied_count >= MAX_APPLIES: break
    print(f"🚀 Visiting: {job_url.split('/')[-1][:30]}")
    driver.get(job_url)
    time.sleep(4)

    try:
        if "already applied" in driver.page_source.lower():
            print("⏩ Already applied.")
            continue
        if driver.find_elements(By.ID, "company-site-button"):
            print("⏩ External site job (skipping).")
            continue

        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Apply']")))
        driver.execute_script("arguments[0].click();", apply_btn)
        print("🖱️ Apply clicked.")
        time.sleep(5)

        # --- CHATBOT LOOP WITH 2s WAIT ---
        status = True
        loop_guard = 0
        while status and loop_guard < 10:
            loop_guard += 1
            if "successfully applied" in driver.page_source.lower():
                applied_count += 1
                save_screenshot(f"success_{applied_count}")
                print(f"🎉 Success! Total: {applied_count}")
                break

            try:
                # 1. Radio Buttons
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    driver.execute_script("arguments[0].click();", radios[0].find_element(By.TAG_NAME, "input"))
                    time.sleep(1)
                    
                    # JobSailor's Save Button XPath
                    save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")
                    driver.execute_script("arguments[0].click();", save_btn)
                    
                    print("⌛ Waiting 2s for next question...")
                    time.sleep(2) # <--- THE 2 SECOND WAIT
                    continue

                # 2. Text Areas
                text_areas = driver.find_elements(By.CLASS_NAME, "textArea")
                if text_areas:
                    ans = "2" if "experience" in driver.page_source.lower() else "yes"
                    text_areas[0].send_keys(ans)
                    time.sleep(1)
                    
                    save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")
                    driver.execute_script("arguments[0].click();", save_btn)
                    
                    print("⌛ Waiting 2s for next question...")
                    time.sleep(2) # <--- THE 2 SECOND WAIT
                    continue
                
                status = False
            except: status = False

    except Exception as e:
        print(f"❌ Skipped: {type(e).__name__}")

driver.quit()
