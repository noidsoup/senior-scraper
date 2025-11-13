#!/usr/bin/env python3
"""Check if Senior Place has state filters we can use"""

import asyncio
from playwright.async_api import async_playwright

USERNAME = "allison@aplaceforseniors.org"
PASSWORD = "Hugomax2025!"

async def check_filters():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        
        # Go to communities
        print("📍 Navigating to communities...")
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(5000)
        
        # Take screenshot
        await page.screenshot(path='seniorplace_filters.png')
        print("📸 Screenshot saved: seniorplace_filters.png")
        
        # Look for filter elements
        print("\n🔍 Looking for filters/search...")
        
        # Check for common filter patterns
        filters = await page.query_selector_all('select, input[type="search"], button:has-text("Filter")')
        print(f"Found {len(filters)} potential filter elements")
        
        # Check for state dropdown
        state_select = await page.query_selector('select[name*="state" i], select[name*="location" i]')
        if state_select:
            print("✅ Found state select dropdown!")
            options = await state_select.query_selector_all('option')
            print(f"   Has {len(options)} options")
        
        # Check for search input
        search = await page.query_selector('input[type="search"], input[placeholder*="search" i]')
        if search:
            print("✅ Found search input!")
            placeholder = await search.get_attribute('placeholder')
            print(f"   Placeholder: {placeholder}")
        
        # Get page HTML to inspect
        html = await page.content()
        
        # Look for state-related text
        if 'state' in html.lower() or 'location' in html.lower():
            print("✅ Page contains state/location filter text")
        
        print("\n⏸️  Browser open - check manually for filters")
        print("Press Enter when done...")
        input()
        
        await browser.close()

asyncio.run(check_filters())

