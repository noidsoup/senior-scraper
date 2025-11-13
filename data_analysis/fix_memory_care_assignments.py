#!/usr/bin/env python3
"""
Simple fix: Find Senior Place listings with Memory Care, match by URL to current WP export,
and create update CSV for missing Memory Care assignments.
"""

import csv
import re

def normalize_url(url):
    """Normalize URL for matching"""
    if not url:
        return ""
    # Remove protocol, trailing slashes, query params
    url = re.sub(r'^https?://', '', url.strip())
    url = re.sub(r'[/?#].*$', '', url)
    return url.lower()

def main():
    seniorplace_file = "organized_csvs/seniorplace_data_export.csv"
    current_wp_file = "organized_csvs/Listings-Export-2025-August-28-1956.csv"
    output_file = "organized_csvs/MEMORY_CARE_UPDATES.csv"
    
    print("🧠 Finding Memory Care assignments...")
    
    # Step 1: Find Senior Place listings with Memory Care
    memory_care_urls = {}
    
    with open(seniorplace_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get('title', '').strip()
            care_type = row.get('type', '').strip()
            url = row.get('url', '').strip()
            
            if 'memory care' in care_type.lower() and url and 'seniorplace.com' in url:
                norm_url = normalize_url(url)
                memory_care_urls[norm_url] = {
                    'title': title,
                    'type': care_type,
                    'url': url
                }
                print(f"  SP Memory Care: {title} -> {norm_url}")
    
    print(f"Found {len(memory_care_urls)} Senior Place listings with Memory Care")
    
    # Step 2: Match against current WP export
    updates_needed = []
    
    with open(current_wp_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            wp_id = row.get('ID', '').strip()
            wp_title = row.get('Title', '').strip()
            website = row.get('website', '').strip()
            senior_place_url = row.get('senior_place_url', '').strip()
            current_type = row.get('type', '').strip()
            
            # Check both website and senior_place_url fields
            urls_to_check = [website, senior_place_url]
            
            for check_url in urls_to_check:
                if not check_url:
                    continue
                    
                norm_check = normalize_url(check_url)
                
                if norm_check in memory_care_urls:
                    sp_data = memory_care_urls[norm_check]
                    
                    # Check if already has Memory Care in type field
                    if 'memory care' not in current_type.lower():
                        updates_needed.append({
                            'ID': wp_id,
                            'Title': wp_title,
                            'current_type': current_type,
                            'website': website,
                            'senior_place_url': senior_place_url,
                            'matched_url': check_url,
                            'sp_title': sp_data['title'],
                            'sp_type': sp_data['type'],
                            'action': 'add_memory_care'
                        })
                        print(f"  📌 ID {wp_id}: {wp_title} needs Memory Care")
                    break
    
    print(f"Found {len(updates_needed)} listings that need Memory Care added")
    
    # Step 3: Write update CSV
    if updates_needed:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['ID', 'Title', 'current_type', 'website', 'senior_place_url', 
                         'matched_url', 'sp_title', 'sp_type', 'action']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updates_needed)
        
        print(f"✅ Wrote updates to: {output_file}")
        
        # Sample of what needs updating
        print("\n📋 Sample updates needed:")
        for i, update in enumerate(updates_needed[:5]):
            print(f"  {i+1}. ID {update['ID']}: {update['Title']}")
            print(f"     Current: {update['current_type']}")
            print(f"     Senior Place: {update['sp_type']}")
            print()
    else:
        print("✅ No Memory Care updates needed - all listings already assigned correctly")

if __name__ == "__main__":
    main()
