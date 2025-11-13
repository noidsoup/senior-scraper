#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright
import csv

async def test_browser():
    print("🔍 Testing browser interaction...")
    
    # Read one row
    with open('california_seniorplace_data_DEDUPED.csv', 'r') as f:
        reader = csv.DictReader(f)
        row = next(reader)
    
    print(f"📋 Testing with: {row['title']}")
    print(f"🔍 URL: {row['url']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.fill("#email", "allison@aplaceforseniors.org")
        await page.fill("#password", "Hugomax2025!")
        await page.click("#signin")
        await page.wait_for_timeout(5000)
        print("✅ Logged in")
        
        # Visit facility
        print(f"🔍 Visiting: {row['url']}")
        await page.goto(row['url'])
        await page.wait_for_timeout(3000)
        
        # Look for Attributes tab
        print("🔍 Looking for Attributes tab...")
        attributes_tab = await page.query_selector('button:has-text("Attributes"), a:has-text("Attributes"), [role="tab"]:has-text("Attributes")')
        if attributes_tab:
            await attributes_tab.click()
            await page.wait_for_timeout(2000)
            print("✅ Clicked Attributes tab")
        else:
            print("❌ Could not find Attributes tab")
            return
        
        # Try different selectors for checkboxes
        print("🔍 Looking for checkboxes with different selectors...")
        
        # Method 1: All checkboxes
        all_checkboxes = await page.query_selector_all('input[type="checkbox"]')
        print(f"Found {len(all_checkboxes)} total checkboxes")
        
        # Method 2: Checked checkboxes
        checked_checkboxes = await page.query_selector_all('input[type="checkbox"]:checked')
        print(f"Found {len(checked_checkboxes)} checked checkboxes")
        
        # Method 3: Look for labels
        labels = await page.query_selector_all('label')
        print(f"Found {len(labels)} labels")
        
        # Method 4: Look for any text that might be community types
        page_text = await page.inner_text('body')
        print(f"Page text length: {len(page_text)}")
        
        # Show some of the page content
        print("🔍 First 500 chars of page content:")
        print(page_text[:500])
        
        print("🔍 Browser will stay open for 10 seconds...")
        await page.wait_for_timeout(10000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_browser())
