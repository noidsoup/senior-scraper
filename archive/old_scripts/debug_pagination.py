#!/usr/bin/env python3
"""
Debug: Check what the pagination looks like
"""

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Login
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('#email', 'allison@aplaceforseniors.org')
        await page.fill('#password', 'Hugomax2025!')
        await page.click('#signin')
        await page.wait_for_selector('text=Communities', timeout=15000)
        
        # Go to communities
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        # Check pagination
        print("Checking for pagination elements...")
        
        # Try different selectors
        selectors = [
            'nav[aria-label="Pagination"]',
            'nav >> text=Next',
            'button:has-text("Next")',
            'a:has-text("Next")',
            '.pagination',
            '[class*="paginat"]',
        ]
        
        for selector in selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    html = await el.evaluate('el => el.outerHTML')
                    print(f"\n✅ Found with: {selector}")
                    print(html[:200])
                else:
                    print(f"❌ Not found: {selector}")
            except Exception as e:
                print(f"❌ Error with {selector}: {e}")
        
        # Take screenshot
        await page.screenshot(path='pagination_debug.png', full_page=True)
        print("\n📸 Screenshot saved: pagination_debug.png")
        
        input("\nPress Enter to close...")
        await browser.close()

asyncio.run(main())

