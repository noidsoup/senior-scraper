#!/usr/bin/env python3
"""TEST: Scrape 2 AZ listings and verify care types work"""

import asyncio
import csv
from playwright.async_api import async_playwright

USERNAME = "allison@aplaceforseniors.org"
PASSWORD = "Hugomax2025!"

async def test_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging in...")
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        
        # Go to communities
        print("📍 Getting first page...")
        await page.goto("https://app.seniorplace.com/communities")
        await page.wait_for_timeout(3000)
        
        # Get first 2 AZ listings
        cards = await page.query_selector_all('div.flex.space-x-6')
        test_listings = []
        
        for card in cards[:10]:  # Check first 10 cards
            try:
                # Get title and URL
                title_el = await card.query_selector('h3 a')
                if not title_el:
                    continue
                    
                title = await title_el.inner_text()
                href = await title_el.get_attribute('href')
                url = f"https://app.seniorplace.com{href}" if href.startswith('/') else href
                
                # Get address
                address_lines = await card.query_selector_all("div.flex-1 > div > div > div")
                if len(address_lines) < 2:
                    continue
                    
                citystatezip = await address_lines[1].inner_text()
                
                # Check if AZ
                if 'AZ' in citystatezip:
                    test_listings.append({
                        'title': title.strip(),
                        'url': url,
                        'address': citystatezip.strip()
                    })
                    print(f"  Found: {title.strip()}")
                    
                if len(test_listings) >= 2:
                    break
                    
            except:
                continue
        
        print(f"\n✅ Found {len(test_listings)} AZ listings to test\n")
        
        # Now visit each detail page and get care types
        for idx, listing in enumerate(test_listings, 1):
            print(f"🔍 Testing listing {idx}: {listing['title']}")
            print(f"   URL: {listing['url']}")
            
            try:
                await page.goto(listing['url'])
                await page.wait_for_timeout(2000)
                
                # Click Attributes tab
                print("   Clicking Attributes tab...")
                attributes_tab = await page.query_selector('button:has-text("Attributes"), a:has-text("Attributes")')
                if attributes_tab:
                    await attributes_tab.click()
                    await page.wait_for_timeout(1000)
                    print("   ✅ Attributes tab clicked")
                else:
                    print("   ⚠️ No Attributes tab found")
                
                # Find checked checkboxes
                print("   Looking for checked care types...")
                care_types = []
                
                # Look for checked checkboxes in the Community Type(s) section
                checked_boxes = await page.query_selector_all('input[type="checkbox"][checked]')
                print(f"   Found {len(checked_boxes)} checked checkboxes")
                
                for checkbox in checked_boxes:
                    try:
                        # Get parent label
                        label = await checkbox.evaluate_handle('el => el.closest("label")')
                        if label:
                            text = await label.inner_text()
                            # Only community types
                            if any(keyword in text for keyword in ['Living', 'Care', 'Nursing', 'Memory', 'Hospice', 'Health', 'Respite', 'Community']):
                                care_types.append(text.strip())
                                print(f"     ✓ {text.strip()}")
                    except:
                        continue
                
                listing['care_types'] = ', '.join(care_types) if care_types else 'NO CARE TYPES FOUND'
                print(f"   📋 Care types: {listing['care_types']}\n")
                
            except Exception as e:
                print(f"   ❌ Error: {e}\n")
                listing['care_types'] = 'ERROR'
        
        # Save to CSV
        output_file = 'TEST_CARE_TYPES.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'address', 'url', 'care_types'])
            writer.writeheader()
            writer.writerows(test_listings)
        
        print("=" * 70)
        print(f"✅ Test complete! Saved to: {output_file}")
        print("=" * 70)
        
        # Show the CSV
        print("\n📄 CSV CONTENTS:")
        print("-" * 70)
        with open(output_file, 'r') as f:
            print(f.read())
        
        await browser.close()

asyncio.run(test_scraper())

