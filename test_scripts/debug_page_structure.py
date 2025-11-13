#!/usr/bin/env python3
"""
Debug script to see the actual page structure of Senior Place communities
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_page_structure():
    """Debug the page structure"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto('https://app.seniorplace.com/login')
        await page.wait_for_load_state('networkidle')
        
        if await page.locator('input[type="email"]').count() > 0:
            await page.fill('input[type="email"]', 'allison@aplaceforseniors.org')
            await page.fill('input[type="password"]', 'Hugomax2023!')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            print("✅ Logged in")
        
        # Go to communities page
        print("\n🔍 Going to communities page...")
        await page.goto('https://app.seniorplace.com/communities')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
        print(f"📄 Current URL: {page.url}")
        print(f"📄 Page title: {await page.title()}")
        
        # Look for search input
        search_inputs = page.locator('input')
        print(f"\n🔍 Found {await search_inputs.count()} input elements:")
        
        for i in range(await search_inputs.count()):
            input_elem = search_inputs.nth(i)
            placeholder = await input_elem.get_attribute('placeholder')
            type_attr = await input_elem.get_attribute('type')
            print(f"  Input {i+1}: type={type_attr}, placeholder='{placeholder}'")
        
        # Look for any elements with "search" in them
        search_elements = page.locator('[class*="search"]')
        print(f"\n🔍 Found {await search_elements.count()} elements with 'search' in class:")
        
        for i in range(min(5, await search_elements.count())):
            elem = search_elements.nth(i)
            tag = await elem.evaluate('el => el.tagName')
            classes = await elem.get_attribute('class')
            print(f"  {tag} {i+1}: {classes}")
        
        # Take a screenshot
        await page.screenshot(path="debug_communities_page.png")
        print("\n📸 Screenshot saved as debug_communities_page.png")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page_structure())
