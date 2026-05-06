import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
load_dotenv()

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {  # Or load from env
    "current_ctc": os.getenv('CURRENT_CTC', '3'),
    "expected_ctc": os.getenv('EXPECTED_CTC', '5'),
    "notice_period": os.getenv('NOTICE_PERIOD', '15'),
    "experience": os.getenv('EXPERIENCE', '2')
}

def get_shadow_root(driver, element):
    """Accesses elements hidden inside Shadow DOM."""
    return driver.execute_script('return arguments[0].shadowRoot', element)

def cdp_type(driver, element, text):
    """
    PRO TECH: Uses Chrome DevTools Protocol to insert text.
    This bypasses React/Vue event listeners by simulating hardware-level input.
    """
    try:
        driver.execute_script("arguments[0].focus();", element)
        time.sleep(0.2)
        # Clear field first
        driver.execute_script("arguments[0].value = '';", element)
        # Hardware-level text insertion
        driver.execute_cdp_cmd('Input.insertText', {'text': str(text)})
        # Trigger validation events
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """, element)
        print(f"   [CDP] Successfully typed: {text}")
    except Exception as e:
        print(f"   [CDP Error] {e}")

def find_all_inputs(driver):
    """Finds all inputs, including those hidden in Shadow DOM."""
    all_inputs = driver.find_elements(By.XPATH, "//input | //textarea | //select")
    # Shadow DOM piercing (Experimental but powerful)
    hosts = driver.find_elements(By.XPATH, "//*[contains(@class, 'naukri')]") # Common Naukri shadow hosts
    for host in hosts:
        try:
            shadow = get_shadow_root(driver, host)
            if shadow:
                all_inputs.extend(shadow.find_elements(By.CSS_SELECTOR, "input, textarea, select"))
        except: continue
    return all_inputs

def handle_questionnaire(driver, job_idx):
    wait = WebDriverWait(driver, 10)
    max_steps = 8  # Increased for multi-page forms
    
    for step in range(1, max_steps + 1):
        print(f"   Step {step}: Waiting for form...")
        time.sleep(3)
        driver.save_screenshot(f"output/JOB_{job_idx}_STEP_{step}.png")  # Save to output/

        # Switch to iframe if present (common in Naukri popups)
        try:
            iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
            print("   Switched to iframe")
        except TimeoutException:
            pass  # No iframe

        # Targeted field finders
        fields = []

        # Text inputs/textareas (prioritize by common Naukri attrs)
        text_fields = driver.find_elements(By.CSS_SELECTOR, 
            "input[type='text'], input[type='number'], input[type='email'], textarea, [role='textbox']")
        fields.extend(text_fields)

        # Radios: Find inputs + associated labels
        radio_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        for radio in radio_inputs:
            if radio.is_displayed():
                fields.append(radio)
                # Click label too for React trigger
                try:
                    label = driver.execute_script("return arguments[0].closest('label') || arguments[0].previousElementSibling;", radio)
                    if label: fields.append(label)
                except: pass

        # Checkboxes (bonus)
        check_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        fields.extend(check_fields)

        # Selects
        selects = driver.find_elements(By.TAG_NAME, "select")
        fields.extend(selects)

        if not fields:
            print(f"   No fields found. Likely complete.")
            driver.switch_to.default_content()
            return True

        # Process fields
        for field in fields:
            if not field.is_displayed(): continue
            
            # Scroll and hover
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
            ActionChains(driver).move_to_element(field).perform()
            time.sleep(0.5)

            ctx = (field.get_attribute('placeholder') or '' + ' ' +
                   field.get_attribute('name') or '' + ' ' +
                   field.get_attribute('label') or '' + ' ' +
                   field.text).lower()

            print(f"   Processing field ctx: {ctx[:50]}...")

            if field.tag_name == 'input' and field.get_attribute('type') == 'radio':
                # Radio: Select based on positive keywords, click label/input
                if any(kw in ctx for kw in ['yes', 'willing', 'agree', 'immediate', '15', 'relocate']):
                    try:
                        field.click()
                        print("   Radio selected")
                    except: pass

            elif field.tag_name == 'input' and field.get_attribute('type') == 'checkbox':
                field.click()  # Default check positives
                print("   Checkbox checked")

            elif field.tag_name in ['input', 'textarea']:
                val = "Yes"
                if any(k in ctx for k in ['current', 'ctc', 'salary']): val = MY_PROFILE_DATA['current_ctc']
                elif any(k in ctx for k in ['expect', 'ctc', 'salary']): val = MY_PROFILE_DATA['expected_ctc']
                elif any(k in ctx for k in ['notice', 'join']): val = MY_PROFILE_DATA['notice_period']
                elif 'experi' in ctx: val = MY_PROFILE_DATA['experience']
                cdp_type(driver, field, val)  # Keep your CDP func

            elif field.tag_name == 'select':
                try:
                    sel = Select(field)
                    sel.select_by_visible_text("Yes")  # Or first option
                    print("   Select set")
                except: pass

        # Find & click Next/Save (more selectors)
        save_selectors = [
            "//button[contains(translate(text(), 'SAVE', 'save'), 'save')]",
            "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]",
            "//button[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]",
            "//span[contains(text(), 'Continue')]/parent::button",
            "[data-automation='save-continue']"
        ]
        save_btn = None
        for sel in save_selectors:
            try:
                save_btn = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                break
            except TimeoutException:
                continue

        if save_btn:
            driver.execute_script("arguments[0].click();", save_btn)
            print(f"   Step {step} submitted")
        else:
            print(f"   No submit btn; assuming done")
            break

        driver.switch_to.default_content()  # Exit iframe

    print(f"✅ Job {job_idx} questionnaire complete")
    return True
    
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        return False

def run_automation():
    print("🚀 Starting Advanced CDP-Based Bot...")
    cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", fix_hairline=True)

    try:
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        driver.refresh()
        time.sleep(5)

        driver.get("https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f")
        time.sleep(10)

        links = [el.get_attribute('href') for el in driver.find_elements(By.CSS_SELECTOR, "a.title") if el.get_attribute('href')]
        print(f"Found {len(links)} jobs.")

        applied = 0
        for idx, link in enumerate(links[:15]):
            try:
                driver.get(link)
                time.sleep(random.uniform(7, 10))
                
                if "already applied" in driver.page_source.lower(): continue

                apply_btns = driver.find_elements(By.XPATH, "//button[text()='Apply' or contains(text(), 'Apply')]")
                if apply_btns and apply_btns[0].is_displayed():
                    driver.execute_script("arguments[0].click();", apply_btns[0])
                    print(f"✅ Applying to Job {idx+1}")
                    handle_questionnaire(driver, idx+1)
                    applied += 1
                
                if applied >= 5: break 
            except: continue

        print(f"🏁 Final Applied Count: {applied}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_automation()
