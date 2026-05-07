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

# --- CLEANUP & CONFIG ---
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

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

# --- HELPER FUNCTIONS ---
def save_screenshot(name):
    """Creates the logs directory if missing and saves the screenshot."""
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"{name}_{int(time.time())}.png")
    driver.save_screenshot(path)
    print(f"📸 Screenshot saved: {path}")

def inject_cookies():
    """Robust cookie injection handling both JSON and Raw Text formats."""
    print("🔄 Injecting cookies...")
    driver.get("https://www.naukri.com/")
    time.sleep(3)
    cookies_raw = os.environ.get('NAUKRI_COOKIE')
    
    if not cookies_raw:
        print("❌ No cookies found in secrets.")
        return
        
    try:
        cookies_raw = cookies_raw.strip()
        if cookies_raw.startswith('['):
            for c in json.loads(cookies_raw):
                driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.naukri.com'})
        else:
            for pair in cookies_raw.split(';'):
                if '=' in pair:
                    n, v = pair.strip().split('=', 1)
                    driver.add_cookie({'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com'})
        driver.refresh()
        time.sleep(3)
        print("✅ Cookie injection successful.")
    except Exception as e:
        print(f"❌ Cookie Error: {e}")

def get_job_links():
    """Searches jobs using the exact URL Naukri generated, sorted by date."""
    print("🔍 Searching for Java Developer jobs (Pune, 1 Yr Exp, Date Sort)...")
    url = "https://www.naukri.com/java-developer-jobs-in-pune?k=java%20developer&l=pune&experience=1&nignbevent_src=jobsearchDeskGNB&sort=d"
    driver.get(url)
    time.sleep(5)
    
    save_screenshot("search_page_verification")
    
    links = []
    elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'title') or contains(@href, '/job-listings')]")
    for el in elements:
        href = el.get_attribute("href")
        if href and isinstance(href, str) and "/job-listings" in href and href not in links:
            links.append(href)

    print(f"🎯 Found {len(links)} valid links.")
    return links[:15]

# --- MAIN AUTOMATION ---
inject_cookies()
job_links = get_job_links()

for job_url in job_links:
    if applied_count >= MAX_APPLIES:
        print("🏁 Maximum applies reached for today.")
        break
        
    print(f"\n🚀 Visiting: {job_url.split('/')[-1][:40]}")
    driver.get(job_url)
    time.sleep(3)

    try:
        if driver.find_elements(By.ID, "already-applied"):
            print("⏩ Already applied. Skipping.")
            continue
        if driver.find_elements(By.ID, "company-site-button"):
            print("⏩ External site (company-site-button). Skipping.")
            continue
        if "expired" in driver.page_source.lower():
            print("⏩ Job expired. Skipping.")
            continue

        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Apply']")))
        driver.execute_script("arguments[0].click();", apply_btn)
        print("🖱️ Apply clicked. Starting questionnaire...")
        time.sleep(3)

        status = True
        loop_guard = 0
        last_question = ""

        while status and loop_guard < 8:
            loop_guard += 1
            time.sleep(2)
            
            success_xpath = "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"
            if driver.find_elements(By.XPATH, success_xpath) or "successfully applied" in driver.page_source.lower():
                applied_count += 1
                save_screenshot(f"SUCCESS_job_{applied_count}")
                print(f"🎉 Successfully applied! (Total: {applied_count})")
                status = False
                break

            try:
                current_q = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]").text
                if current_q == last_question and loop_guard > 1:
                    print("🛑 Bot stuck on same question. Saving failure screenshot.")
                    save_screenshot("FAIL_stuck_in_loop")
                    status = False
                    break
                last_question = current_q
            except: pass

            try:
                radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
                if radios:
                    print("🤖 Selecting first radio option...")
                    first_input = radios[0].find_element(By.CSS_SELECTOR, "input")
                    driver.execute_script("arguments[0].click();", first_input)
                    time.sleep(1)
                    
                    save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div | //div[contains(@class, 'sendMsg')]")
                    driver.execute_script("arguments[0].click();", save_btn)
                    continue

                text_areas = driver.find_elements(By.XPATH, "//div[contains(@class, 'textArea')]")
                if text_areas:
                    print("🤖 Entering fallback text...")
                    txt_field = text_areas[0].find_element(By.TAG_NAME, "input") if text_areas[0].find_elements(By.TAG_NAME, "input") else text_areas[0]
                    ans = "2" if "experience" in driver.page_source.lower() else "yes"
                    txt_field.send_keys(ans)
                    time.sleep(1)
                    
                    save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div | //div[contains(@class, 'sendMsg')]")
                    driver.execute_script("arguments[0].click();", save_btn)
                    continue
                
                status = False

            # THIS WAS THE MISSING EXCEPT BLOCK FOR THE INNER TRY
            except Exception as e:
                status = False

    # THIS IS THE EXCEPT BLOCK FOR THE OUTER TRY (The job application process)
    except Exception as e:
        error_name = type(e).__name__
        print(f"❌ Error during application: {error_name}")
        save_screenshot(f"FAIL_{error_name}")

driver.quit()
