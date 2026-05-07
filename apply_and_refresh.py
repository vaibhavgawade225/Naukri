import os
import time
import random
import warnings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
    """JobSailor Logic: Fills chatbot forms without AI and tracks success/failure."""
    status = True
    loop_guard = 0
    last_question = ""

    while status and loop_guard < 8:
        loop_guard += 1
        time.sleep(2)
        
        # 1. SUCCESS CHECK
        success_xpath = "//span[contains(@class, 'apply-message') and contains(text(), 'successfully applied')]"
        if driver.find_elements(By.XPATH, success_xpath) or "successfully applied" in driver.page_source.lower():
            save_screenshot(driver, f"SUCCESS_job_{job_idx}")
            print(f"🎉 Successfully applied to Job {job_idx}!")
            return True

        # 2. ANTI-LOOP PROTECTION
        try:
            current_q = driver.find_element(By.XPATH, "//li[contains(@class, 'botItem')]").text
            if current_q == last_question and loop_guard > 1:
                print("🛑 Bot stuck on the same question. Saving failure screenshot.")
                save_screenshot(driver, f"FAIL_stuck_loop_job_{job_idx}")
                return False
            last_question = current_q
        except: pass

        # 3. FILL QUESTIONS & SAVE
        try:
            # Handle Radio Buttons
            radios = driver.find_elements(By.CSS_SELECTOR, ".ssrc__radio-btn-container")
            if radios:
                print("🤖 Selecting first radio option...")
                first_input = radios[0].find_element(By.CSS_SELECTOR, "input")
                driver.execute_script("arguments[0].click();", first_input)
                time.sleep(1)
                
                # JobSailor's Save Button XPath
                save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div | //div[contains(@class, 'sendMsg')]")
                driver.execute_script("arguments[0].click();", save_btn)
                continue

            # Handle Text Areas
            text_areas = driver.find_elements(By.XPATH, "//div[contains(@class, 'textArea')]")
            if text_areas:
                print("🤖 Entering fallback text...")
                txt_field = text_areas[0].find_element(By.TAG_NAME, "input") if text_areas[0].find_elements(By.TAG_NAME, "input") else text_areas[0]
                ans = "2" if "experience" in driver.page_source.lower() else "yes"
                txt_field.send_keys(ans)
                time.sleep(1)
                
                # JobSailor's Save Button XPath
                save_btn = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div | //div[contains(@class, 'sendMsg')]")
                driver.execute_script("arguments[0].click();", save_btn)
                continue
            
            # Exit loop if no fields exist
            status = False
        except Exception as e:
            status = False
            
    # If the loop finishes without hitting the "Success" check
    save_screenshot(driver, f"FAIL_incomplete_job_{job_idx}")
    return False

def run_automation():
    print("🚀 Starting Hybrid JobSailor Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.add_argument("--disable-notifications")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # --- LOGIN LOGIC (From your working script) ---
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        driver.refresh()
        time.sleep(5)

        # --- SEARCH LOGIC (From your working script) ---
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
                time.sleep(random.uniform(5, 8))
                
                # Check if already applied or external site
                if "already applied" in driver.page_source.lower() or driver.find_elements(By.ID, "company-site-button"):
                    continue

                # Click Apply button
                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Starting Apply Process for Job {idx+1}...")
                    time.sleep(3)
                    
                    # Hand over to JobSailor logic
                    if handle_questionnaire(driver, idx+1):
                        applied += 1
                
                # Stop after hitting limit to stay within time constraints
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
