#!/usr/bin/env python3
"""
Comprehensive scraper to check ALL Senior Place listings from latest WordPress export.
Uses exact HTML structure provided by user to get community types accurately.
"""

import csv
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import argparse
import re

# Canonical mapping from memory.md
CANONICAL_MAPPING = {
    'assisted living facility': 'Assisted Living Community',
    'assisted living home': 'Assisted Living Home', 
    'independent living': 'Independent Living',
    'memory care': 'Memory Care',
    'skilled nursing': 'Nursing Home',
    'continuing care retirement community': 'Assisted Living Community',
    'in-home care': 'Home Care',
    'home health': 'Home Care',
    'hospice': 'Home Care',
    'respite care': 'Assisted Living Community',
}

CANONICAL_TO_ID = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}

def generate_wp_type_field(canonical_types):
    """Generate WordPress serialized type field for multiple types"""
    if not canonical_types:
        return 'a:1:{i:0;i:1;}'  # Uncategorized
    
    type_ids = [CANONICAL_TO_ID[t] for t in canonical_types if t in CANONICAL_TO_ID]
    
    if len(type_ids) == 1:
        return f'a:1:{{i:0;i:{type_ids[0]};}}'
    else:
        # Multiple types: a:N:{i:0;i:ID1;i:1;i:ID2;...}
        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
        return f'a:{len(type_ids)}:{{{items}}}'

def decode_current_wp_type(type_field):
    """Decode current WordPress type field to human readable"""
    if not type_field or type_field == '0':
        return 'Other/Unknown'
    
    # Extract all type IDs from serialized format
    type_ids = re.findall(r'i:\d+;i:(\d+);', type_field)
    type_names = []
    
    for type_id in type_ids:
        for name, id_val in CANONICAL_TO_ID.items():
            if str(id_val) == type_id:
                type_names.append(name)
                break
    
    return ', '.join(type_names) if type_names else 'Other/Unknown'

async def scrape_community_types_from_attributes(context, url, title):
    """Scrape community types from Senior Place attributes page using exact HTML structure"""
    try:
        page = await context.new_page()
        
        # Navigate to attributes page
        attributes_url = f"{url.rstrip('/')}/attributes"
        await page.goto(attributes_url, wait_until="networkidle", timeout=20000)
        
        # Wait for the specific Community Type section
        await page.wait_for_selector('div:has-text("Community Type(s)")', timeout=10000)
        
        # Extract community types using the exact HTML structure provided
        community_types = await page.evaluate("""
            () => {
                const communityTypes = [];
                
                // Find the Community Type(s) section specifically  
                const communityTypeDiv = Array.from(document.querySelectorAll('div')).find(div => 
                    div.textContent && div.textContent.trim() === 'Community Type(s)' && 
                    div.classList.contains('font-bold')
                );
                
                if (!communityTypeDiv) {
                    return [];
                }
                
                // Get the options container that follows the Community Type(s) header
                let optionsContainer = communityTypeDiv.parentElement.querySelector('.options');
                
                if (!optionsContainer) {
                    return [];
                }
                
                // Get all checked checkboxes in this specific section
                const checkedInputs = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
                
                for (const input of checkedInputs) {
                    // Find the label text next to this checkbox
                    const labelDiv = input.parentElement.querySelector('div.ml-2');
                    if (labelDiv && labelDiv.textContent) {
                        const typeText = labelDiv.textContent.trim();
                        if (typeText) {
                            communityTypes.push(typeText);
                        }
                    }
                }
                
                return communityTypes;
            }
        """)
        
        await page.close()
        
        if community_types and len(community_types) > 0:
            print(f"  ✅ Found community types: {community_types}")
            return community_types
        else:
            print(f"  ⚠️  No community types found")
            return []
            
    except Exception as e:
        print(f"  ❌ Error scraping {url}: {str(e)}")
        if 'page' in locals():
            await page.close()
        return []

def extract_senior_place_url(row):
    """Extract Senior Place URL from various possible fields"""
    
    # Check website field first
    website = row.get('website', '') or row.get('_website', '')
    if website and 'seniorplace.com' in website:
        return website
    
    # Check senior_place_url field
    sp_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
    if sp_url and 'seniorplace.com' in sp_url:
        return sp_url
    
    return None

