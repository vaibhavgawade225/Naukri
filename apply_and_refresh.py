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

async def fill_inputs_in_all_frames(page, job_idx, step):
    found_any = False
    for frame in page.frames:
        try:
            # Targeted selector for interactive inputs
            inputs = frame.locator("input:not([type='hidden']), textarea, select")
            count = await inputs.count()
            
            for i in range(count):
                field = inputs.nth(i)
                if not await field.is_visible():
                    continue
                
                found_any = True
                html_context = await field.evaluate("el => el.outerHTML + (el.parentElement ? el.parentElement.innerText : '')")
                ctx = html_context.lower()

                field_type = await field.get_attribute("type")
                
                if field_type == "radio":
                    if any(k in ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                        await field.click(force=True)
                
                elif await field.evaluate("el => ['INPUT', 'TEXTAREA'].includes(el.tagName)"):
                    val = "Yes" 
                    if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                    elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                    elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                    elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
                    
                    await field.click()
                    await field.fill(val)
                    await field.press("Tab")
        except:
            continue
    return found_any

async def handle_questionnaire(page, job_idx):
    try:
        for step in range(1, 6):
            await page.wait_for_timeout(5000)
            await page.screenshot(path=f"JOB_{job_idx}_STEP_{step}_START.png")

            if not await fill_inputs_in_all_frames(page, job_idx, step):
                print(f"   [Step {step}] No inputs found.")
                break

            btn_clicked = False
            for frame in page.frames:
                # Optimized button finder
                submit_btn = frame.locator("button").filter(has_text=re.compile(r"save|submit|next|apply", re.IGNORECASE)).first
                if await submit_btn.is_visible():
                    await submit_btn.click()
                    print(f"   🚀 Clicked Submit/Next in frame.")
                    btn_clicked = True
                    break
            
            if not btn_clicked:
                break
    except Exception as e:
        print(f"   [!] Questionnaire Error: {e}")

async def run_automation():
    async with async_playwright() as p:
        print("🚀 Starting Corrected Playwright Bot...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Login
        cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
        await page.goto("https://www.naukri.com/")
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    await context.add_cookies([{'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com', 'path': '/'}])
            await page.reload()

        # Job Search
        await page.goto("https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f")
        await page.wait_for_timeout(5000)
        
        # --- FIXED LINK EXTRACTION ---
        locators = page.locator("a.title")
        job_links = []
        for i in range(await locators.count()):
            href = await locators.nth(i).get_attribute("href")
            if href: job_links.append(href)
        
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:15]):
            try:
                await page.goto(link)
                await page.wait_for_timeout(6000)

                if "already applied" in (await page.content()).lower():
                    continue

                apply_btn = page.get_by_role("button", name="Apply", exact=True).first
                if await apply_btn.is_visible():
                    print(f"✅ Job {idx+1}: Applying...")
                    await apply_btn.click()
                    await handle_questionnaire(page, idx+1)
                    applied += 1
                
                if applied >= 5: break
            except: continue

        await browser.close()
        print(f"🏁 Final Applied Count: {applied}")

if __name__ == "__main__":
    asyncio.run(run_automation())
