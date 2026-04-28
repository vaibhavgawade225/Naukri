import os
import time
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# --- YOUR DATA CABINET ---
# Fill these with your actual details for the bot to use
MY_PROFILE_DATA = {
    "experience": "2",            # Years
    "current_ctc": "5,00,000",      # Annual
    "expected_ctc": "7,00,000",     # Annual
    "notice_period": "7",          # Days
    "current_location": "Pune",
    "relocation": "Yes",            # 'Yes' or 'No'
    "notice_period_buyout": "No"    # 'Yes' or 'No'
}

def answer_questions(driver):
    """Detects and intelligently answers common job questions."""
    try:
        # Find all question containers
        question_wrappers = driver.find_elements(By.XPATH, "//div[contains(@class, 'question')] | //li[contains(@class, 'item')]")
        
        for wrapper in question_wrappers:
            text = wrapper.text.lower()
            inputs = wrapper.find_elements(By.XPATH, ".//input | .//select | .//textarea")
            
            if not inputs: continue
            
            # 1. Handle CTC Questions
            if "current ctc" in text or "current salary" in text:
                inputs[0].send_keys(MY_PROFILE_DATA["current_ctc"])
            elif "expected ctc" in text or "expected salary" in text:
                inputs[0].send_keys(MY_PROFILE_DATA["expected_ctc"])
            
            # 2. Handle Notice Period
            elif "notice period" in text or "immidiate joiner" in text:
                if inputs[0].tag_name == "select": # If it's a dropdown
                    inputs[0].send_keys(MY_PROFILE_DATA["notice_period"])
                else:
                    inputs[0].send_keys(MY_PROFILE_DATA["notice_period"])

            # 3. Handle Relocation (Yes/No)
            elif "relocate" in text or "relocation" in text:
                choice = MY_PROFILE_DATA["relocation"].lower()
                for radio in wrapper.find_elements(By.XPATH, ".//input[@type='radio']"):
                    if choice in radio.get_attribute("value").lower() or choice in radio.find_element(By.XPATH, "..").text.lower():
                        driver.execute_script("arguments[0].click();", radio)
                        break

            # 4. Default: If it's a 'Yes/No' and we aren't sure, pick 'Yes' to proceed
            elif "authorized" in text or "visa" in text or "confirm" in text:
                for radio in wrapper.find_elements(By.XPATH, ".//input[@type='radio']"):
                    if "yes" in radio.get_attribute("value").lower() or "yes" in radio.find_element(By.XPATH, "..").text.lower():
                        driver.execute_script("arguments[0].click();", radio)
                        break
        
        # Finally, click Submit if present
        submit_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Save')]")
        if submit_btn:
            submit_btn[0].click()
            print("Questionnaire submitted successfully.")
            
    except Exception as e:
        print(f"Error answering questions: {str(e)}")

def run_automation():
    print("Starting Java Developer Smart-Apply...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        # Step 1: Login via Cookies
        driver.get("https://www.naukri.com/")
        time.sleep(4)
        for item in cookie_raw.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.naukri.com', 'path': '/'})

        # Step 2: Search Latest Java Jobs
        search_url = "https://www.naukri.com/java-developer-jobs?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(8)

        job_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'srp-jobtuple-wrapper')]")
        
        applied_count = 0
        for i, card in enumerate(job_cards[:7]):
            try:
                # Open job in new tab
                title_link = card.find_element(By.XPATH, ".//a[@class='title ']")
                title_link.click()
                time.sleep(5)
                
                driver.switch_to.window(driver.window_handles[-1])
                driver.save_screenshot(f"job_{i+1}_opening.png")
                
                # Check for Apply Button
                apply_btn = WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply')] | //button[@id='apply-button']"))
                )
                apply_btn.click()
                time.sleep(4)

                # Check for Questionnaire
                if "question" in driver.page_source.lower() or driver.find_elements(By.XPATH, "//div[contains(@class, 'drawer')]"):
                    print(f"Job {i+1}: Questionnaire detected. Invoking Smart-Answer...")
                    answer_questions(driver)
                    time.sleep(3)

                print(f"Job {i+1}: Applied.")
                applied_count += 1
                driver.save_screenshot(f"job_{i+1}_applied.png")

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                print(f"Skipping job {i+1}: {str(e)[:50]}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

        print(f"FINISHED: Total applied this run: {applied_count}")

    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        driver.save_screenshot("fatal_error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
