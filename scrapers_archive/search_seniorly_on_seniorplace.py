#!/usr/bin/env python3
"""
Search Seniorly listings on Senior Place to get accurate care types
Uses Senior Place search functionality to find listings and extract care type pills
"""

import asyncio
import csv
import json
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright
import time

# Our canonical mapping system
SENIORPLACE_TO_CANONICAL = {
    'Independent Living': 'Independent Living',
    'Assisted Living Facility': 'Assisted Living Community', 
    'Assisted Living Home': 'Assisted Living Home',
    'Memory Care': 'Memory Care',
    'Skilled Nursing': 'Nursing Home',
    'Continuing Care Retirement Community': 'Assisted Living Community',
    'In-Home Care': 'Home Care',
    'Home Health': 'Home Care',
    'Hospice': 'Home Care',
    'Respite Care': 'Assisted Living Community',
    'Board and Care Home': 'Assisted Living Home',
    'Adult Care Home': 'Assisted Living Home'
}

async def search_seniorplace_for_listing(page, listing_title: str) -> Optional[Dict]:
    """
    Search for a listing on Senior Place and extract care types from results
    """
    try:
        # Navigate to communities page
        await page.goto('https://app.seniorplace.com/communities')
        await page.wait_for_load_state('networkidle')
        
        # Find and fill the search input
        search_input = page.locator('input[placeholder="Name, Contact, or Street"]')
        await search_input.fill(listing_title)
        
        # Wait for search results to load
        await page.wait_for_timeout(2000)
        
        # Look for the first result card
        result_cards = page.locator('div[class*="flex space-x-6 w-full items-start justify-between p-6"]')
        
        if await result_cards.count() > 0:
            first_card = result_cards.nth(0)
            
            # Extract the title from the result
            title_element = first_card.locator('h3 a')
            if await title_element.count() > 0:
                found_title = await title_element.text_content()
                
                # Extract care type pills
                care_type_pills = first_card.locator('span[class*="rounded-full bg-amber-100 text-amber-800"], span[class*="rounded-full bg-yellow-100 text-yellow-800"], span[class*="rounded-full bg-blue-100 text-blue-800"], span[class*="rounded-full bg-green-100 text-green-800"], span[class*="rounded-full bg-purple-100 text-purple-800"], span[class*="rounded-full bg-red-100 text-red-800"]')
                
                care_types = []
                for i in range(await care_type_pills.count()):
                    pill_text = await care_type_pills.nth(i).text_content()
                    if pill_text:
                        care_types.append(pill_text.strip())
                
                # Extract the URL if available
                url_element = first_card.locator('h3 a')
                url = await url_element.get_attribute('href') if await url_element.count() > 0 else None
                if url and not url.startswith('http'):
                    url = f"https://app.seniorplace.com{url}"
                
                return {
                    'found_title': found_title,
                    'care_types': care_types,
                    'url': url,
                    'matched': True
                }
        
        return {
            'found_title': None,
            'care_types': [],
            'url': None,
            'matched': False
        }
        
    except Exception as e:
        print(f"  ❌ Error searching for '{listing_title}': {str(e)}")
        return None

async def map_care_types_to_canonical(care_types: List[str]) -> List[str]:
    """Map Senior Place care types to our canonical CMS categories"""
    canonical_types = []
    
    for care_type in care_types:
        if care_type in SENIORPLACE_TO_CANONICAL:
            canonical_types.append(SENIORPLACE_TO_CANONICAL[care_type])
        else:
            print(f"    ⚠️  Unmapped care type: {care_type}")
            canonical_types.append(care_type)  # Keep original if not mapped
    
    return list(set(canonical_types))  # Remove duplicates

async def main():
    """Main function to process Seniorly listings"""
    
    # Read our current CSV
    input_file = "organized_csvs/01_WORDPRESS_IMPORT_READY.csv"
    output_file = "organized_csvs/02_SENIORLY_CARE_TYPES_CORRECTED.csv"
    
    print("🔍 Starting Seniorly care type correction via Senior Place search...")
    
    # Read existing data
    listings = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        listings = list(reader)
    
    print(f"📊 Loaded {len(listings)} listings")
    
    # Filter for Seniorly-only listings (those with website containing "seniorly.com")
    seniorly_listings = []
    for listing in listings:
        website = listing.get('website', '').strip()
        
        if 'seniorly.com' in website.lower():
            seniorly_listings.append(listing)
    
    print(f"🎯 Found {len(seniorly_listings)} Seniorly-only listings to process")
    
    # Process with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to True for production
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login to Senior Place (if needed)
        print("🔐 Logging into Senior Place...")
        await page.goto('https://app.seniorplace.com/login')
        await page.wait_for_load_state('networkidle')
        
        # Check if we need to login
        if await page.locator('input[type="email"]').count() > 0:
            await page.fill('input[type="email"]', 'allison@aplaceforseniors.org')
            await page.fill('input[type="password"]', 'Hugomax2023!')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            print("✅ Logged in successfully")
        else:
            print("ℹ️  Already logged in or no login required")
        
        processed_count = 0
        updated_count = 0
        
        for listing in seniorly_listings:
            title = listing.get('Title', '').strip()
            if not title:
                continue
                
            print(f"\n🔍 [{processed_count + 1}/{len(seniorly_listings)}] Searching for: {title}")
            
            # Search on Senior Place
            result = await search_seniorplace_for_listing(page, title)
            
            if result and result['matched']:
                print(f"  ✅ Found: {result['found_title']}")
                print(f"  🏷️  Care types: {', '.join(result['care_types'])}")
                
                # Map to canonical categories
                canonical_types = await map_care_types_to_canonical(result['care_types'])
                print(f"  🎯 Canonical: {', '.join(canonical_types)}")
                
                # Update the listing
                listing['normalized_types'] = ', '.join(canonical_types)
                if result['url']:
                    listing['senior_place_url'] = result['url']
                
                print(f"  🔄 Updated: {listing['Title']}")
                print(f"     Old types: {listing.get('normalized_types', 'N/A')}")
                print(f"     New types: {', '.join(canonical_types)}")
                print(f"     Senior Place URL: {result['url']}")
                
                updated_count += 1
                
            else:
                print(f"  ❌ Not found on Senior Place")
                # Keep existing normalized_types if available
            
            processed_count += 1
            
            # Small delay to be respectful
            await asyncio.sleep(1)
        
        await browser.close()
    
    # Write updated data
    print(f"\n💾 Writing updated data to {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=listings[0].keys())
        writer.writeheader()
        writer.writerows(listings)
    
    print(f"✅ Complete! Updated {updated_count} out of {len(seniorly_listings)} Seniorly listings")
    print(f"📁 Output file: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
