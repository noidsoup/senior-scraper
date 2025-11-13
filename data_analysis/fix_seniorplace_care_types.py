#!/usr/bin/env python3
"""
Fix Senior Place care types by re-scraping and applying our mapping system
"""

import csv
import requests
import re
import asyncio
from playwright.async_api import async_playwright
from typing import Dict, List, Set, Optional, Tuple
import argparse
from collections import defaultdict

# Our existing Senior Place → CMS category mapping
TYPE_LABEL_MAP: Dict[str, str] = {
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

# CMS category → WordPress term ID mapping
CANONICAL_TO_ID: Dict[str, int] = {
    "Assisted Living Community": 5,
    "Assisted Living Home": 162,
    "Independent Living": 6,
    "Memory Care": 3,
    "Nursing Home": 7,
    "Home Care": 488,
    "Uncategorized": 1,  # Default for unmapped types
}

async def scrape_seniorplace_care_types(context, url: str) -> Tuple[str, List[str]]:
    """Scrape care types from a Senior Place URL using Playwright for dynamic content"""
    try:
        page = await context.new_page()
        await page.goto(url, timeout=30000)
        
        # Navigate to the attributes tab where Community Types is located
        if not url.endswith('/attributes'):
            if url.endswith('/'):
                await page.goto(url + 'attributes', timeout=30000)
            else:
                await page.goto(url + '/attributes', timeout=30000)
        
        # Wait for the Community Types section to load
        await page.wait_for_selector('text=Community Type', timeout=20000)
        
        # Use the same logic as the working scraper
        types = await page.evaluate(
            """
            () => {
              const out = [];
              // Find the section that contains 'Community Type(s)'
              const labels = Array.from(document.querySelectorAll('label.inline-flex'));
              for (const label of labels) {
                const textEl = label.querySelector('div.ml-2');
                const input = label.querySelector('input[type="checkbox"]');
                if (!textEl || !input) continue;
                if (!input.checked) continue;  // Only get CHECKED boxes
                const name = (textEl.textContent || '').trim();
                if (name) out.push(name);
              }
              return out;
            }
            """
        )
        
        await page.close()
        
        # Convert to lowercase for mapping
        care_types = [t.strip().lower() for t in (types or [])]
        return url, care_types
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        try:
            await page.close()
        except:
            pass
        return url, []

def map_care_types_to_cms(senior_place_types: List[str]) -> Tuple[List[str], List[str]]:
    """Map Senior Place care types to our CMS categories"""
    mapped_types = []
    unmapped_types = []
    
    for sp_type in senior_place_types:
        if sp_type in TYPE_LABEL_MAP:
            cms_type = TYPE_LABEL_MAP[sp_type]
            if cms_type not in mapped_types:  # Avoid duplicates
                mapped_types.append(cms_type)
        else:
            unmapped_types.append(sp_type)
    
    return mapped_types, unmapped_types

async def process_seniorplace_listings():
    """Main function to process Senior Place listings"""
    
    current_file = "/Users/nicholas/Repos/senior-scrapr/CURRENT Listings-Export-2025-August-27-1801.csv"
    output_file = "/Users/nicholas/Repos/senior-scrapr/nCORRECTED_Senior_Place_Care_Types.csv"
    unmapped_report = "/Users/nicholas/Repos/senior-scrapr/UNMAPPED_Senior_Place_Types.csv"
    
    # Senior Place credentials
    username = "allison@aplaceforseniors.org"
    password = "Hugomax2023!"
    login_url = "https://app.seniorplace.com/login"
    
    print("🔧 SENIOR PLACE CARE TYPE CORRECTION")
    print("=" * 50)
    
    # Extract Senior Place listings
    seniorplace_listings = []
    all_listings = []
    
    print("📥 Loading current listings...")
    with open(current_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            all_listings.append(row)
            website = row.get('website', '').strip()
            
            if 'seniorplace.com' in website.lower():
                seniorplace_listings.append(row)
    
    print(f"Found {len(seniorplace_listings):,} Senior Place listings out of {len(all_listings):,} total")
    
    # Process in batches to avoid overwhelming the server
    batch_size = 20  # Increased from 10 for speed
    results = {}
    unmapped_report_data = []
    failed_urls_log = []  # Track failed/unavailable listings
    
    print(f"🔄 Re-scraping care types from Senior Place URLs...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Login to Senior Place first
        print("🔐 Logging in to Senior Place...")
        page = await context.new_page()
        await page.goto(login_url)
        await page.fill('#email', username)
        await page.fill('#password', password)
        await page.click('#signin')
        await page.wait_for_selector('text=Communities', timeout=20000)
        await page.close()
        print("✅ Login successful!")
        
        for i in range(0, len(seniorplace_listings), batch_size):
            batch = seniorplace_listings[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(seniorplace_listings) + batch_size - 1)//batch_size}...")
            
            # Scrape care types for this batch
            tasks = []
            for listing in batch:
                url = listing.get('website', '').strip()
                if url:
                    tasks.append(scrape_seniorplace_care_types(context, url))
            
            batch_results = await asyncio.gather(*tasks)
            
            # Process results and log failures
            for url, care_types in batch_results:
                results[url] = care_types
                # Log failed URLs for analysis
                if not care_types:  # Empty list means scraping failed
                    failed_urls_log.append(url)
            
            # Small delay between batches
            await asyncio.sleep(1)  # Reduced from 2 seconds for speed
        
        await browser.close()
    
    print("🗂️  Mapping care types to CMS categories...")
    
    # Update listings with corrected care types
    updated_listings = []
    stats = {
        'total_processed': 0,
        'successfully_mapped': 0,
        'unmapped': 0,
        'no_types_found': 0
    }
    
    for row in all_listings:
        website = row.get('website', '').strip()
        
        if 'seniorplace.com' in website.lower():
            stats['total_processed'] += 1
            
            # Get scraped care types
            scraped_types = results.get(website, [])
            
            # Add scraped care types column for visibility
            row['scraped_care_types'] = ', '.join(scraped_types) if scraped_types else 'Uncategorized'
            
            # Extract and separate URLs for tracking
            row['senior_place_url'] = website if 'seniorplace.com' in website.lower() else ''
            row['seniorly_url'] = ''
            
            # Check all fields for Seniorly URLs (some listings might be on both platforms)
            for field_name, field_value in row.items():
                if field_value and isinstance(field_value, str) and field_name != 'website':
                    if 'seniorly.com' in field_value.lower():
                        row['seniorly_url'] = field_value.strip()
                        break
            
            if scraped_types:
                # Map to CMS categories
                mapped_types, unmapped_types = map_care_types_to_cms(scraped_types)
                
                if mapped_types:
                    # Successfully mapped
                    stats['successfully_mapped'] += 1
                    
                    # Get ALL mapped type IDs for WordPress serialized format
                    type_ids = [CANONICAL_TO_ID[t] for t in mapped_types if t in CANONICAL_TO_ID]
                    
                    if len(type_ids) == 1:
                        # Single type: a:1:{i:0;i:ID;}
                        row['type'] = f'a:1:{{i:0;i:{type_ids[0]};}}'
                    else:
                        # Multiple types: a:N:{i:0;i:ID1;i:1;i:ID2;...}
                        items = ''.join(f'i:{i};i:{type_ids[i]};' for i in range(len(type_ids)))
                        row['type'] = f'a:{len(type_ids)}:{{{items}}}'
                    
                elif unmapped_types:
                    # Has types but none mapped
                    stats['unmapped'] += 1
                    row['type'] = f'a:1:{{i:0;i:{CANONICAL_TO_ID["Uncategorized"]};}}'
                    
                    # Add to unmapped report
                    unmapped_report_data.append({
                        'Title': row.get('Title', ''),
                        'Website': website,
                        'Senior_Place_Types': ', '.join(scraped_types),
                        'Unmapped_Types': ', '.join(unmapped_types)
                    })
                    
                else:
                    # No types found after scraping
                    stats['no_types_found'] += 1
                    row['type'] = f'a:1:{{i:0;i:{CANONICAL_TO_ID["Uncategorized"]};}}'
            else:
                # Scraping failed or no types found
                stats['no_types_found'] += 1
                row['type'] = f'a:1:{{i:0;i:{CANONICAL_TO_ID["Uncategorized"]};}}'
        else:
            # Non-Senior Place listing, add N/A for scraped types column
            row['scraped_care_types'] = 'N/A (not Senior Place)'
            
            # Check if this is a Seniorly listing or has both URLs
            row['senior_place_url'] = ''
            row['seniorly_url'] = ''
            
            # Check all fields for Seniorly URLs
            for field_name, field_value in row.items():
                if field_value and isinstance(field_value, str):
                    if 'seniorly.com' in field_value.lower():
                        row['seniorly_url'] = field_value.strip()
                        break
        
        updated_listings.append(row)
    
    # Write corrected CSV
    print("💾 Writing corrected listings...")
    
    # Add new columns for tracking URLs and scraped care types
    output_headers = list(headers) + ['scraped_care_types', 'senior_place_url', 'seniorly_url']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_headers)
        writer.writeheader()
        writer.writerows(updated_listings)
    
    # Write unmapped types report
    if unmapped_report_data:
        print("📋 Writing unmapped types report...")
        with open(unmapped_report, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Title', 'Website', 'Senior_Place_Types', 'Unmapped_Types'])
            writer.writeheader()
            writer.writerows(unmapped_report_data)
    
    # Write failed URLs log
    if failed_urls_log:
        failed_log_file = "/Users/nicholas/Repos/senior-scrapr/FAILED_Senior_Place_URLs.txt"
        print(f"⚠️  Writing failed URLs log...")
        with open(failed_log_file, 'w', encoding='utf-8') as f:
            f.write(f"Senior Place URLs that failed to scrape ({len(failed_urls_log)} total)\n")
            f.write("=" * 60 + "\n\n")
            for url in failed_urls_log:
                f.write(f"{url}\n")
            f.write(f"\nReasons for failure could be:\n")
            f.write(f"- Listing no longer exists\n")
            f.write(f"- Page structure changed\n") 
            f.write(f"- Network timeouts\n")
            f.write(f"- Access permissions changed\n")
    
    # Print summary
    print("\n📊 CORRECTION SUMMARY")
    print("=" * 30)
    print(f"Total Senior Place listings: {stats['total_processed']:,}")
    print(f"Successfully mapped: {stats['successfully_mapped']:,}")
    print(f"Set to Uncategorized: {stats['unmapped'] + stats['no_types_found']:,}")
    print(f"  - Unmapped types: {stats['unmapped']:,}")
    print(f"  - No types found: {stats['no_types_found']:,}")
    print()
    print(f"✅ Output file: {output_file}")
    if unmapped_report_data:
        print(f"⚠️  Unmapped report: {unmapped_report}")
        print(f"   ({len(unmapped_report_data)} listings need review)")
    if failed_urls_log:
        print(f"❌ Failed URLs log: FAILED_Senior_Place_URLs.txt")
        print(f"   ({len(failed_urls_log)} URLs failed to scrape)")
    
    return stats

if __name__ == "__main__":
    asyncio.run(process_seniorplace_listings())
