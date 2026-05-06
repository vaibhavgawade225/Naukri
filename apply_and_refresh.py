import os
import asyncio
import random
from playwright.async_api import async_playwright

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

async def handle_questionnaire(page, job_idx):
    """
    Playwright handles questionnaires by automatically waiting for 
    elements and triggering React state updates.
    """
    try:
        # Loop for multi-step questions
        for step in range(1, 6):
            # Wait for any potential popup/question to appear
            await page.wait_for_timeout(5000)
            
            # Take a screenshot to see the questionnaire
            await page.screenshot(path=f"JOB_{job_idx}_STEP_{step}_START.png")

            # 1. FIND ALL INPUTS (Text, Radio, Select)
            # Playwright's locator is much smarter than Selenium's find_elements
            inputs = page.locator("input, textarea, select")
            count = await inputs.count()
            
            if count == 0:
                print(f"   [Step {step}] No questions found. Moving on.")
                break

            for i in range(count):
                field = inputs.nth(i)
                if not await field.is_visible():
                    continue

                # Get context (Placeholder, Name, or surrounding text)
                placeholder = await field.get_attribute("placeholder") or ""
                name = await field.get_attribute("name") or ""
                # Get the text of the parent element to understand the question
                parent_text = await field.evaluate("el => el.parentElement.innerText")
                ctx = (placeholder + " " + name + " " + parent_text).lower()

                field_type = await field.get_attribute("type")

                # --- HANDLING RADIO BUTTONS ---
                if field_type == "radio":
                    if any(k in ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                        await field.click(force=True)

                # --- HANDLING TEXT / NUMBER FIELDS ---
                elif await field.evaluate("el => el.tagName") in ["INPUT", "TEXTAREA"]:
                    val = "YES" # Default for Job 8 type questions
                    if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                    elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                    elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                    elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
                    
                    # .fill() is the "Magic" - it triggers React/Vue events automatically
                    await field.fill(val)
                    await field.press("Tab") # Trigger blur event

                # --- HANDLING DROPDOWNS ---
                elif await field.evaluate("el => el.tagName") == "SELECT":
                    await field.select_option(index=1)

            # 2. CLICK SAVE / SUBMIT
            # We look for any button that says Save, Submit, Next, or Apply
            save_btn = page.get_by_role("button", name=re.compile("save|submit|next|apply", re.IGNORECASE))
            
            if await save_btn.is_visible():
                await page.screenshot(path=f"JOB_{job_idx}_STEP_{step}_FILLED.png")
                await save_btn.click()
                print(f"   🚀 Job {job_idx}: Clicked Submit/Save for Step {step}")
            else:
                print(f"   ✅ Job {job_idx}: Questionnaire complete.")
                break

    except Exception as e:
        print(f"   [!] Error in questionnaire: {e}")

async def run_automation():
    async with async_playwright() as p:
        print("🚀 Starting Pro-Level Playwright Automation...")
        browser = await p.chromium.launch(headless=True)
        # Set a realistic user agent
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )

        # Handle Cookies
        page = await context.new_page()
        await page.goto("https://www.naukri.com/")
        
        cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    await context.add_cookies([{'name': n, 'value': v, 'domain': '.naukri.com', 'path': '/'}])
            await page.reload()

        # Search
        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        await page.goto(search_url)
        await page.wait_for_timeout(5000)

        # Get Job Links
        job_links = await page.locator("a.title").all_attribute_contents("href")
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:20]):
            try:
                await page.goto(link)
                await page.wait_for_timeout(7000)

                if "already applied" in (await page.content()).lower():
                    continue

                # Look for the main Apply button
                apply_btn = page.get_by_role("button", name="Apply", exact=True)
                if await apply_btn.is_visible():
                    print(f"✅ Applying to Job {idx+1}...")
                    await apply_btn.click()
                    await handle_questionnaire(page, idx+1)
                    applied += 1

                if applied >= 5: break
            except: continue

        await browser.close()
        print(f"🏁 Final Applied Count: {applied}")

import re
if __name__ == "__main__":
    asyncio.run(run_automation())
