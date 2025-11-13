#!/usr/bin/env python3
"""
Sync Seniorly listings with Senior Place care types
1. Get title from Seniorly listing
2. Search on Senior Place
3. Extract care type pills from result card
4. Map to our canonical categories
5. Update normalized_types
"""

import asyncio
import csv
from playwright.async_api import async_playwright

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

async def search_and_extract_care_types(page, listing_title: str):
    """Search for listing on Senior Place and extract care types from full listing page"""
    try:
        # Navigate to communities page
        await page.goto('https://app.seniorplace.com/communities')
        await page.wait_for_load_state('networkidle')
        
        # Search for the title
        search_input = page.locator('input[type="text"][placeholder="Name, Contact, or Street"]')
        await search_input.wait_for(timeout=10000)
        await search_input.fill(listing_title)
        await page.wait_for_timeout(5000)  # Wait longer for results to load
        
        # Find result cards - look for the flex-1 overflow-visible div that contains the title and care types
        result_cards = page.locator('div[class*="flex-1 overflow-visible"]')
        
        if await result_cards.count() > 0:
            # Look for exact title match in first few results
            for i in range(min(3, await result_cards.count())):
                card = result_cards.nth(i)
                title_element = card.locator('h3 a')
                
                if await title_element.count() > 0:
                    found_title = await title_element.text_content()
                    
                    # Check if this is our listing (exact or close match)
                    if (found_title.lower().strip() == listing_title.lower().strip() or 
                        listing_title.lower() in found_title.lower() or
                        found_title.lower() in listing_title.lower()):
                        
                        print(f"    ✅ Found match: {found_title}")
                        
                        # Get URL
                        url = await title_element.get_attribute('href')
                        if url and not url.startswith('http'):
                            url = f"https://app.seniorplace.com{url}"
                        
                        print(f"    🔗 URL: {url}")
                        
                        # Extract care type pills from the search result card
                        care_types = []
                        
                        # Look for care type pills within this specific card
                        pill_spans = card.locator('span[class*="rounded-full"]')
                        
                        for j in range(await pill_spans.count()):
                            span = pill_spans.nth(j)
                            span_text = await span.text_content()
                            span_classes = await span.get_attribute('class')
                            
                            # Check if this span has color classes (any color)
                            if span_text and any(color in span_classes for color in ['amber', 'yellow', 'blue', 'green', 'purple', 'red', 'gray', 'cyan', 'teal']):
                                care_types.append(span_text.strip())
                                print(f"      🎯 Found pill: '{span_text}' (classes: {span_classes})")
                        
                        print(f"    🏷️  Care types found on result card: {', '.join(care_types)}")
                        
                        return {
                            'found': True,
                            'title': found_title,
                            'care_types': care_types,
                            'url': url
                        }
            
            print(f"    ❌ No exact title match found in results")
        else:
            print(f"    ❌ No search results found")
            
        return {'found': False, 'care_types': [], 'url': None}
        
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
        return {'found': False, 'care_types': [], 'url': None}

async def map_to_canonical(care_types):
    """Map Senior Place care types to our canonical categories"""
    canonical = []
    
    for care_type in care_types:
        if care_type in SENIORPLACE_TO_CANONICAL:
            canonical.append(SENIORPLACE_TO_CANONICAL[care_type])
        else:
            print(f"      ⚠️  Unmapped: {care_type}")
            canonical.append(care_type)  # Keep original if not mapped
    
    return list(set(canonical))  # Remove duplicates

async def main():
    """Main function to sync Seniorly listings with Senior Place care types"""
    
    input_file = "organized_csvs/01_WORDPRESS_IMPORT_READY.csv"
    output_file = "organized_csvs/02_SENIORLY_CARE_TYPES_SYNCED.csv"
    
    print("🔄 Starting Seniorly care type sync with Senior Place...")
    
    # Read data
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        listings = list(reader)
    
    print(f"📊 Loaded {len(listings)} listings")
    
    # Find Seniorly listings
    seniorly_listings = []
    for listing in listings:
        website = listing.get('website', '').strip()
        if 'seniorly.com' in website.lower():
            seniorly_listings.append(listing)
    
    print(f"🎯 Found {len(seniorly_listings)} Seniorly listings to sync")
    
    # Process with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Login
        print("🔐 Logging into Senior Place...")
        await page.goto('https://app.seniorplace.com/login')
        await page.wait_for_load_state('networkidle')
        
        if await page.locator('input[type="email"]').count() > 0:
            await page.fill('input[type="email"]', 'allison@aplaceforseniors.org')
            await page.fill('input[type="password"]', 'Hugomax2023!')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            print("✅ Logged in")
        
        updated_count = 0
        
        for i, listing in enumerate(seniorly_listings, 1):
            title = listing.get('Title', '').strip()
            if not title:
                continue
                
            print(f"\n🔍 [{i}/{len(seniorly_listings)}] Processing: {title}")
            
            # Search and extract care types
            result = await search_and_extract_care_types(page, title)
            
            if result['found']:
                print(f"    🏷️  Care types found: {', '.join(result['care_types'])}")
                
                # Map to canonical categories
                canonical_types = await map_to_canonical(result['care_types'])
                print(f"    🎯 Mapped to: {', '.join(canonical_types)}")
                
                # Update listing
                old_types = listing.get('normalized_types', 'N/A')
                listing['normalized_types'] = ', '.join(canonical_types)
                listing['senior_place_url'] = result['url']
                
                print(f"    🔄 Updated: {old_types} → {', '.join(canonical_types)}")
                updated_count += 1
                
            else:
                print(f"    ⚠️  Keeping existing types: {listing.get('normalized_types', 'N/A')}")
            
            # Small delay
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
