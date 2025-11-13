#!/usr/bin/env python3
"""
Scrape care types directly from Seniorly URLs
"""

import csv
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import argparse

async def scrape_seniorly_care_types(session, url):
    """Scrape care types from a Seniorly listing page"""
    
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Map Seniorly care types to our canonical CMS categories
                SENIORLY_TO_CANONICAL = {
                    'assisted living': 'Assisted Living Community',
                    'assisted living community': 'Assisted Living Community',
                    'assisted living facility': 'Assisted Living Community',
                    'board and care home': 'Assisted Living Home',
                    'adult care home': 'Assisted Living Home',
                    'memory care': 'Memory Care',
                    'independent living': 'Independent Living',
                    'nursing home': 'Nursing Home',
                    'skilled nursing': 'Nursing Home',
                    'home care': 'Home Care',
                    'in-home care': 'Home Care',
                    'continuing care retirement community': 'Assisted Living Community',
                    # Note: Do not include service-only terms like "respite care" in mapping.
                }
                
                # Look for COMMUNITY TYPES (not care services) by targeting the care section specifically
                found_community_types = []
                
                # Method 1: Target the specific community types section (most reliable)
                care_section = soup.find('section', id='care')
                if care_section:
                    # Extract COMMUNITY TYPES from the care section only (not care services)
                    community_type_items = care_section.find_all('li', id=lambda x: x and any(community_type in x.lower() for community_type in ['assisted-living', 'board-and-care-home', 'memory-care', 'independent-living', 'nursing-home', 'home-care']))
                    
                    for item in community_type_items:
                        item_text = item.get_text().lower().strip()
                        
                        # Map the found community types to our canonical categories
                        if 'assisted living' in item_text:
                            found_community_types.append('Assisted Living Community')
                        elif 'board and care home' in item_text:
                            found_community_types.append('Assisted Living Home')
                        elif 'memory care' in item_text:
                            found_community_types.append('Memory Care')
                        elif 'independent living' in item_text:
                            found_community_types.append('Independent Living')
                        elif 'nursing home' in item_text:
                            found_community_types.append('Nursing Home')
                        elif 'home care' in item_text:
                            found_community_types.append('Home Care')
                    
                    # Log what we found
                    if found_community_types:
                        print(f"  ✅ Found {len(found_community_types)} community types: {', '.join(found_community_types)}")
                    else:
                        print(f"  ⚠️  No community types found in care section")
                
                # Method 2: Fallback - look in main content if care section not found
                if not found_community_types:
                    main_content = soup.find('main') or soup.find('article')
                    if main_content:
                        content_text = main_content.get_text().lower()
                        
                        # Look for specific community type mentions
                        for seniorly_type, canonical_type in SENIORLY_TO_CANONICAL.items():
                            if seniorly_type in content_text and canonical_type not in found_community_types:
                                found_community_types.append(canonical_type)
                    
                    print(f"  ⚠️  Fallback to main content search")
                
                # Return mapped canonical community types (not care services)
                return ', '.join(sorted(found_community_types)) if found_community_types else 'No community types found'
            
            else:
                return f'HTTP {response.status}'
                
    except Exception as e:
        return f'Error: {str(e)}'

async def update_seniorly_care_types(max_items: int | None = None):
    """Update care types for all Seniorly listings.

    Args:
        max_items: If provided, process at most this many Seniorly listings (for spot checks).
    """
    
    print("🔍 SCRAPING SENIORLY CARE TYPES")
    print("=" * 50)
    
    input_file = "organized_csvs/01_WORDPRESS_IMPORT_READY.csv"
    output_file = "organized_csvs/SENIORLY_CARE_TYPES_UPDATED.csv"
    
    # Read the import file
    listings = []
    seniorly_listings = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            website = row.get('website', '').strip()
            title = row.get('Title', '').strip()
            
            # Check if this is a Seniorly listing
            if 'seniorly.com' in website.lower():
                seniorly_listings.append({
                    'row': row,
                    'title': title,
                    'seniorly_url': website,
                    'current_types': row.get('normalized_types', '')
                })
            
            listings.append(row)
    
    print(f"📊 Found {len(seniorly_listings)} Seniorly listings to update")
    print()
    
    # Scrape care types for each Seniorly listing
    updated_count = 0
    failed_count = 0
    
    async with aiohttp.ClientSession() as session:
        for i, listing in enumerate(seniorly_listings, 1):
            print(f"🔍 {i:3d}/{len(seniorly_listings)}: {listing['title'][:40]}...")
            
            # Scrape care types from Seniorly
            scraped_types = await scrape_seniorly_care_types(session, listing['seniorly_url'])
            
            if scraped_types and 'Error' not in scraped_types and 'HTTP' not in scraped_types:
                # Update the listing with scraped care types
                listing['row']['normalized_types'] = scraped_types
                updated_count += 1
                print(f"     ✅ Updated: {scraped_types}")
            else:
                failed_count += 1
                print(f"     ❌ Failed: {scraped_types}")
            
            # Small delay to be respectful
            await asyncio.sleep(0.5)
            
            # Progress update every 50 listings
            if i % 50 == 0:
                print(f"     📊 Progress: {i}/{len(seniorly_listings)} (Updated: {updated_count}, Failed: {failed_count})")

            # Optional cap for spot checks
            if max_items is not None and i >= max_items:
                print(f"\n⏸️  Reached max_items={max_items}; stopping early for verification.")
                break
    
    # Write updated file
    print(f"\n💾 Writing updated file...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(listings)
    
    print(f"\n✅ COMPLETED!")
    print(f"📁 Output: {output_file}")
    print(f"📊 Total Seniorly listings: {len(seniorly_listings)}")
    print(f"✅ Successfully updated: {updated_count}")
    print(f"❌ Failed: {failed_count}")
    
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Seniorly community types and update CSV")
    parser.add_argument("--max", type=int, default=None, help="Process at most N Seniorly listings (for spot checks)")
    args = parser.parse_args()

    asyncio.run(update_seniorly_care_types(max_items=args.max))
