#!/usr/bin/env python3
"""
Debug script to see exactly what's in the result card
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_card_content():
    """Debug the result card content"""
    
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
        
        # Try different card selectors
        print("\n🔍 Trying different card selectors...")
        
        # Selector 1: The one we're using
        selector1 = 'div[class*="flex space-x-6 w-full items-start justify-between p-6"]'
        cards1 = page.locator(selector1)
        print(f"1. Selector '{selector1}': Found {await cards1.count()} cards")
        
        if await cards1.count() > 0:
            card1 = cards1.nth(0)
            print(f"   First card HTML:")
            print(await card1.inner_html())
            
            # Look for spans in this card
            spans1 = card1.locator('span')
            print(f"   Found {await spans1.count()} spans in first card")
            
            for i in range(min(5, await spans1.count())):
                span = spans1.nth(i)
                text = await span.text_content()
                classes = await span.get_attribute('class')
                print(f"     Span {i+1}: '{text}' (classes: {classes})")
        
        # Selector 2: Simpler approach
        selector2 = 'div[class*="flex space-x-6"]'
        cards2 = page.locator(selector2)
        print(f"\n2. Selector '{selector2}': Found {await cards2.count()} cards")
        
        if await cards2.count() > 0:
            card2 = cards2.nth(0)
            spans2 = card2.locator('span[class*="rounded-full"]')
            print(f"   Found {await spans2.count()} rounded spans in first card")
            
            for i in range(min(5, await spans2.count())):
                span = spans2.nth(i)
                text = await span.text_content()
                classes = await span.get_attribute('class')
                print(f"     Span {i+1}: '{text}' (classes: {classes})")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_card_content())
