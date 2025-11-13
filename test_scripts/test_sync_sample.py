#!/usr/bin/env python3
"""
Test script for Seniorly care type sync
Tests on 3 sample listings to verify the approach works
"""

import asyncio
from playwright.async_api import async_playwright

async def test_sync_sample():
    """Test sync on 3 sample listings"""
    
    # Sample listings to test
    test_listings = [
        "A & I Adult Care Home",
        "American Dream Home", 
        "Elliecare"
    ]
    
    print("🧪 Testing Seniorly care type sync on 3 sample listings...")
    
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
            search_input = page.locator('input[type="text"][placeholder="Name, Contact, or Street"]')
            await search_input.wait_for(timeout=10000)
            await search_input.fill(title)
            await page.wait_for_timeout(5000)  # Wait longer for results to load
            
            # Check results - look for the flex-1 overflow-visible div that contains the title and care types
            result_cards = page.locator('div[class*="flex-1 overflow-visible"]')
            
            if await result_cards.count() > 0:
                # Look for exact title match in first few results
                for j in range(min(3, await result_cards.count())):
                    card = result_cards.nth(j)
                    title_element = card.locator('h3 a')
                    
                    if await title_element.count() > 0:
                        found_title = await title_element.text_content()
                        
                        # Check if this is our listing
                        if (found_title.lower().strip() == title.lower().strip() or 
                            title.lower() in found_title.lower() or
                            found_title.lower() in title.lower()):
                            
                            print(f"  ✅ Found match: {found_title}")
                            
                            # Extract care type pills
                            care_types = []
                            pill_spans = card.locator('span[class*="rounded-full"]')
                            
                            for k in range(await pill_spans.count()):
                                span = pill_spans.nth(k)
                                text = await span.text_content()
                                classes = await span.get_attribute('class')
                                
                                # Check if this span has color classes (any color)
                                if text and any(color in classes for color in ['amber', 'yellow', 'blue', 'green', 'purple', 'red', 'gray', 'cyan', 'teal']):
                                    care_types.append(text.strip())
                                    print(f"      🎯 Found pill: '{text}' (classes: {classes})")
                            
                            print(f"  🏷️  Care types: {', '.join(care_types)}")
                            
                            # Get URL
                            url = await title_element.get_attribute('href')
                            if url and not url.startswith('http'):
                                url = f"https://app.seniorplace.com{url}"
                            print(f"  🔗 URL: {url}")
                            
                            break
                else:
                    print("  ❌ No title match found in results")
            else:
                print("  ❌ No results found")
            
            await asyncio.sleep(2)
        
        await browser.close()
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_sync_sample())
