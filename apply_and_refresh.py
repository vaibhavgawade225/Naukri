import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

# Profile data from env secrets
MY_PROFILE_DATA = {
    "current_ctc": os.getenv('CURRENT_CTC', '3'),
    "expected_ctc": os.getenv('EXPECTED_CTC', '5'),
    "notice_period": os.getenv('NOTICE_PERIOD', '15'),
    "experience": os.getenv('EXPERIENCE', '2')
}

def get_shadow_root(driver, element):
    """Access Shadow DOM elements."""
    return driver.execute_script('return arguments[0].shadowRoot', element)

def cdp_type(driver, element, text):
    """CDP text insertion bypassing React events."""
    try:
        driver.execute_script("arguments[0].focus();", element)
        time.sleep(0.2)
        driver.execute_script("arguments[0].value = '';", element)
        driver.execute_cdp_cmd('Input.insertText', {'text': str(text)})
        driver.execute_script("""
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """, element)
        print(f"   [CDP] Typed: {text}")
    except Exception as e:
        print(f"   [CDP Error] {e}")

def handle_questionnaire(driver, job_idx):
    """Fixed questionnaire handler with iframes, waits, radios."""
    wait = WebDriverWait(driver, 12)
    max_steps = 8
    
    try:
        for step in range(1, max_steps + 1):
            print(f"   Job {job_idx} Step {step}: Waiting...")
            time.sleep(3)
            
            # Screenshot for debug
            try:
                os.makedirs('output', exist_ok=True)
                driver.save_screenshot(f"output/JOB_{job_idx}_STEP_{step}.png")
            except: pass

            # Handle iframe
            try:
                iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                driver.switch_to.frame(iframe)
                print("   → Entered iframe")
            except TimeoutException:
                pass

            # Find all field types
            fields = []
            
            # Text/textarea
            text_fields = driver.find_elements(By.CSS_SELECTOR, 
                "input[type='text'], input[type='number'], input[type='email'], textarea, [role='textbox']")
            fields.extend(text_fields)
            
            # Radios + labels
            radio_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            for radio in radio_inputs:
                if radio.is_displayed():
                    fields.append(radio)
                    try:
                        label = driver.execute_script(
                            "return arguments[0].closest('label') || arguments[0].previousElementSibling;", radio)
                        if label: fields.append(label)
                    except: pass
            
            # Checkboxes
            fields.extend(driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"))
            
            # Selects
            fields.extend(driver.find_elements(By.TAG_NAME, "select"))

            if not fields:
                print(f"   No fields. Complete.")
                driver.switch_to.default_content()
                return True

            # Process fields
            for field in fields:
                if not field.is_displayed(): continue
                
                # Human-like interaction
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
                ActionChains(driver).move_to_element(field).perform()
                time.sleep(random.uniform(0.3, 0.7))

                # Context for decision
                ctx = (field.get_attribute('placeholder') or '' + ' ' +
                       field.get_attribute('name') or '' + ' ' +
                       field.get_attribute('aria-label') or '' + ' ' +
                       field.text).lower()[:100]

                print(f"   Field ctx: {ctx}")

                # Radio/Checkbox logic
                if field.tag_name == 'input':
                    if field.get_attribute('type') == 'radio':
                        if any(kw in ctx for kw in ['yes', 'willing', 'agree', 'immediate', '15', 'relocate']):
                            try:
                                field.click()
                                print("   ✓ Radio selected")
                            except: pass
                    elif field.get_attribute('type') == 'checkbox':
                        field.click()
                        print("   ✓ Checkbox checked")

                # Text fields - CDP
                elif field.tag_name in ['input', 'textarea'] and field.get_attribute('type') not in ['radio', 'checkbox']:
                    val = "Yes"
                    if any(k in ctx for k in ['current', 'ctc', 'salary']): val = MY_PROFILE_DATA['current_ctc']
                    elif any(k in ctx for k in ['expect', 'ctc', 'target']): val = MY_PROFILE_DATA['expected_ctc']
                    elif any(k in ctx for k in ['notice', 'join', 'available']): val = MY_PROFILE_DATA['notice_period']
                    elif 'experi' in ctx: val = MY_PROFILE_DATA['experience']
                    cdp_type(driver, field, val)

                # Select dropdowns
                elif field.tag_name == 'select':
                    try:
                        sel = Select(field)
                        options = [o.text for o in sel.options]
                        if 'Yes' in options:
                            sel.select_by_visible_text("Yes")
                        else:
                            sel.select_by_index(1)  # First non-empty
                        print("   ✓ Select set")
                    except: pass

            # Find submit button (expanded selectors)
            save_selectors = [
                "//button[contains(translate(text(),'SAVE','save'),'save')]",
                "//button[contains(translate(text(),'NEXT','next'),'next')]",
                "//button[contains(translate(text(),'CONTINUE','continue'),'continue')]",
                "//button[contains(translate(text(),'SUBMIT','submit'),'submit')]",
                "//span[contains(text(),'Continue')]/parent::button",
                "//button[contains(@class,'save') or contains(@class,'next')]",
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
                driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", save_btn)
                print(f"   ✓ Step {step} submitted")
            else:
                print(f"   No button found; assuming complete")
                break

            driver.switch_to.default_content()

        print(f"✅ Job {job_idx} complete")
        return True

    except Exception as e:
        print(f"❌ Questionnaire error: {e}")
        driver.switch_to.default_content()
        return False

def run_automation():
    """Main automation loop."""
    print("🚀 Naukri Auto-Apply Bot v2.0")
    cookie_raw = os.getenv('NAUKRI_COOKIE', '').strip()
    
    if not cookie_raw:
        print("❌ NAUKRI_COOKIE env var missing!")
        return

    # GitHub Actions optimized options
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-web-security")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    
    # Auto ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        # Login via cookies
        driver.get("https://www.naukri.com/")
        time.sleep(5)
        
        for item in cookie_raw.split(';'):
            if '=' in item:
                n, v = item.strip().split('=', 1)
                driver.add_cookie({'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'})
        
        driver.refresh()
        time.sleep(8)
        print("✓ Logged in via cookies")

        # Job search
        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        driver.get(search_url)
        time.sleep(12)

        links = [el.get_attribute('href') for el in 
                driver.find_elements(By.CSS_SELECTOR, "a[data-automation='jobTitle']") 
                if el.get_attribute('href')]
        print(f"Found {len(links)} Java dev jobs")

        applied = 0
        for idx, link in enumerate(links[:10]):  # Reduced limit
            try:
                print(f"\n--- Job {idx+1}: {link} ---")
                driver.get(link)
                time.sleep(random.uniform(8, 12))
                
                if "already applied" in driver.page_source.lower():
                    print("  Skip: Already applied")
                    continue

                # Easy Apply button
                apply_btns = driver.find_elements(By.XPATH, 
                    "//button[contains(translate(text(),'APPLY','apply'),'apply') or contains(@class,'apply')]")
                
                if apply_btns:
                    apply_btn = apply_btns[0]
                    driver.execute_script("arguments[0].scrollIntoView(true);", apply_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", apply_btn)
                    print(f"  → Apply clicked")
                    
                    if handle_questionnaire(driver, idx+1):
                        applied += 1
                        print(f"  ✓ Applied successfully!")
                
                if applied >= 3:  # Conservative limit
                    break
                    
            except Exception as e:
                print(f"  Job {idx+1} error: {e}")
                continue

        print(f"\n🏁 Session complete. Applied: {applied}/{len(links)} jobs")

    except Exception as e:
        print(f"❌ Fatal: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    os.makedirs('output', exist_ok=True)
    run_automation()
