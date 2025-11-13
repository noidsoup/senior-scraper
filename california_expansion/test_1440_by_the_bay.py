#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright
import csv

async def test_1440_by_the_bay():
    print("🔍 Testing 1440 By The Bay specifically...")
    
    # Read the CSV and find 1440 By The Bay
    with open('california_seniorplace_data_DEDUPED.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Find the specific facility
    target_facility = None
    for row in rows:
        if "1440 By The Bay" in row['title']:
            target_facility = row
            break
    
    if not target_facility:
        print("❌ Could not find 1440 By The Bay")
        return
    
    print(f"📋 Found: {target_facility['title']}")
    print(f"🔍 Current type: {target_facility['type']}")
    print(f"🔍 URL: {target_facility['url']}")
    
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
        print(f"🔍 Visiting: {target_facility['url']}")
        await page.goto(target_facility['url'])
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
        
        # Find checked checkboxes
        print("🔍 Looking for checked checkboxes...")
        checked_checkboxes = await page.query_selector_all('input[type="checkbox"]:checked')
        print(f"Found {len(checked_checkboxes)} checked checkboxes")
        
        types = []
        for i, cb in enumerate(checked_checkboxes):
            print(f"\n🔍 Processing checkbox {i+1}:")
            
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
                print(f"  ❌ Error: {e}")
        
        print(f"\n🎯 Final types found for 1440 By The Bay: {types}")
        
        # Show what the mapping would be
        TYPE_TO_CANONICAL = {
            "Assisted Living Home": "Assisted Living Home",
            "Assisted Living Facility": "Assisted Living Community",
            "Assisted Living Community": "Assisted Living Community",
            "Independent Living": "Independent Living",
            "Memory Care": "Memory Care",
            "Skilled Nursing": "Nursing Home",
            "Nursing Home": "Nursing Home",
            "Continuing Care Retirement Community": "Assisted Living Community",
            "In-Home Care": "Home Care",
            "Home Health": "Home Care",
            "Hospice": "Home Care",
            "Home Care": "Home Care",
        }
        
        normalized_types = []
        for t in types:
            canonical = TYPE_TO_CANONICAL.get(t, t)
            normalized_types.append(canonical)
        
        print(f"🗺️ Mapped to canonical types: {normalized_types}")
        
        print("🔍 Browser will stay open for 10 seconds...")
        await page.wait_for_timeout(10000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_1440_by_the_bay())
