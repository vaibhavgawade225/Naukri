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

async def handle_questionnaire(page, job_idx):
    """Handles chatbot/frame questions with human-like typing."""
    for step in range(1, 6):
        await page.wait_for_timeout(random.randint(4000, 6000))
        # Deep search for inputs in all frames
        found_any = False
        for frame in page.frames:
            try:
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
                            val = MY_PROFILE_DATA.get("experience", "2")
                            if "current" in ctx: val = MY_PROFILE_DATA["current_ctc"]
                            elif "expected" in ctx: val = MY_PROFILE_DATA["expected_ctc"]
                            elif "notice" in ctx: val = MY_PROFILE_DATA["notice_period"]
                            await field.fill(val)
                            await field.press("Tab")
            except: continue
        
        if not found_any: break
        
        # Click Next/Save
        btn_clicked = False
        for frame in page.frames:
            btn = frame.locator("button").filter(has_text=re.compile(r"save|submit|next|apply", re.IGNORECASE)).first
            if await btn.is_visible():
                await btn.click()
                btn_clicked = True; break
        if not btn_clicked: break

async def run_automation():
    async with async_playwright() as p:
        print("🚀 Starting Stealth Playwright Bot...")
        # Launch with specific arguments to disable bot-detection flags
        browser = await p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox'
        ])
        
        # Spoofing a real Windows Chrome 128 User Profile
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Referer": "https://www.google.com/"
            }
        )

        page = await context.new_page()
        
        # Inject script to hide Playwright's "webdriver" property
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 1. Apply Cookies
        cookie_raw = os.environ.get('NAUKRI_COOKIE', '').strip()
        await page.goto("https://www.naukri.com/", wait_until="domcontentloaded")
        if cookie_raw:
            for item in cookie_raw.split(';'):
                if '=' in item:
                    n, v = item.strip().split('=', 1)
                    await context.add_cookies([{'name': n.strip(), 'value': v.strip(), 'domain': '.naukri.com', 'path': '/'}])
            await page.reload(wait_until="networkidle")

        # 2. Navigate to Search with human-like delay
        search_url = "https://www.naukri.com/java-developer-jobs-in-mumbai-pune?experience=0&experience=1&experience=2&sort=f"
        await page.goto(search_url, wait_until="networkidle")
        await page.wait_for_timeout(random.randint(5000, 8000))
        
        await page.screenshot(path="ACCESS_CHECK.png")
        
        if "access denied" in (await page.content()).lower():
            print("❌ ACCESS DENIED: Naukri blocked the GitHub IP. Try updating your NAUKRI_COOKIE.")
            await browser.close()
            return

        # 3. Extract Job Links using a more robust method
        job_links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a'))
                .map(a => a.href)
                .filter(href => href && href.includes('job-listings-'))
        }''')
        
        job_links = list(set(job_links))
        print(f"Found {len(job_links)} jobs.")

        applied = 0
        for idx, link in enumerate(job_links[:10]):
            try:
                print(f"🔗 Opening Job {idx+1}...")
                await page.goto(link, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(6000, 9000))
                
                # Check for Apply button
                apply_btn = page.locator("button:has-text('Apply')").first
                if await apply_btn.is_visible():
                    # Check if already applied via page content
                    if "already applied" in (await page.content()).lower():
                        print(f"   Skip: Already applied.")
                        continue
                        
                    await apply_btn.click()
                    print(f"   ✅ Applying...")
                    await handle_questionnaire(page, idx+1)
                    applied += 1
                    
                if applied >= 5: break
            except Exception as e:
                print(f"   Error: {e}")
                continue

        await browser.close()
        print(f"🏁 Final Applied Count: {applied}")

if __name__ == "__main__":
    asyncio.run(run_automation())
