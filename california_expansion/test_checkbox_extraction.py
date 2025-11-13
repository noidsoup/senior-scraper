#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright
import csv

async def test_checkbox_extraction():
    print("🔍 Testing checkbox extraction...")
    
    # Read one row
    with open('california_seniorplace_data_DEDUPED.csv', 'r') as f:
        reader = csv.DictReader(f)
        row = next(reader)
    
    print(f"📋 Testing with: {row['title']}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
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
        
        # Click Attributes tab
        print("🔍 Clicking Attributes tab...")
        attributes_tab = await page.query_selector('button:has-text("Attributes"), a:has-text("Attributes"), [role="tab"]:has-text("Attributes")')
        if attributes_tab:
            await attributes_tab.click()
            await page.wait_for_timeout(2000)
            print("✅ Clicked Attributes tab")
        else:
            print("❌ Could not find Attributes tab")
            return
        
        # Find checked checkboxes and extract text
        print("🔍 Extracting text from checked checkboxes...")
        checked_checkboxes = await page.query_selector_all('input[type="checkbox"]:checked')
        print(f"Found {len(checked_checkboxes)} checked checkboxes")
        
        types = []
        for i, cb in enumerate(checked_checkboxes):
            print(f"\n🔍 Processing checkbox {i+1}:")
            
            # Method 1: Get label text
            try:
                label = await cb.evaluate_handle('el => el.closest("label")')
                if label:
                    text = await label.inner_text()
                    print(f"  Label text: '{text}'")
                    if text and text.strip():
                        text_clean = text.strip()
                        if any(keyword in text_clean.lower() for keyword in ['assisted', 'living', 'memory', 'nursing', 'independent', 'care', 'home', 'facility']):
                            types.append(text_clean)
                            print(f"  ✅ Added type: {text_clean}")
                        else:
                            print(f"  ⚠️ Skipped (not a community type): {text_clean}")
            except Exception as e:
                print(f"  ❌ Error getting label: {e}")
            
            # Method 2: Get parent text
            try:
                parent = await cb.evaluate_handle('el => el.parentElement')
                if parent:
                    parent_text = await parent.inner_text()
                    print(f"  Parent text: '{parent_text}'")
            except Exception as e:
                print(f"  ❌ Error getting parent: {e}")
            
            # Method 3: Get next sibling text
            try:
                next_sibling = await cb.evaluate_handle('el => el.nextElementSibling')
                if next_sibling:
                    sibling_text = await next_sibling.inner_text()
                    print(f"  Next sibling text: '{sibling_text}'")
            except Exception as e:
                print(f"  ❌ Error getting next sibling: {e}")
        
        print(f"\n🎯 Final types found: {types}")
        
        print("🔍 Browser will stay open for 5 seconds...")
        await page.wait_for_timeout(5000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_checkbox_extraction())
