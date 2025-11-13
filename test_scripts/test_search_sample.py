#!/usr/bin/env python3
"""
Test script for Senior Place search functionality
Tests on 3 sample listings to verify the approach works
"""

import asyncio
import csv
from playwright.async_api import async_playwright

async def test_search_sample():
    """Test search on 3 sample listings"""
    
    # Sample listings to test
    test_listings = [
        "A & I Adult Care Home",
        "American Dream Home", 
        "Elliecare"
    ]
    
    print("🧪 Testing Senior Place search on 3 sample listings...")
    
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
        
        # Test each listing
        for i, title in enumerate(test_listings, 1):
            print(f"\n🔍 [{i}/3] Testing: {title}")
            
            # Navigate to communities page
            await page.goto('https://app.seniorplace.com/communities')
            await page.wait_for_load_state('networkidle')
            
            # Search
            search_input = page.locator('input[placeholder="Name, Contact, or Street"]')
            await search_input.fill(title)
            await page.wait_for_timeout(2000)
            
            # Check results
            result_cards = page.locator('div[class*="flex space-x-6 w-full items-start justify-between p-6"]')
            
            if await result_cards.count() > 0:
                first_card = result_cards.nth(0)
                
                # Get title
                title_element = first_card.locator('h3 a')
                if await title_element.count() > 0:
                    found_title = await title_element.text_content()
                    print(f"  ✅ Found: {found_title}")
                    
                    # Get care type pills
                    care_type_pills = first_card.locator('span[class*="rounded-full bg-amber-100 text-amber-800"], span[class*="rounded-full bg-yellow-100 text-yellow-800"], span[class*="rounded-full bg-blue-100 text-blue-800"], span[class*="rounded-full bg-green-100 text-green-800"], span[class*="rounded-full bg-purple-100 text-purple-800"], span[class*="rounded-full bg-red-100 text-red-800"]')
                    
                    care_types = []
                    for j in range(await care_type_pills.count()):
                        pill_text = await care_type_pills.nth(j).text_content()
                        if pill_text:
                            care_types.append(pill_text.strip())
                    
                    print(f"  🏷️  Care types: {', '.join(care_types)}")
                    
                    # Get URL
                    url_element = first_card.locator('h3 a')
                    url = await url_element.get_attribute('href') if await url_element.count() > 0 else None
                    if url and not url.startswith('http'):
                        url = f"https://app.seniorplace.com{url}"
                    print(f"  🔗 URL: {url}")
                    
                else:
                    print("  ❌ No title found")
            else:
                print("  ❌ No results found")
            
            await asyncio.sleep(2)
        
        await browser.close()
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_search_sample())
