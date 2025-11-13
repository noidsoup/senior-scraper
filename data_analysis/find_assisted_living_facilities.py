#!/usr/bin/env python3
"""
Find Senior Place listings that actually show "Assisted Living Facility" 
to understand the pattern and fix the mapping.
"""

import csv
import asyncio
from playwright.async_api import async_playwright
import random

async def check_listing_care_types(context, url: str, title: str) -> dict:
    """Check what care types a listing actually shows on Senior Place"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        
        # Wait for community type section
        await page.wait_for_selector('text=Community Type', timeout=8000)
        
        # Extract checked care types
        care_types = await page.evaluate("""
            () => {
                const careTypes = [];
                const labels = Array.from(document.querySelectorAll("label.inline-flex"));
                
                for (const label of labels) {
                    const textEl = label.querySelector("div.ml-2");
                    const input = label.querySelector('input[type="checkbox"]');
                    
                    if (!textEl || !input) continue;
                    if (!input.checked) continue;
                    
                    const name = (textEl.textContent || "").trim();
                    if (name) careTypes.push(name);
                }
                
                return careTypes;
            }
        """)
        
        await page.close()
        
        return {
            'title': title,
            'url': url,
            'care_types': care_types,
            'status': 'success'
        }
        
    except Exception as e:
        if 'page' in locals():
            await page.close()
        return {
            'title': title,
            'url': url,
            'care_types': [],
            'status': f'error: {str(e)}'
        }

async def find_facilities():
    """Find listings that show as 'Assisted Living Facility' on Senior Place"""
    
    # Get some random Senior Place URLs to test
    test_urls = []
    
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        all_listings = []
        for row in reader:
            title = row.get('Title', '').strip('"')
            senior_place_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
            
            if senior_place_url and 'seniorplace.com' in senior_place_url:
                all_listings.append({
                    'title': title,
                    'url': senior_place_url
                })
        
        # Take a random sample to test
        test_urls = random.sample(all_listings, min(30, len(all_listings)))
    
    print(f"🔍 Testing {len(test_urls)} random Senior Place listings to find facilities...")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login
        page = await context.new_page()
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', 'allison@aplaceforseniors.org')
        await page.fill('input[name="password"]', 'Hugomax2023!')
        await page.click('button[type="submit"]')
        await page.wait_for_selector('text=Communities', timeout=15000)
        await page.close()
        
        print("✅ Logged in successfully")
        print()
        
        facilities_found = []
        homes_found = []
        other_types = []
        
        for i, listing in enumerate(test_urls):
            print(f"📋 {i+1}/{len(test_urls)}: {listing['title']}")
            
            result = await check_listing_care_types(context, listing['url'], listing['title'])
            
            if result['status'] == 'success':
                care_types = result['care_types']
                print(f"    Care types: {care_types}")
                
                if 'Assisted Living Facility' in care_types:
                    facilities_found.append(result)
                    print(f"    🎯 FACILITY FOUND!")
                elif 'Assisted Living Home' in care_types:
                    homes_found.append(result)
                    print(f"    🏠 Home")
                else:
                    other_types.append(result)
                    print(f"    ℹ️  Other")
            else:
                print(f"    ❌ {result['status']}")
            
            print()
            
            # Add small delay
            await asyncio.sleep(1)
        
        await browser.close()
        
        # Results summary
        print("🎯 RESULTS SUMMARY")
        print("=" * 50)
        print(f"Assisted Living Facilities found: {len(facilities_found)}")
        print(f"Assisted Living Homes found: {len(homes_found)}")
        print(f"Other types found: {len(other_types)}")
        print()
        
        if facilities_found:
            print("🏢 ASSISTED LIVING FACILITIES:")
            for facility in facilities_found:
                print(f"  • {facility['title']}")
                print(f"    Types: {facility['care_types']}")
                print(f"    URL: {facility['url']}")
                print()
        else:
            print("❌ No 'Assisted Living Facility' listings found in this sample")
            print("   This might mean:")
            print("   1. They're rare and we need a larger sample")
            print("   2. Senior Place changed their terminology")
            print("   3. Our scraping logic needs adjustment")

if __name__ == "__main__":
    asyncio.run(find_facilities())
