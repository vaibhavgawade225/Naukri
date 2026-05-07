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

for job_idx, job_url in enumerate(job_links, 1):
    if applied_count >= MAX_APPLIES:
        print("🏁 Maximum applies reached for today.")
        break
        
    print(f"\n🚀 Visiting Job {job_idx}: {job_url.split('/')[-1][:40]}")
    driver.get(job_url)
    time.sleep(3)

    try:
        # Pre-apply checks
        if driver.find_elements(By.ID, "already-applied") or driver.find_elements(By.ID, "company-site-button"):
            print("⏩ Already applied or External site. Skipping.")
            continue

        # Click initial apply button
        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[text()='Apply']")))
        driver.execute_script("arguments[0].click();", apply_btn)
        print("🖱️ Apply clicked. Starting JobSailor questionnaire logic...")
        
        # Initial success check (JobSailor style)
        try:
            success_message = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH,"//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"))
            )
            applied_count += 1
            print("🎉 Successfully applied! (No questionnaire needed)")
            save_screenshot(f"SUCCESS_job_{job_idx}")
            continue
        except:
            pass # Move into questionnaire loop

        # ==========================================
        # EXACT JOBSAILOR QUESTIONNAIRE LOGIC
        # ==========================================
        status = True
        loop_guard = 0
        
        while status and loop_guard < 12:
            loop_guard += 1
            time.sleep(1)
            
            try:
                # 1. Try Radio Buttons First
                radio_buttons = WebDriverWait(driver, 2).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ssrc__radio-btn-container"))
                )
                print("🤖 JobSailor: Selecting first radio option...")
                selected_button = radio_buttons[0].find_element(By.CSS_SELECTOR, "input")
                driver.execute_script("arguments[0].click();", selected_button)

                # JobSailor Save Button
                save_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")))
                driver.execute_script("arguments[0].click();", save_button)

                # JobSailor Success Check
                try:
                    success_message = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"))
                    )
                    if success_message:
                        status = False
                except: pass

            except Exception as e:
                # 2. Fallback to Text Area
                try:
                    chat_list = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, "//ul[contains(@id, 'chatList_')]"))
                    )
                    li_elements = chat_list.find_elements(By.TAG_NAME, "li")
                    last_question_text = li_elements[-1].text if li_elements else ""
                    
                    print(f"🤖 JobSailor: Text Area detected. Question: '{last_question_text[:30]}...'")
                    input_field = driver.find_element(By.XPATH, "//div[@class='textArea']")
                    
                    # Rule-based logic instead of Gemini API
                    ans = "2" if "experience" in last_question_text.lower() or "years" in last_question_text.lower() else "yes"
                    
                    # Try to find input inside the div, else use the div
                    try:
                        input_box = input_field.find_element(By.TAG_NAME, "input")
                        input_box.send_keys(ans)
                    except:
                        input_field.send_keys(ans)
                        
                    time.sleep(1)

                    # JobSailor Save Button
                    save_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")))
                    driver.execute_script("arguments[0].click();", save_button)

                    # JobSailor Success Check
                    try:
                        success_message = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"))
                        )
                        if success_message:
                            status = False
                    except: pass

                except Exception as fallback_e:
                    # 3. Final Catch-All / Status Header check
                    try:
                        if driver.find_elements(By.XPATH,"//div[contains(@class, 'apply-status-header') and contains(@class, 'green')]"):
                            continue
                        # If absolutely no elements found, it might be stuck or a captcha
                        if not driver.find_elements(By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"):
                            status = False # Break loop if lost
                    except: pass

            finally:
                # JobSailor Final Success Validation
                success_message_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]")
                if success_message_elements:
                    status = False
        
        # After loop finishes, count success or fail
        if not status and driver.find_elements(By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"):
            applied_count += 1
            print(f"🎉 Successfully applied! (Total: {applied_count})")
            save_screenshot(f"SUCCESS_job_{job_idx}")
        else:
            print("⚠️ Questionnaire failed or timed out.")
            save_screenshot(f"FAIL_questionnaire_job_{job_idx}")

    except Exception as e:
        error_name = type(e).__name__
        print(f"❌ Error during application: {error_name}")
        save_screenshot(f"FAIL_{error_name}_job_{job_idx}")

driver.quit()
