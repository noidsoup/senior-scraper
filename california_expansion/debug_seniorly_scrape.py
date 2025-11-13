#!/usr/bin/env python3
"""
Debug Seniorly city scraping to see what's actually on the page
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Not headless so we can see
        page = await browser.new_page()
        
        # Try a major city that definitely has facilities
        city_url = "https://www.seniorly.com/assisted-living/california/los-angeles"
        
        print(f"🔍 Loading: {city_url}")
        await page.goto(city_url, timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Take screenshot
        await page.screenshot(path="seniorly_la_page.png")
        print("📸 Screenshot saved: seniorly_la_page.png")
        
        # Check page title
        title = await page.title()
        print(f"📄 Page title: {title}")
        
        # Look for any links that might be facilities
        all_links = await page.query_selector_all('a[href*="/assisted-living/california/los-angeles/"]')
        print(f"\n🔗 Found {len(all_links)} links with LA URLs")
        
        # Print first few
        for i, link in enumerate(all_links[:5]):
            href = await link.get_attribute('href')
            text = await link.inner_text()
            print(f"  {i+1}. {text[:50]} -> {href[:80]}")
        
        # Try to find facility cards by different selectors
        print("\n🔍 Testing different selectors:")
        
        selectors = [
            'div[class*="card"]',
            'article',
            'a[href*="/communities/"]',
            '[data-testid*="community"]',
            '[class*="listing"]',
            '[class*="facility"]',
            '[class*="result"]',
        ]
        
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            print(f"  {selector}: {len(elements)} elements")
        
        # Get page content to inspect
        content = await page.content()
        
        # Look for "communities" or "facilities" in the HTML
        if 'communities' in content.lower():
            print("\n✅ Found 'communities' in page content")
        if 'no results' in content.lower() or 'no communities' in content.lower():
            print("\n⚠️  Found 'no results' message in page")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape())

