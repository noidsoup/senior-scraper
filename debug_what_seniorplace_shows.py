#!/usr/bin/env python3
"""Check what Senior Place is actually showing"""

import asyncio
import os
from playwright.async_api import async_playwright

USERNAME = os.getenv("SP_USERNAME")
PASSWORD = os.getenv("SP_PASSWORD")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.wait_for_timeout(2000)
        await page.fill('input[type="email"]', USERNAME)
        await page.fill('input[type="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        
        # Navigate to communities
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(5000)
        
        # Check URL
        current_url = page.url
        print(f"\nCurrent URL: {current_url}")
        
        # Check for any filter indicators
        print("\nChecking for active filters...")
        
        # Count total listings shown
        cards = await page.query_selector_all('div.flex.space-x-6')
        print(f"Listings on page 1: {len(cards)}")
        
        # Check pagination info
        pagination_text = await page.query_selector('div.text-sm.text-gray-700')
        if pagination_text:
            text = await pagination_text.inner_text()
            print(f"Pagination text: {text}")
        
        # Check if there's a filter button or indicator
        filter_buttons = await page.query_selector_all('button')
        for btn in filter_buttons[:10]:  # Check first 10 buttons
            text = await btn.inner_text()
            if 'filter' in text.lower() or 'clear' in text.lower():
                print(f"Found button: {text}")
        
        print("\nLEAVING BROWSER OPEN - Check manually for filters!")
        print("Press Enter when done...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

