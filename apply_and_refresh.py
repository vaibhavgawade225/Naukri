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
    """Finds inputs, forces focus, and types like a physical keyboard."""
    found_inputs = False
    clicked_save = False

    try:
        # 1. Broad search: Inputs, Textareas, Selects, and Content-Editable Divs
        inputs = driver.find_elements(By.XPATH, "//input | //textarea | //select | //*[@contenteditable='true']")
        
        for field in inputs:
            try:
                field_type = field.get_attribute("type")
                if field_type in ["hidden", "submit", "button", "file"]:
                    continue # Ignore background code elements
                    
                # Get surrounding text to understand the question
                html_ctx = driver.execute_script("return arguments[0].outerHTML + (arguments[0].parentElement ? arguments[0].parentElement.innerText : '');", field).lower()
            except: 
                continue # Skip if element goes stale
                
            found_inputs = True
            
            # --- RADIO & CHECKBOXES ---
            if field_type in ["radio", "checkbox"]:
                if any(k in html_ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                    # PRO FIX: Click the hidden input AND its visual wrapper to trigger the React state
                    driver.execute_script("arguments[0].click(); if(arguments[0].parentElement) arguments[0].parentElement.click();", field)
                    time.sleep(0.2)
            
            # --- SELECT DROPDOWNS ---
            elif field.tag_name == "select":
                driver.execute_script("arguments[0].selectedIndex = 1; arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", field)

            # --- TEXT & NUMBER FIELDS ---
            elif field.tag_name in ["input", "textarea"] or field.get_attribute("contenteditable") == "true":
                val = "Yes"
                if "current" in html_ctx and "ctc" in html_ctx: val = MY_PROFILE_DATA["current_ctc"]
                elif "expected" in html_ctx and "ctc" in html_ctx: val = MY_PROFILE_DATA["expected_ctc"]
                elif "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]
                elif "experience" in html_ctx: val = MY_PROFILE_DATA["experience"]
                
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
                    time.sleep(0.5)
                    
                    # PRO FIX: 1. Force Focus and Clear via JavaScript
                    driver.execute_script("arguments[0].focus(); arguments[0].value = '';", field)
                    time.sleep(0.2)
                    
                    # PRO FIX: 2. Hardware-Level Typing via ActionChains
                    ActionChains(driver).send_keys(str(val)).perform()
                    
                    # PRO FIX: 3. Dispatch manual events so the "Save" button wakes up
                    driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                    """, field)
                    time.sleep(0.5)
                except: pass

        # 2. Click Save/Submit/Next/Apply
        buttons = driver.find_elements(By.XPATH, "//button")
        for btn in buttons:
            try:
                if not btn.is_displayed(): continue
                btn_text = btn.text.lower()
                if any(word in btn_text for word in ["save", "submit", "next", "apply"]):
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    # Click via JS bypasses pop-up blockers
                    driver.execute_script("arguments[0].click();", btn)
                    clicked_save = True
                    print("   🚀 Clicked Submit/Next button.")
                    break
            except: continue

    except Exception as e:
        pass 

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
