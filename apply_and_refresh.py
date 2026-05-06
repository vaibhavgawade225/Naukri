import os
import asyncio
import random
import re  # <--- FIXED: Moved to top
from playwright.async_api import async_playwright

# --- YOUR PROFILE DATA ---
MY_PROFILE_DATA = {
    "current_ctc": "3", 
    "expected_ctc": "5", 
    "notice_period": "15", 
    "experience": "2"
}

async def fill_inputs_in_all_frames(page, job_idx, step):
    """
    Finds and fills inputs inside the main page AND all iframes.
    """
    found_any = False
    # Check main page + every frame (Naukri often uses chatbots in iframes)
    for frame in page.frames:
        inputs = frame.locator("input:not([type='hidden']), textarea, select")
        count = await inputs.count()
        
        for i in range(count):
            field = inputs.nth(i)
            if not await field.is_visible():
                continue
            
            found_any = True
            # Get text context to identify the question
            html_context = await field.evaluate("el => el.outerHTML + el.parentElement.innerText")
            ctx = html_context.lower()

            # Handle Radios
            if await field.get_attribute("type") == "radio":
                if any(k in ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                    await field.click(force=True)
            
            # Handle Text/Number boxes
            elif await field.evaluate("el => ['INPUT', 'TEXTAREA'].includes(el.tagName)"):
                val = "Yes" 
                if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
                
                await field.click()
                await field.fill(val)
                await field.press("Tab") # Trigger React state update
    return found_any

async def handle_questionnaire(page, job_idx):
    try:
        for step in range(1, 6):
            await page.wait_for_timeout(5000)
            await page.screenshot(path=f"JOB_{job_idx}_STEP_{step}_START.png")

            # Fill all frames
            if not await fill_inputs_in_all_frames(page, job_idx, step):
                print(f"   [Step {step}] No questions found in any frame.")
                break

            # Click Save/Submit in whichever frame it exists
            btn_clicked = False
            for frame in page.frames:
                # Playwright's Regex search for any variation of Save/Submit/Next
                submit_btn = frame.get_by_role("button", name=re.compile("save|submit|next|apply", re.IGNORECASE))
                if await submit_btn.is_visible():
                    await submit_btn.click()
                    btn_clicked = True
                    break
            
            if not btn_clicked:
                break
    except Exception as e:
        print(f"   [!] Error handling questionnaire: {e}")

async def run_automation():
    async with async_playwright() as p:
        print("🚀 Starting Iframe-Ready Playwright Bot...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Login with Cookies
        cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
        await page.goto("https://www.naukri.com/")
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    await context.add_cookies([{'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com', 'path': '/'}])
            await page.reload()

        # Job List
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

if __name__ == "__main__":
    asyncio.run(run_automation())
