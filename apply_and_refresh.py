import os
import asyncio
import random
import re
from playwright.async_api import async_playwright

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

async def fill_frame_inputs(frame, job_idx, step):
    """
    Finds and fills inputs inside a specific frame.
    Returns True if it found and interacted with anything.
    """
    found_something = False
    # Look for all possible input types
    inputs = frame.locator("input:not([type='hidden']), textarea, select, [contenteditable='true']")
    count = await inputs.count()

    for i in range(count):
        field = inputs.nth(i)
        if not await field.is_visible():
            continue
        
        found_something = True
        # Get context to decide what to type
        html = await field.evaluate("el => el.outerHTML + el.parentElement.innerText")
        ctx = html.lower()

        # 1. Handle Radios/Checkboxes
        field_type = await field.get_attribute("type")
        if field_type in ["radio", "checkbox"]:
            if any(k in ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree", "confirm"]):
                await field.click(force=True)
        
        # 2. Handle Text/Number/Textarea
        elif await field.evaluate("el => ['INPUT', 'TEXTAREA'].includes(el.tagName)"):
            val = "Yes" # Default
            if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
            elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
            elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
            elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
            
            await field.click() # Focus
            await field.fill("") # Clear
            await field.type(val, delay=100) # Type like a human
            await field.press("Enter") # Trigger React state

        # 3. Handle Selects
        elif await field.evaluate("el => el.tagName === 'SELECT'"):
            try: await field.select_option(index=1)
            except: pass

    return found_something

async def handle_questionnaire(page, job_idx):
    """Recursively checks all frames for the questionnaire."""
    try:
        for step in range(1, 6):
            await page.wait_for_timeout(6000)
            await page.screenshot(path=f"JOB_{job_idx}_STEP_{step}_DEBUG.png")

            # Check Main Page + All Iframes
            all_frames = page.frames
            any_input_found = False
            
            for frame in all_frames:
                if await fill_frame_inputs(frame, job_idx, step):
                    any_input_found = True
            
            if not any_input_found:
                print(f"   [Job {job_idx}] No inputs detected in any frame at Step {step}.")
                break

            # FIND & CLICK SAVE (In any frame)
            clicked = False
            for frame in all_frames:
                save_btn = frame.locator("button:has-text('Save'), button:has-text('Submit'), button:has-text('Next'), button:has-text('Apply')").first
                if await save_btn.is_visible():
                    await save_btn.click()
                    print(f"   🚀 Job {job_idx}: Clicked button in frame.")
                    clicked = True
                    break
            
            if not clicked:
                print(f"   [Job {job_idx}] Inputs filled but no Save button found.")
                break
                
            await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"   [!] Questionnaire Error: {e}")

async def run_automation():
    async with async_playwright() as p:
        print("🚀 Starting Multi-Frame Playwright Bot...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Cookie Login
        cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
        await page.goto("https://www.naukri.com/")
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    await context.add_cookies([{'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com', 'path': '/'}])
            await page.reload()

        # Search Jobs
        await page.goto("https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f")
        await page.wait_for_timeout(5000)
        
        job_links = await page.locator("a.title").all_attribute_contents("href")
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:15]):
            try:
                await page.goto(link)
                await page.wait_for_timeout(6000)

                if "already applied" in (await page.content()).lower():
                    continue

                apply_btn = page.locator("button:has-text('Apply')").first
                if await apply_btn.is_visible():
                    print(f"✅ Job {idx+1}: Clicking Apply...")
                    await apply_btn.click()
                    await handle_questionnaire(page, idx+1)
                    applied += 1
                
                if applied >= 5: break
            except Exception as e:
                print(f"   Error on job {idx+1}: {e}")
                continue

        await browser.close()
        print(f"🏁 Final Apply Count: {applied}")

if __name__ == "__main__":
    asyncio.run(run_automation())