async def process_all_senior_place_listings(username, password, limit=None):
    """Process all Senior Place listings from latest WordPress export"""
    
    print("🏘️  COMPREHENSIVE SENIOR PLACE TYPE CHECKER")
    print("=" * 60)
    print("Checking ALL Senior Place listings from latest WordPress export")
    print("Getting current community types and comparing to WordPress data")
    print()
    
    # Read latest WordPress export
    all_listings = []
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '').strip('"')
            sp_url = extract_senior_place_url(row)
            
            if sp_url:
                all_listings.append({
                    'wp_id': row.get('ID', ''),
                    'title': title,
                    'url': sp_url,
                    'current_wp_type': decode_current_wp_type(row.get('type', '')),
                    'current_type_field': row.get('type', ''),
                    'website': row.get('website', ''),
                    'senior_place_url': row.get('senior_place_url', ''),
                })
    
    if limit:
        all_listings = all_listings[:limit]
    
    print(f"📊 Found {len(all_listings)} Senior Place listings to check")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login to Senior Place
        print("🔐 Logging into Senior Place...")
        page = await context.new_page()
        await page.goto("https://app.seniorplace.com/login")
        await page.fill('input[name="email"]', username)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_selector('text=Communities', timeout=15000)
        await page.close()
        print("✅ Successfully logged in")
        print()
        
        # Process all listings
        corrections_needed = []
        all_results = []
        successful_scrapes = 0
        failed_scrapes = 0
        
        for i, listing in enumerate(all_listings):
            print(f"📋 {i+1}/{len(all_listings)}: {listing['title']}")
            print(f"    Current WP: {listing['current_wp_type']}")
            
            # Scrape current community types from Senior Place
            community_types = await scrape_community_types_from_attributes(context, listing['url'], listing['title'])
            
            if community_types:
                successful_scrapes += 1
                
                # Map to canonical types (ALL types, following memory rules)
                canonical_types = []
                for sp_type in community_types:
                    sp_lower = sp_type.lower()
                    if sp_lower in CANONICAL_MAPPING:
                        canonical = CANONICAL_MAPPING[sp_lower]
                        if canonical not in canonical_types:
                            canonical_types.append(canonical)
                
                if canonical_types:
                    # Generate correct WordPress type field
                    correct_type_field = generate_wp_type_field(canonical_types)
                    should_be_types = ', '.join(canonical_types)
                    
                    # Check if this differs from current WordPress data
                    if listing['current_type_field'] != correct_type_field:
                        print(f"    🚨 MISMATCH! Should be: {should_be_types}")
                        
                        corrections_needed.append({
                            'ID': listing['wp_id'],
                            'Title': listing['title'],
                            'type': correct_type_field,
                            'normalized_types': should_be_types,
                            'senior_place_types': ', '.join(community_types),
                            'current_wp_types': listing['current_wp_type'],
                            'correction_reason': f'SP shows: {", ".join(community_types)} → Should map to: {should_be_types}'
                        })
                    else:
                        print(f"    ✅ Correct: {should_be_types}")
                
                all_results.append({
                    'wp_id': listing['wp_id'],
                    'title': listing['title'],
                    'community_types': community_types,
                    'canonical_types': canonical_types,
                    'current_wp_type': listing['current_wp_type'],
                    'status': 'match' if listing['current_type_field'] == correct_type_field else 'mismatch'
                })
            else:
                failed_scrapes += 1
                print(f"    ❌ Failed to get community types")
                
                all_results.append({
                    'wp_id': listing['wp_id'],
                    'title': listing['title'],
                    'community_types': [],
                    'canonical_types': [],
                    'current_wp_type': listing['current_wp_type'],
                    'status': 'failed'
                })
            
            print()
            
            # Small delay to be respectful
            await asyncio.sleep(0.5)
        
        await browser.close()
        
        # Results summary
        print(f"\n🎯 FINAL RESULTS:")
        print(f"  Total processed: {len(all_listings)}")
        print(f"  Successful scrapes: {successful_scrapes}")
        print(f"  Failed scrapes: {failed_scrapes}")
        print(f"  Corrections needed: {len(corrections_needed)}")
        print()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save corrections needed (the important file!)
        if corrections_needed:
            corrections_file = f"organized_csvs/SENIOR_PLACE_TYPE_CORRECTIONS_{timestamp}.csv"
            with open(corrections_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=corrections_needed[0].keys())
                writer.writeheader()
                writer.writerows(corrections_needed)
            
            print(f"💾 CORRECTIONS FILE: {corrections_file}")
            print(f"   → Import this to WordPress using ID matching!")
            print()
            
            print(f"📋 SAMPLE CORRECTIONS:")
            for i, corr in enumerate(corrections_needed[:5]):
                print(f"  {i+1}. {corr['Title']}")
                print(f"     Senior Place: {corr['senior_place_types']}")
                print(f"     Should be: {corr['normalized_types']}")
                print(f"     Currently: {corr['current_wp_types']}")
                print()
            
            if len(corrections_needed) > 5:
                print(f"   ... and {len(corrections_needed) - 5} more corrections")
                print()
        else:
            print(f"✅ NO CORRECTIONS NEEDED! All {successful_scrapes} listings are correctly mapped.")
        
        # Save full results for analysis
        if all_results:
            all_data_file = f"organized_csvs/ALL_SENIOR_PLACE_ANALYSIS_{timestamp}.csv"
            with open(all_data_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['wp_id', 'title', 'community_types', 'canonical_types', 'current_wp_type', 'status']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for result in all_results:
                    output_row = {
                        'wp_id': result['wp_id'],
                        'title': result['title'],
                        'community_types': ', '.join(result['community_types']) if result['community_types'] else '',
                        'canonical_types': ', '.join(result['canonical_types']) if result['canonical_types'] else '',
                        'current_wp_type': result['current_wp_type'],
                        'status': result['status']
                    }
                    writer.writerow(output_row)
            
            print(f"💾 Full analysis: {all_data_file}")

def main():
    parser = argparse.ArgumentParser(description="Check all Senior Place community types against WordPress")
    parser.add_argument('--username', default='allison@aplaceforseniors.org', help='Senior Place username')
    parser.add_argument('--password', default='Hugomax2023!', help='Senior Place password')
    parser.add_argument('--limit', type=int, help='Limit for testing (default: all)')
    
    args = parser.parse_args()
    
    print("🚀 Starting comprehensive Senior Place type checking...")
    print("This will find ALL listings that need care type corrections")
    print()
    
    asyncio.run(process_all_senior_place_listings(args.username, args.password, args.limit))

if __name__ == "__main__":
    main()
