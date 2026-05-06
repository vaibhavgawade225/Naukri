import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

def process_inputs_and_save(driver):
    found_inputs = False
    clicked_save = False

    try:
        # 1. Target all possible input areas
        inputs = driver.find_elements(By.XPATH, "//input | //textarea | //select | //*[@contenteditable='true']")
        
        for field in inputs:
            try:
                field_type = field.get_attribute("type")
                if field_type in ["hidden", "submit", "button", "file"]: continue
                    
                html_ctx = driver.execute_script("return arguments[0].outerHTML + (arguments[0].parentElement ? arguments[0].parentElement.innerText : '');", field).lower()
                found_inputs = True
                
                # --- RADIO & CHECKBOXES ---
                if field_type in ["radio", "checkbox"]:
                    if any(k in html_ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree", "confirm"]):
                        driver.execute_script("arguments[0].click();", field)
                        # Trigger change events so React notices the selection
                        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", field)
                
                # --- TEXT & NUMBER FIELDS ---
                elif field.tag_name in ["input", "textarea"] or field.get_attribute("contenteditable") == "true":
                    val = "Yes"
                    if "current" in html_ctx: val = MY_PROFILE_DATA["current_ctc"]
                    elif "expected" in html_ctx: val = MY_PROFILE_DATA["expected_ctc"]
                    elif "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]
                    elif "experience" in html_ctx: val = MY_PROFILE_DATA["experience"]
                    
                    # PRO FIX: The 'React Wake-up' Sequence
                    driver.execute_script("""
                        var el = arguments[0];
                        var val = arguments[1];
                        el.focus();
                        el.value = val;
                        // Dispatch multiple events to satisfy React/Redux listeners
                        el.dispatchEvent(new Event('keydown', { bubbles: true }));
                        el.dispatchEvent(new Event('keypress', { bubbles: true }));
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('keyup', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                    """, field, val)

            except: continue

        time.sleep(2) # Wait for button to enable

        # 2. Click Save/Submit/Next/Apply
        # We search for buttons by text more aggressively
        buttons = driver.find_elements(By.XPATH, "//button | //input[@type='submit'] | //input[@type='button']")
        for btn in buttons:
            try:
                btn_text = (btn.text or btn.get_attribute("value") or "").lower()
                if any(word in btn_text for word in ["save", "submit", "next", "apply"]):
                    # If button is disabled, force enable it for the click
                    driver.execute_script("arguments[0].removeAttribute('disabled');", btn)
                    driver.execute_script("arguments[0].click();", btn)
                    clicked_save = True
                    print(f"   🚀 Clicked: {btn_text}")
                    break
            except: continue

    except Exception as e:
        print(f"   [!] Error in frame: {e}")

    return found_inputs, clicked_save

def handle_questionnaire(driver, job_idx):
    """Checks main page, then deep-dives into all iframes."""
    for step in range(1, 6):
        time.sleep(6)
        driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_START.png")
        
        # 1. Check Main Window
        driver.switch_to.default_content()
        found, clicked = process_inputs_and_save(driver)

        # 2. If nothing found, check every Iframe (Chatbot Apply Boxes)
        if not found and not clicked:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                try:
                    driver.switch_to.frame(frame)
                    f_found, f_clicked = process_inputs_and_save(driver)
                    if f_found or f_clicked:
                        found, clicked = True, True
                        break
                except: pass
                finally:
                    driver.switch_to.default_content()

        driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_END.png")

        if not found and not clicked:
            print(f"   ✅ Job {job_idx}: Form finished or no inputs found at Step {step}.")
            break
        
        time.sleep(3)

def run_automation():
    print("🚀 Starting Selenium ActionChains Pro Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
            driver.refresh()
            time.sleep(5)

        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(8)
        
        # Scrape Job Links
        job_links = []
        links = driver.find_elements(By.XPATH, "//a[contains(@href, 'job-listings-')]")
        for link in links:
            href = link.get_attribute('href')
            if href and href not in job_links:
                job_links.append(href)

        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                driver.get(link)
                time.sleep(random.uniform(6, 9))
                
                if "already applied" in driver.page_source.lower():
                    continue

                apply_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply') or text()='Apply']")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Starting Apply Process for Job {idx+1}...")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break 
            except Exception as e:
                print(f"   Error on job: {e}")
                continue

        print(f"🏁 Total Successful Cycles: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
