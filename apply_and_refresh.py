import os
import time
import random
import warnings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# --- CLEANUP ---
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

def save_screenshot(driver, name):
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"{name}_{int(time.time())}.png")
    driver.save_screenshot(path)
    print(f"📸 Screenshot saved: {path}")

def handle_questionnaire(driver, job_idx):
    """
    100% PURE JOBSAILOR LOGIC:
    Uses their exact try/except block, locators, and save logic.
    """
    status = True
    wait = WebDriverWait(driver, 10)
    already_applied_elements = driver.find_elements(By.ID, "already-applied")
    loop_guard = 0
    
    while status and loop_guard < 15:
        loop_guard += 1
        
        try:
            # === JOBSAILOR RADIO LOGIC ===
            radio_buttons = WebDriverWait(driver, 1).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ssrc__radio-btn-container"))
            )
            
            question = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]/div/div/span").text
            print(f"Question: {question}")
            
            # Select Option 1 (No AI)
            selected_button = radio_buttons[0].find_element(By.CSS_SELECTOR, "input")
            driver.execute_script("arguments[0].click();", selected_button)

            # Exact JobSailor Save Button Logic
            save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")))
            save_button.click()

            # Exact JobSailor Success Check
            success_message = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"))
            )
            if success_message:
                status = False

        except Exception as e:
            print(f"Error during radio button selection or saving: {e}")
            
            # === JOBSAILOR FALLBACK LOGIC (Text Box) ===
            try:
                chat_list = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, "//ul[contains(@id, 'chatList_')]"))
                )
                li_elements = chat_list.find_elements(By.TAG_NAME, "li")
                last_question_text = None
                
                if li_elements:
                    last_li_element = li_elements[-1]
                    last_question_text = last_li_element.text
                    print("Last question text:", last_question_text)
                else:
                    print("No <li> elements found.")

                input_field = driver.find_element(By.XPATH, "//div[@class='textArea']")

                # Hardcoded logic instead of Bard/Gemini
                ans = "2" if last_question_text and ("experience" in last_question_text.lower() or "years" in last_question_text.lower()) else "yes"
                
                input_field.send_keys(ans)
                time.sleep(1)

                # Exact JobSailor Save Button Logic
                save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")))
                save_button.click()

                apply_status_header = driver.find_elements(By.XPATH,"//div[contains(@class, 'apply-status-header') and contains(@class, 'green')]")
                
                success_message = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"))
                )
                if success_message:
                    status = False

                if apply_status_header:
                    print("The element exists.")
                else:
                    print("The element does not exist.")

            except Exception as inner_e:
                # === JOBSAILOR ERROR/FINALLY CATCH ===
                if already_applied_elements:
                    status = False
                elif driver.find_elements(By.XPATH,"//div[contains(@class, 'apply-status-header') and contains(@class, 'green')]"):
                    continue
                print(f"Error during fallback procedure: {inner_e}")
                
            finally:
                success_message_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'You have successfully applied')]")
                if success_message_elements:
                    status = False

    # Return Result
    if not status:
        save_screenshot(driver, f"SUCCESS_job_{job_idx}")
        print(f"🎉 Successfully applied to Job {job_idx}!")
        return True
    else:
        save_screenshot(driver, f"FAIL_stuck_job_{job_idx}")
        return False

def run_automation():
    print("🚀 Starting Pro-Level Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # --- LOGIN LOGIC ---
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        driver.refresh()
        time.sleep(5)

        # --- SEARCH LOGIC (Using your exact URL snippet) ---
        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(10)
        
        save_screenshot(driver, "DEBUG_search_results")

        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"🎯 Found {len(links)} potential jobs.")

        applied = 0
        for idx, link in enumerate(links[:20]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                # Pre-Checks
                if "already applied" in driver.page_source.lower() or driver.find_elements(By.ID, "company-site-button"):
                    continue

                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Starting Apply Process for Job {idx+1}...")
                    
                    if handle_questionnaire(driver, idx+1):
                        applied += 1
                
                if applied >= 5: 
                    break 
            except Exception as e:
                print(f"Skipping job {idx+1} due to error: {e}")
                continue

        print(f"🏁 Total Successful Cycles: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
