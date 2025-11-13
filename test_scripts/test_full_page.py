#!/usr/bin/env python3
"""
Test script for clicking through to full listing pages
"""

import asyncio
from playwright.async_api import async_playwright

async def test_full_page():
    """Test clicking through to full listing page"""
    
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
        search_input = page.locator('input[placeholder="Name, Contact, or Street"]')
        await search_input.clear()
        await search_input.fill('A & I Adult Care Home')
        await page.wait_for_timeout(2000)
        
        # Find and click first result
        result_cards = page.locator('div[class*="flex space-x-6 w-full items-start justify-between p-6"]')
        
        if await result_cards.count() > 0:
            first_card = result_cards.nth(0)
            title_element = first_card.locator('h3 a')
            
            if await title_element.count() > 0:
                found_title = await title_element.text_content()
                print(f"  ✅ Found: {found_title}")
                
                # Click through to full page
                await title_element.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(3000)
                
                print(f"  🔗 Now on: {page.url}")
                
                # Look for care type pills on full page
                care_types = []
                pill_selectors = [
                    'span[class*="rounded-full bg-amber-100 text-amber-800"]',
                    'span[class*="rounded-full bg-yellow-100 text-yellow-800"]',
                    'span[class*="rounded-full bg-blue-100 text-blue-800"]',
                    'span[class*="rounded-full bg-green-100 text-green-800"]',
                    'span[class*="rounded-full bg-purple-100 text-purple-800"]',
                    'span[class*="rounded-full bg-red-100 text-red-800"]',
                    'span[class*="rounded-full bg-gray-100 text-gray-800"]'
                ]
                
                for selector in pill_selectors:
                    pills = page.locator(selector)
                    for j in range(await pills.count()):
                        pill_text = await pills.nth(j).text_content()
                        if pill_text and pill_text.strip():
                            care_types.append(pill_text.strip())
                
                print(f"  🏷️  Care types on full page: {', '.join(care_types)}")
                
                # Also check page title
                page_title = await page.title()
                print(f"  📄 Page title: {page_title}")
                
            else:
                print("  ❌ No title element found")
        else:
            print("  ❌ No results found")
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_full_page())
