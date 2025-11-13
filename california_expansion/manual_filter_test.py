#!/usr/bin/env python3
"""
Manual filter test - opens the page and lets you select the California filter
"""
import asyncio
from playwright.async_api import async_playwright

async def manual_filter_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        await page.goto("https://app.seniorplace.com/login")
        await page.wait_for_timeout(2000)
        
        email_field = await page.query_selector('#email')
        if not email_field:
            print("❌ Email field not found")
            await browser.close()
            return
        
        await page.fill('#email', "melanie@aplaceforseniors.com")
        await page.fill('#password', "Melanie123!")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)
        
        # Go to communities page
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        print("🔍 Page loaded! Please manually select the California filter.")
        print("📝 Look for:")
        print("   - 'More filters' button")
        print("   - 'In CA' button") 
        print("   - State dropdown")
        print("   - Any other filter options")
        print("\n⏳ Waiting 30 seconds for you to select the filter...")
        print("   (The script will automatically continue)")
        
        # Wait 30 seconds for manual interaction
        await page.wait_for_timeout(30000)
        
        # Take screenshot of the filtered results
        await page.screenshot(path="filtered_results.png")
        print("📸 Screenshot saved: filtered_results.png")
        
        # Check how many results we have
        cards = await page.query_selector_all('[data-testid*="community"], .community-card, [class*="card"]')
        print(f"✅ Found {len(cards)} community cards after filtering")
        
        # Check if they're all California
        ca_count = 0
        for i, card in enumerate(cards[:5]):  # Check first 5 cards
            try:
                text = await card.inner_text()
                if 'CA' in text or 'California' in text:
                    ca_count += 1
            except:
                pass
        
        print(f"✅ Verified: {ca_count}/5 sample cards are California")
        
        # Get the current URL to see if it has filter parameters
        current_url = page.url
        print(f"🔗 Current URL: {current_url}")
        
        # Look for any filter-related elements that might be active
        active_filters = await page.query_selector_all('[class*="active"], [aria-selected="true"], [data-selected="true"]')
        print(f"🔍 Found {len(active_filters)} potentially active filter elements")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(manual_filter_test())
