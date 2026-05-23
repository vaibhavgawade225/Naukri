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

warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# ─── CONFIG ───────────────────────────────────────────────
EMAIL      = os.environ.get("NAUKRI_USER", "")
PASSWORD   = os.environ.get("NAUKRI_PASS", "")
SEARCH_URL = "https://www.naukri.com/software-testing-software-tester-software-test-engineer-qa-testing-sdet-test-engineering-manual-testing-jobs-in-mumbai-all-areas?k=software%20testing%2C%20software%20tester%2C%20software%20test%20engineer%2C%20qa%20testing%2C%20sdet%2C%20test%20engineering%2C%20manual%20testing&l=mumbai%20(all%20areas)%2C%20pune%2C%20bengaluru%2C%20new%20delhi%2C%20noida%2C%20greater%20noida%2C%20hyderabad&experience=2&nignbevent_src=jobsearchDeskGNB"
MAX_APPLY  = 10
# ──────────────────────────────────────────────────────────

def save_screenshot(driver, name):
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"{name}_{int(time.time())}.png")
    driver.save_screenshot(path)
    print(f"📸 Screenshot: {path}")

def login_naukri(driver, email, password):
    print("🔐 Logging in...")
    driver.get("https://www.naukri.com/nlogin/login")
    time.sleep(3)
    wait = WebDriverWait(driver, 10)

    try:
        email_field = wait.until(EC.presence_of_element_located((By.ID, "usernameField")))
        email_field.clear()
        email_field.send_keys(email)

        pass_field = driver.find_element(By.ID, "passwordField")
        pass_field.clear()
        pass_field.send_keys(password)

        login_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Login')]")
        ))
        driver.execute_script("arguments[0].click();", login_btn)
        time.sleep(5)

        save_screenshot(driver, "after_login")
        print("✅ Login successful.")
    except Exception as e:
        save_screenshot(driver, "login_error")
        print(f"❌ Login failed: {e}")
        raise

def refresh_profile(driver):
    """
    Updates profile headline to push it to the top of recruiter searches.
    """
    print("🔄 Refreshing profile to boost visibility...")
    try:
        driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(5)
        save_screenshot(driver, "profile_page")

        # Click edit on headline/summary section
        edit_btns = driver.find_elements(By.XPATH,
            "//span[contains(@class,'edit') or contains(@class,'pencil')]")
        if edit_btns:
            driver.execute_script("arguments[0].click();", edit_btns[0])
            time.sleep(2)

            # Find headline input and update it with a small change
            headline = driver.find_elements(By.XPATH,
                "//input[contains(@placeholder,'headline') or contains(@name,'headline')]")
            if headline:
                current = headline[0].get_attribute("value")
                headline[0].clear()
                headline[0].send_keys(current.strip())
                time.sleep(1)

                # Save
                save_btn = driver.find_elements(By.XPATH,
                    "//button[contains(text(),'Save')]")
                if save_btn:
                    driver.execute_script("arguments[0].click();", save_btn[0])
                    time.sleep(2)
                    print("✅ Profile refreshed successfully!")
                    save_screenshot(driver, "profile_refreshed")
                else:
                    print("⚠ Save button not found.")
            else:
                print("⚠ Headline field not found.")
        else:
            print("⚠ Edit button not found on profile.")

    except Exception as e:
        print(f"⚠ Profile refresh failed: {e}")
        save_screenshot(driver, "profile_refresh_error")

def handle_questionnaire(driver, job_idx):
    status = True
    wait = WebDriverWait(driver, 10)
    already_applied = driver.find_elements(By.ID, "already-applied")
    loop_guard = 0

    while status and loop_guard < 15:
        loop_guard += 1

        try:
            radio_buttons = WebDriverWait(driver, 1).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ssrc__radio-btn-container"))
            )
            question = driver.find_element(By.XPATH,
                "//li[contains(@class, 'botItem')]/div/div/span").text
            print(f"❓ Question: {question}")

            selected = radio_buttons[0].find_element(By.CSS_SELECTOR, "input")
            driver.execute_script("arguments[0].click();", selected)

            save_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")
            ))
            save_btn.click()

            success = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH,
                    "//span[contains(@class,'apply-message') and contains(text(),'successfully applied')]"))
            )
            if success:
                status = False

        except Exception as e:
            print(f"Radio fallback triggered: {e}")
            try:
                chat_list = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, "//ul[contains(@id,'chatList_')]"))
                )
                li_elements = chat_list.find_elements(By.TAG_NAME, "li")
                last_q = li_elements[-1].text if li_elements else ""
                print(f"Last question: {last_q}")

                input_field = driver.find_element(By.XPATH, "//div[@class='textArea']")
                ans = "2" if "experience" in last_q.lower() or "years" in last_q.lower() else "yes"
                input_field.send_keys(ans)
                time.sleep(1)

                save_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/div/div[1]/div[3]/div/div")
                ))
                save_btn.click()

                success = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH,
                        "//span[contains(@class,'apply-message') and contains(text(),'successfully applied')]"))
                )
                if success:
                    status = False

            except Exception as inner_e:
                if already_applied:
                    status = False
                elif driver.find_elements(By.XPATH,
                        "//div[contains(@class,'apply-status-header') and contains(@class,'green')]"):
                    continue
                print(f"Inner error: {inner_e}")

            finally:
                done = driver.find_elements(By.XPATH,
                    "//span[contains(@class,'apply-message') and contains(text(),'You have successfully applied')]")
                if done:
                    status = False

    if not status:
        save_screenshot(driver, f"SUCCESS_job_{job_idx}")
        print(f"🎉 Applied to Job {job_idx}!")
        return True
    else:
        save_screenshot(driver, f"FAIL_job_{job_idx}")
        return False

def run_automation():
    print("🚀 Starting bot...")

    if not EMAIL or not PASSWORD:
        print("❌ NAUKRI_USER or NAUKRI_PASS environment variable is missing!")
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Login
        login_naukri(driver, EMAIL, PASSWORD)

        # Step 2: Refresh profile to boost visibility
        refresh_profile(driver)

        # Step 3: Search and apply jobs
        driver.get(SEARCH_URL)
        time.sleep(10)
        save_screenshot(driver, "search_results")

        links = [
            el.get_attribute('href')
            for el in driver.find_elements(By.CSS_SELECTOR, "a.title")
            if el.get_attribute('href')
        ]
        print(f"🎯 Found {len(links)} jobs.")

        applied = 0
        for idx, link in enumerate(links[:30]):
            if applied >= MAX_APPLY:
                break
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))

                if "already applied" in driver.page_source.lower():
                    print(f"⏭ Job {idx+1}: Already applied, skipping.")
                    continue
                if driver.find_elements(By.ID, "company-site-button"):
                    print(f"⏭ Job {idx+1}: External site, skipping.")
                    continue

                apply_btns = driver.find_elements(By.XPATH,
                    "//button[text()='Apply' or contains(text(),'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"📨 Applying to Job {idx+1}...")
                    if handle_questionnaire(driver, idx+1):
                        applied += 1

            except Exception as e:
                print(f"⚠ Job {idx+1} skipped: {e}")
                continue

        print(f"\n🏁 Done! Successfully applied to {applied} job(s).")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()