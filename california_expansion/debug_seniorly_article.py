#!/usr/bin/env python3
"""
Debug what's inside the article tags on Seniorly
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_articles():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        city_url = "https://www.seniorly.com/assisted-living/california/los-angeles"
        
        print(f"🔍 Loading: {city_url}")
        await page.goto(city_url, timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Get all article elements
        articles = await page.query_selector_all('article')
        print(f"\n📦 Found {len(articles)} article elements\n")
        
        # Look at first 3 articles
        for i, article in enumerate(articles[:3]):
            print(f"{'='*60}")
            print(f"ARTICLE {i+1}:")
            print(f"{'='*60}")
            
            # Get inner HTML to see structure
            html = await article.inner_html()
            print(html[:500])
            print("\n")
            
            # Try to find links
            links = await article.query_selector_all('a')
            print(f"  Links in article: {len(links)}")
            for link in links[:3]:
                href = await link.get_attribute('href')
                text = await link.inner_text()
                print(f"    - {text[:30]} -> {href}")
            
            # Try to find any text
            text = await article.inner_text()
            print(f"\n  Full text: {text[:200]}")
            print()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_articles())

