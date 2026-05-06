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
            # Broad search for any interactive element
            inputs = frame.locator("input:not([type='hidden']), textarea, select")
            count = await inputs.count()
            for i in range(count):
                field = inputs.nth(i)
                if await field.is_visible():
                    found_any = True
                    ctx = await field.evaluate("el => el.outerHTML + (el.parentElement ? el.parentElement.innerText : '')")
                    ctx = ctx.lower()
                    if await field.get_attribute("type") == "radio":
                        if any(k in ctx for k in ["15", "immediate", "yes", "willing", "relocate", "agree"]):
                            await field.click(force=True)
                    elif await field.evaluate("el => ['INPUT', 'TEXTAREA'].includes(el.tagName)"):
                        val = "Yes"
                        if "current" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                        elif "expected" in ctx and "ctc" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                        elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                        elif "experience" in ctx: val = MY_PROFILE_DATA["experience"]
                        await field.fill(val)
                        await field.press("Tab")
        except: continue
    return found_any

async def handle_questionnaire(page, job_idx):
    for step in range(1, 6):
        await page.wait_for_timeout(4000)
        await page.screenshot(path=f"JOB_{job_idx}_STEP_{step}_START.png")
        if not await fill_inputs_in_all_frames(page, job_idx, step): break
        btn_clicked = False
        for frame in page.frames:
            submit_btn = frame.locator("button").filter(has_text=re.compile(r"save|submit|next|apply", re.IGNORECASE)).first
            if await submit_btn.is_visible():
                await submit_btn.click()
                btn_clicked = True; break
        if not btn_clicked: break

async def run_automation():
    async with async_playwright() as p:
        print("🚀 Starting Refined Playwright Bot...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        # Cookie Login
        cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
        await page.goto("https://www.naukri.com/", wait_until="networkidle")
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    await context.add_cookies([{'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com', 'path': '/'}])
            await page.reload()

        # Search Page
        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        await page.goto(search_url, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        # DEBUG: Take a screenshot of the search results to see if we are blocked
        await page.screenshot(path="SEARCH_RESULTS_DEBUG.png")

        # UPDATED LINK SELECTOR: Looking for any link that looks like a job description
        job_links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a'))
                .map(a => a.href)
                .filter(href => href.includes('job-listings-'))
        }''')
        
        # Remove duplicates
        job_links = list(set(job_links))
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                await page.goto(link, wait_until="networkidle")
                await page.wait_for_timeout(5000)
                if "already applied" in (await page.content()).lower(): continue
                apply_btn = page.locator("button:has-text('Apply')").first
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
