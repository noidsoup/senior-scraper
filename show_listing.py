#!/usr/bin/env python3
"""Quick script to fetch and display a single Senior Place listing"""

import asyncio
import os
import json
from playwright.async_api import async_playwright

# Get a sample URL from the CSV - pick one with care types
import csv
sample_row = None
with open('monthly_updates/20251205_115842/new_listings_20251205_115842.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    for row in rows:
        if row.get('normalized_types') and row['normalized_types'].strip():
            sample_row = row
            break
    if not sample_row and rows:
        sample_row = rows[0]
sample_url = sample_row.get('senior_place_url', '') if sample_row else ''

if not sample_url:
    print("No URL found in CSV")
    exit(1)

print(f"Fetching listing from: {sample_url}\n")

async def fetch_listing():
    sp_user = os.getenv('SP_USERNAME')
    sp_pass = os.getenv('SP_PASSWORD')
    
    if not sp_user or not sp_pass:
        print("ERROR: SP_USERNAME and SP_PASSWORD must be set")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login
            print("Logging into Senior Place...")
            await page.goto("https://app.seniorplace.com/login", timeout=30000)
            await page.fill('input[name="email"]', sp_user)
            await page.fill('input[name="password"]', sp_pass)
            await page.click('button[type="submit"]')
            await page.wait_for_selector('text=Communities', timeout=15000)
            print("✓ Logged in\n")
            
            # Go to listing page
            print("Loading listing page...")
            await page.goto(sample_url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(1500)
            
            # Extract title
            title_el = await page.query_selector('h1')
            title = await title_el.inner_text() if title_el else 'Unknown'
            
            # Extract address
            address = ''
            city = ''
            state = ''
            zip_code = ''
            
            address_els = await page.query_selector_all('address p')
            if len(address_els) >= 1:
                address = (await address_els[0].inner_text()) or ''
            if len(address_els) >= 2:
                location = (await address_els[1].inner_text()) or ''
                parts = location.split(',')
                if len(parts) >= 2:
                    city = parts[0].strip()
                    state_zip = parts[1].strip().split()
                    if len(state_zip) > 0:
                        state = state_zip[0]
                    if len(state_zip) > 1:
                        zip_code = state_zip[1]
            
            # Go to attributes page for full details
            print("Loading attributes page...")
            attrs_url = sample_url.rstrip('/') + '/attributes'
            await page.goto(attrs_url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(1000)
            
            # Extract care types
            care_types = await page.evaluate("""
                () => {
                    const types = [];
                    const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                    
                    for (const label of labels) {
                        const textEl = label.querySelector("div.ml-2");
                        const input = label.querySelector('input[type="checkbox"]');
                        
                        if (!textEl || !input) continue;
                        if (!input.checked) continue;
                        
                        const name = (textEl.textContent || "").trim();
                        if (name) types.push(name);
                    }
                    
                    return types;
                }
            """)
            
            # Extract pricing and description
            pricing_and_desc = await page.evaluate("""
                () => {
                    const result = {};
                    const groups = document.querySelectorAll('.form-group');
                    for (const group of groups) {
                        const labelText = group.textContent || '';
                        const input = group.querySelector('input');
                        const textarea = group.querySelector('textarea');
                        
                        if (labelText.includes('Monthly Base Price') && input) {
                            result.monthly_base_price = input.value;
                        }
                        if (labelText.includes('High End') && input) {
                            result.price_high_end = input.value;
                        }
                        if (labelText.includes('Second Person Fee') && input) {
                            result.second_person_fee = input.value;
                        }
                        if (labelText.includes('Description') && (textarea || input)) {
                            const source = textarea || input;
                            result.description = (source.value || source.textContent || '').trim();
                        }
                    }
                    return result;
                }
            """)
            
            # Extract featured image
            await page.goto(sample_url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(500)
            featured_image = ''
            img_el = await page.query_selector("img")
            if img_el:
                src = await img_el.get_attribute('src')
                if src:
                    if src.startswith('/api/files/'):
                        featured_image = f"https://placement-crm-cdn.s3.us-west-2.amazonaws.com{src}"
                    else:
                        featured_image = src if src.startswith('http') else f"https://app.seniorplace.com{src}"
            
            listing = {
                'title': title.strip(),
                'address': address.strip(),
                'city': city.strip(),
                'state': state.strip(),
                'zip': zip_code.strip(),
                'care_types': care_types,
                'care_types_display': ', '.join(care_types) if care_types else '',
                'monthly_base_price': pricing_and_desc.get('monthly_base_price', ''),
                'price_high_end': pricing_and_desc.get('price_high_end', ''),
                'second_person_fee': pricing_and_desc.get('second_person_fee', ''),
                'description': pricing_and_desc.get('description', ''),
                'url': sample_url,
                'featured_image': featured_image
            }
            
            # Display
            print("\n" + "=" * 80)
            print("SENIOR PLACE LISTING DATA")
            print("=" * 80)
            print(f"\n📋 TITLE: {listing['title']}")
            print(f"\n📍 ADDRESS:")
            print(f"   Street: {listing['address']}")
            print(f"   City: {listing['city']}")
            print(f"   State: {listing['state']}")
            print(f"   ZIP: {listing['zip']}")
            print(f"\n🔗 URL: {listing['url']}")
            print(f"\n🖼️  FEATURED IMAGE: {listing['featured_image']}")
            print(f"\n🏥 CARE TYPES ({len(care_types)}):")
            for ct in care_types:
                print(f"   • {ct}")
            print(f"\n💰 PRICING:")
            print(f"   Monthly Base Price: ${listing['monthly_base_price']}" if listing['monthly_base_price'] else "   Monthly Base Price: (not set)")
            print(f"   High End: ${listing['price_high_end']}" if listing['price_high_end'] else "   High End: (not set)")
            print(f"   Second Person Fee: ${listing['second_person_fee']}" if listing['second_person_fee'] else "   Second Person Fee: (not set)")
            print(f"\n📝 DESCRIPTION:")
            desc = listing['description']
            if desc:
                print(f"   {desc[:200]}..." if len(desc) > 200 else f"   {desc}")
            else:
                print("   (no description found)")
            
            print("\n" + "=" * 80)
            print("\nJSON Output:")
            print(json.dumps(listing, indent=2, ensure_ascii=False))
            
            await browser.close()
            
        except Exception as e:
            await browser.close()
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fetch_listing())


