#!/usr/bin/env python3
"""
Investigate the actual care type issue based on the user's conversation.

From the conversation, the user mentioned:
- "assisted-living homes are being shown on our site as assisted living communities"
- "if a community is which means a facility, not a home but a facility should be 
  Independent Living assisted-living and Memory Care sometimes not all the time 
  they can be Independent Living only they can be Independent Living and assisted 
  Living and they can be assisted Living only and then assisted Living and Memory Care"

This suggests the issue might be:
1. Some listings showing wrong types vs what Senior Place actually displays
2. Need to verify what Senior Place actually shows vs what our site shows
"""

import csv
import asyncio
from playwright.async_api import async_playwright
import re

async def check_specific_listing_care_types(url: str, expected_title: str) -> dict:
    """Check what care types Senior Place actually shows for a specific listing"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login to Senior Place
        page = await context.new_page()
        await page.goto("https://app.seniorplace.com/login")
        
        await page.fill('input[name="email"]', 'allison@aplaceforseniors.org')
        await page.fill('input[name="password"]', 'Hugomax2023!')
        await page.click('button[type="submit"]')
        
        # Wait for successful login
        await page.wait_for_selector('text=Communities', timeout=15000)
        await page.close()
        
        # Check the listing
        page = await context.new_page()
        attributes_url = f"{url.rstrip('/')}/attributes"
        
        try:
            await page.goto(attributes_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector('text=Community Type', timeout=10000)
            
            # Extract actual care types
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
            await browser.close()
            
            return {
                'url': url,
                'title': expected_title,
                'senior_place_care_types': care_types,
                'status': 'success'
            }
            
        except Exception as e:
            await page.close()
            await browser.close()
            return {
                'url': url,
                'title': expected_title,
                'senior_place_care_types': [],
                'status': f'error: {str(e)}'
            }

def decode_wordpress_type(type_field: str) -> str:
    """Decode WordPress type field"""
    if 'i:0;i:5;' in type_field:
        return 'Assisted Living Community'
    elif 'i:0;i:162;' in type_field:
        return 'Assisted Living Home'
    elif 'i:0;i:6;' in type_field:
        return 'Independent Living'
    elif 'i:0;i:3;' in type_field:
        return 'Memory Care'
    elif 'i:0;i:7;' in type_field:
        return 'Nursing Home'
    elif 'i:0;i:488;' in type_field:
        return 'Home Care'
    else:
        return 'Other/Unknown'

async def main():
    print("🔍 Investigating care type discrepancies...")
    print("Checking what Senior Place actually shows vs what our WordPress has")
    print()
    
    # Find some examples from the conversation
    test_listings = []
    
    with open('organized_csvs/Listings-Export-2025-August-28-1956.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '')
            type_field = row.get('type', '')
            senior_place_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
            
            if not senior_place_url or 'seniorplace.com' not in senior_place_url:
                continue
                
            wordpress_type = decode_wordpress_type(type_field)
            
            # Get some examples of different types
            if len(test_listings) < 10:
                test_listings.append({
                    'title': title,
                    'url': senior_place_url,
                    'wordpress_type': wordpress_type,
                    'type_field': type_field
                })
    
    print(f"📋 Testing {len(test_listings)} listings to compare Senior Place vs WordPress:")
    print()
    
    for i, listing in enumerate(test_listings):
        print(f"{i+1}. {listing['title']}")
        print(f"   WordPress shows: {listing['wordpress_type']}")
        print(f"   Checking Senior Place...")
        
        # Check what Senior Place actually shows
        result = await check_specific_listing_care_types(listing['url'], listing['title'])
        
        if result['status'] == 'success':
            sp_types = result['senior_place_care_types']
            print(f"   Senior Place shows: {sp_types}")
            
            # Apply canonical mapping to see what WordPress SHOULD show
            canonical_types = []
            canonical_mapping = {
                "assisted living facility": "Assisted Living Community",
                "assisted living home": "Assisted Living Home",
                "independent living": "Independent Living",
                "memory care": "Memory Care",
                "skilled nursing": "Nursing Home",
                "continuing care retirement community": "Assisted Living Community",
                "in-home care": "Home Care",
                "home health": "Home Care",
                "hospice": "Home Care",
                "respite care": "Assisted Living Community",
            }
            
            for sp_type in sp_types:
                sp_lower = sp_type.lower()
                if sp_lower in canonical_mapping:
                    canonical = canonical_mapping[sp_lower]
                    if canonical not in canonical_types:
                        canonical_types.append(canonical)
            
            print(f"   Should map to: {canonical_types}")
            
            # Check for discrepancy
            if canonical_types and listing['wordpress_type'] not in canonical_types:
                print(f"   ⚠️  DISCREPANCY: WordPress has '{listing['wordpress_type']}' but should be {canonical_types}")
            elif canonical_types and listing['wordpress_type'] in canonical_types:
                print(f"   ✅ MATCH: Correct mapping")
            elif not canonical_types:
                print(f"   ❓ No mappable types found on Senior Place")
        else:
            print(f"   ❌ Error: {result['status']}")
        
        print()

if __name__ == "__main__":
    asyncio.run(main())
