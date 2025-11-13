#!/usr/bin/env python3
"""
Debug script to see what's actually in the result cards
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_result_card():
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
        
        # Get the first result card HTML
        result_cards = page.locator('div[class*="flex space-x-6 w-full items-start justify-between p-6"]')
        
        if await result_cards.count() > 0:
            first_card = result_cards.nth(0)
            html_content = await first_card.inner_html()
            print("\n📄 HTML Content of first result card:")
            print("=" * 80)
            print(html_content)
            print("=" * 80)
            
            # Also try to find any spans with care type info
            all_spans = first_card.locator('span')
            print(f"\n🔍 Found {await all_spans.count()} span elements:")
            
            for i in range(await all_spans.count()):
                span = all_spans.nth(i)
                text = await span.text_content()
                classes = await span.get_attribute('class')
                print(f"  Span {i+1}: '{text}' (classes: {classes})")
                
                # Check if this looks like a care type pill
                if classes and any(color in classes for color in ['amber', 'yellow', 'blue', 'green', 'purple', 'red', 'gray']):
                    print(f"    🎯 POTENTIAL CARE TYPE PILL: {text}")
        else:
            print("❌ No result cards found")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_result_card())
