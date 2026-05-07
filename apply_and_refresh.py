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
    """Creates the logs directory if missing and saves the screenshot."""
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"{name}_{int(time.time())}.png")
    driver.save_screenshot(path)
    print(f"📸 Screenshot saved: {path}")

def handle_questionnaire(driver, job_idx):
    """
    100% JobSailor Logic Structure:
    Uses their exact try/except flow, element locators, and explicit waits.
    """
    status = True
    wait = WebDriverWait(driver, 10)
    
    # Loop guard to prevent infinite looping if a completely unknown element appears
    loop_guard = 0 
    
    while status and loop_guard < 15:
        loop_guard += 1
        
        try:
            # === JOBSAILOR RADIO BUTTON LOGIC ===
            radio_buttons = WebDriverWait(driver, 2).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ssrc__radio-btn-container"))
            )
            
            print("🤖 Radio buttons found. Selecting Option 1...")
            # Pick the first option instead of using Bard/Gemini
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
                save_screenshot(driver, f"SUCCESS_job_{job_idx}")
                print(f"🎉 Successfully applied to Job {job_idx}!")
                return True

        except Exception as e:
            # === JOBSAILOR FALLBACK LOGIC (Text Area) ===
            try:
                chat_list = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//ul[contains(@id, 'chatList_')]"))
                )
                li_elements = chat_list.find_elements(By.TAG_NAME, "li")
                last_question_text = li_elements[-1].text if li_elements else ""
                
                input_field = driver.find_element(By.XPATH, "//div[@class='textArea']")

                # Hardcoded logic instead of Bard/Gemini
                ans = "2" if "experience" in last_question_text.lower() or "years" in last_question_text.lower() else "yes"
                print(f"🤖 Text field found. Typing: {ans}")
                
                input_field.send_keys(ans)
                time.sleep(1)

                # Exact JobSailor Save Button Logic
                save_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")))
                save_button.click()

                success_message = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"))
                )
                if success_message:
                    status = False
                    save_screenshot(driver, f"SUCCESS_job_{job_idx}")
                    print(f"🎉 Successfully applied to Job {job_idx}!")
                    return True

            except Exception as inner_e:
                # JobSailor Finally / Catch-All Success Check
                try:
                    success_message_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]")
                    if success_message_elements:
                        status = False
                        save_screenshot(driver, f"SUCCESS_job_{job_idx}")
                        print(f"🎉 Successfully applied to Job {job_idx}!")
                        return True
                    else:
                        # No radios, no text box, no success message -> Exit loop
                        status = False
                except:
                    status = False

    # If the while loop breaks without success
    save_screenshot(driver, f"FAIL_incomplete_job_{job_idx}")
    return False

def run_automation():
    print("🚀 Starting Naukri Bot (JobSailor Logic Core)...")
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

        # --- SEARCH LOGIC (Using your specified Pune/1-Yr/Sort-Date URL) ---
        search_url = "https://www.naukri.com/java-developer-jobs-in-pune?k=java%20developer&l=pune&experience=1&nignbevent_src=jobsearchDeskGNB&sort=d"
        driver.get(search_url)
        time.sleep(10)
        
        save_screenshot(driver, "DEBUG_search_results")

        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"🎯 Found {len(links)} potential jobs.")

        applied = 0
        for idx, link in enumerate(links[:20]):
            try:
                driver.get(link)
                time.sleep(random.uniform(5, 8))
                
                # Check if already applied
                if "already applied" in driver.page_source.lower() or driver.find_elements(By.ID, "company-site-button"):
                    continue

                # Click Initial Apply button
                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Starting Apply Process for Job {idx+1}...")
                    
                    # Hand over to JobSailor Questionnaire function
                    if handle_questionnaire(driver, idx+1):
                        applied += 1
                
                # Limit to 10 successful applies to stay under GitHub limits
                if applied >= 10: 
                    break 
            except Exception as e:
                save_screenshot(driver, f"FAIL_exception_job_{idx+1}")
                continue

        print(f"🏁 Total Successful Cycles: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
