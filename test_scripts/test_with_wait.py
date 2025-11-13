#!/usr/bin/env python3
"""
Test script with longer wait times for search results
"""

import asyncio
from playwright.async_api import async_playwright

async def test_with_wait():
    """Test with longer wait times"""
    
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
        
        # Test one listing
        print("\n🔍 Testing: A & I Adult Care Home")
        await page.goto('https://app.seniorplace.com/communities')
        await page.wait_for_load_state('networkidle')
        
        # Search
        search_input = page.locator('input[type="text"][placeholder="Name, Contact, or Street"]')
        await search_input.wait_for(timeout=10000)
        await search_input.fill('A & I Adult Care Home')
        
        # Wait longer for results
        print("⏳ Waiting for search results...")
        await page.wait_for_timeout(5000)
        
        # Check results
        result_cards = page.locator('div[class*="flex-1 overflow-visible"]')
        print(f"Found {await result_cards.count()} result cards")
        
        if await result_cards.count() > 0:
            first_card = result_cards.nth(0)
            
            # Get title
            title_element = first_card.locator('h3 a')
            if await title_element.count() > 0:
                found_title = await title_element.text_content()
                print(f"✅ Found: {found_title}")
                
                # Look for care type pills
                care_types = []
                pill_spans = first_card.locator('span[class*="rounded-full"]')
                print(f"Found {await pill_spans.count()} rounded spans in this card")
                
                for i in range(await pill_spans.count()):
                    span = pill_spans.nth(i)
                    text = await span.text_content()
                    classes = await span.get_attribute('class')
                    print(f"  Span {i+1}: '{text}' (classes: {classes})")
                    
                    # Check if this looks like a care type pill
                    if text and any(color in classes for color in ['amber', 'yellow', 'blue', 'green', 'purple', 'red', 'gray', 'cyan']):
                        care_types.append(text.strip())
                        print(f"    🎯 CARE TYPE PILL: {text}")
                
                print(f"🏷️  Care types found: {', '.join(care_types)}")
                
                # Also check the HTML structure
                print(f"\n📄 Card HTML structure:")
                card_html = await first_card.inner_html()
                print(card_html[:500] + "..." if len(card_html) > 500 else card_html)
                
            else:
                print("❌ No title element found")
        else:
            print("❌ No results found")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_with_wait())
