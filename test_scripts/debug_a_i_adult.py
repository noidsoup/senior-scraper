#!/usr/bin/env python3
"""
Debug script to see all care type pills on A & I Adult Care Home
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_a_i_adult():
    """Debug A & I Adult Care Home care types"""
    
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
        
        # Search for A & I Adult Care Home
        print("\n🔍 Searching for: A & I Adult Care Home")
        await page.goto('https://app.seniorplace.com/communities')
        await page.wait_for_load_state('networkidle')
        
        search_input = page.locator('input[type="text"][placeholder="Name, Contact, or Street"]')
        await search_input.wait_for(timeout=10000)
        await search_input.fill('A & I Adult Care Home')
        await page.wait_for_timeout(5000)
        
        # Find the result card
        result_cards = page.locator('div[class*="flex-1 overflow-visible"]')
        print(f"Found {await result_cards.count()} result cards")
        
        if await result_cards.count() > 0:
            # Look for A & I Adult Care Home specifically
            for i in range(await result_cards.count()):
                card = result_cards.nth(i)
                title_element = card.locator('h3 a')
                
                if await title_element.count() > 0:
                    found_title = await title_element.text_content()
                    
                    if 'A & I ADULT CARE HOME' in found_title.upper():
                        print(f"\n🎯 Found A & I Adult Care Home: {found_title}")
                        
                        # Get the full HTML of this card
                        card_html = await card.inner_html()
                        print(f"\n📄 Full card HTML:")
                        print("=" * 80)
                        print(card_html)
                        print("=" * 80)
                        
                        # Look for ALL spans in this card
                        all_spans = card.locator('span')
                        print(f"\n🔍 Found {await all_spans.count()} total spans in this card:")
                        
                        for j in range(await all_spans.count()):
                            span = all_spans.nth(j)
                            text = await span.text_content()
                            classes = await span.get_attribute('class')
                            print(f"  Span {j+1}: '{text}' (classes: {classes})")
                            
                            # Highlight care type pills
                            if classes and any(color in classes for color in ['amber', 'yellow', 'blue', 'green', 'purple', 'red', 'gray', 'cyan', 'teal']):
                                print(f"    🎯 CARE TYPE PILL: {text}")
                        
                        break
            else:
                print("❌ A & I Adult Care Home not found in results")
        else:
            print("❌ No results found")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_a_i_adult())
