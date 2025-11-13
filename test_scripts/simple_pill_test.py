#!/usr/bin/env python3
"""
Simple test to find care type pills
"""

import asyncio
from playwright.async_api import async_playwright

async def simple_pill_test():
    """Simple test for care type pills"""
    
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
        
        # Search for one listing
        print("\n🔍 Searching for: A & I Adult Care Home")
        await page.goto('https://app.seniorplace.com/communities')
        await page.wait_for_load_state('networkidle')
        
        search_input = page.locator('input[type="text"][placeholder="Name, Contact, or Street"]')
        await search_input.wait_for(timeout=10000)
        await search_input.fill('A & I Adult Care Home')
        await page.wait_for_timeout(3000)
        
        # Try different approaches to find pills
        print("\n🔍 Trying different pill finding approaches...")
        
        # Approach 1: Look for any spans with rounded-full
        rounded_spans = page.locator('span[class*="rounded-full"]')
        print(f"1. Found {await rounded_spans.count()} spans with 'rounded-full'")
        
        for i in range(min(10, await rounded_spans.count())):
            span = rounded_spans.nth(i)
            text = await span.text_content()
            classes = await span.get_attribute('class')
            print(f"   Span {i+1}: '{text}' (classes: {classes})")
        
        # Approach 2: Look for any spans with color classes
        color_spans = page.locator('span[class*="bg-"]')
        print(f"\n2. Found {await color_spans.count()} spans with 'bg-'")
        
        for i in range(min(10, await color_spans.count())):
            span = color_spans.nth(i)
            text = await span.text_content()
            classes = await span.get_attribute('class')
            print(f"   Span {i+1}: '{text}' (classes: {classes})")
        
        # Approach 3: Look for any spans with text- classes
        text_spans = page.locator('span[class*="text-"]')
        print(f"\n3. Found {await text_spans.count()} spans with 'text-'")
        
        for i in range(min(10, await text_spans.count())):
            span = text_spans.nth(i)
            text = await span.text_content()
            classes = await span.get_attribute('class')
            print(f"   Span {i+1}: '{text}' (classes: {classes})")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(simple_pill_test())
