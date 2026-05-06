import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

def force_react_input(driver, element, value):
    """Bypasses React's synthetic events to force text into the box."""
    js_injector = """
    let input = arguments[0];
    let value = arguments[1];
    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
    let nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
    
    if (input.tagName === 'INPUT' && nativeInputValueSetter) {
        nativeInputValueSetter.set.call(input, value);
    } else if (input.tagName === 'TEXTAREA' && nativeTextAreaValueSetter) {
        nativeTextAreaValueSetter.set.call(input, value);
    } else {
        input.value = value;
    }
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    input.dispatchEvent(new Event('blur', { bubbles: true }));
    """
    driver.execute_script(js_injector, element, value)

def process_inputs_and_save(driver):
    """Finds inputs in the current frame, fills them, and clicks save."""
    found_inputs = False
    clicked_save = False

    try:
        # 1. Fill Inputs
        inputs = driver.find_elements(By.XPATH, "//input[not(@type='hidden')] | //textarea | //select")
        for field in inputs:
            if not field.is_displayed(): continue
            
            found_inputs = True
            # Get text around the field to figure out the question
            html_ctx = driver.execute_script("return arguments[0].outerHTML + (arguments[0].parentElement ? arguments[0].parentElement.innerText : '');", field).lower()
            
            field_type = field.get_attribute("type")
            if field_type in ["radio", "checkbox"]:
                if any(k in html_ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                    driver.execute_script("arguments[0].click();", field)
            
            elif field.tag_name in ["input", "textarea"]:
                val = "Yes" # Default fallback
                if "current" in html_ctx and "ctc" in html_ctx: val = MY_PROFILE_DATA["current_ctc"]
                elif "expected" in html_ctx and "ctc" in html_ctx: val = MY_PROFILE_DATA["expected_ctc"]
                elif "notice" in html_ctx: val = MY_PROFILE_DATA["notice_period"]
                elif "experience" in html_ctx: val = MY_PROFILE_DATA["experience"]
                
                force_react_input(driver, field, val)

        # 2. Click Save/Submit
        buttons = driver.find_elements(By.XPATH, "//button")
        for btn in buttons:
            if not btn.is_displayed(): continue
            btn_text = btn.text.lower()
            if any(word in btn_text for word in ["save", "submit", "next", "apply"]):
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn)
                clicked_save = True
                print("   🚀 Clicked Submit/Save button.")
                break
                
    except Exception as e:
        pass # Ignore StaleElement errors while searching

    return found_inputs, clicked_save

def handle_questionnaire(driver, job_idx):
    """Checks the main page, then deeply checks all iframes."""
    for step in range(1, 6):
        time.sleep(5)
        driver.save_screenshot(f"JOB_{job_idx}_STEP_{step}_START.png")
        
        # 1. Try Main Page First
        driver.switch_to.default_content()
        found, clicked = process_inputs_and_save(driver)

        # 2. If nothing found, deeply search all iframes (Chatbots/Popups)
        if not found and not clicked:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                try:
                    driver.switch_to.frame(frame)
                    f_found, f_clicked = process_inputs_and_save(driver)
                    if f_found or f_clicked:
                        found = found or f_found
                        clicked = clicked or f_clicked
                        break # Found the active frame
                except: pass
                finally:
                    driver.switch_to.default_content()

        if not found and not clicked:
            print(f"   ✅ Job {job_idx}: Form finished or no inputs found at Step {step}.")
            break
        
        time.sleep(3)

def run_automation():
    print("🚀 Starting Selenium Stealth + Iframe Injector Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    
    # This is the magic that bypasses Cloudflare Access Denied
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
        
        driver.save_screenshot("SEARCH_RESULTS.png")

        # Robust Link Scraper (Avoids empty arrays)
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
