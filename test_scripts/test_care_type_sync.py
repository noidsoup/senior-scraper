#!/usr/bin/env python3
"""
Test care type synchronization for 50 listings before and after import
"""

import csv
import requests
import json
from datetime import datetime
import argparse

def get_listing_from_api_by_slug(listing_slug):
    """Get listing data from WordPress API by slug (may be ambiguous)."""
    api_url = f"https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/listing?slug={listing_slug}"
    
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]
        return None
    except Exception as e:
        print(f"  ❌ API Error for slug {listing_slug}: {e}")
        return None

def get_listing_from_api_by_id(listing_id):
    """Get listing data from WordPress API by numeric ID (unambiguous)."""
    try:
        api_url = f"https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/listing/{int(listing_id)}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"  ❌ API Error for ID {listing_id}: {e}")
        return None

def decode_wordpress_type(type_field):
    """Decode WordPress serialized type field to readable categories"""
    
    if type_field is None:
        return "Uncategorized"
    
    # WordPress term ID to CMS category mapping
    ID_TO_CATEGORY = {
        "1": "Uncategorized",
        "3": "Memory Care", 
        "5": "Assisted Living Community",
        "6": "Independent Living",
        "7": "Nursing Home",
        "99": "Assisted Living Home",  # Note: 99 might be different from 162
        "162": "Assisted Living Home",
        "488": "Home Care",
    }
    
    try:
        categories = []

        # Case 1: API returns serialized PHP array string
        if isinstance(type_field, str):
            if type_field.strip() == '':
                return "Uncategorized"
            import re
            id_matches = re.findall(r'i:\d+;i:(\d+);', type_field)
            for term_id in id_matches:
                if term_id in ID_TO_CATEGORY:
                    category = ID_TO_CATEGORY[term_id]
                    if category not in categories:
                        categories.append(category)
            return ', '.join(categories) if categories else "Uncategorized"

        # Case 2: API returns a list (common in WP REST for ACF taxonomy fields)
        if isinstance(type_field, list):
            for item in type_field:
                # Item could be an int, str id, or dict
                term_id = None
                term_name = None
                if isinstance(item, dict):
                    # try several common keys
                    for key in ("id", "term_id", "term", "value"):
                        if key in item and item[key] is not None:
                            term_id = str(item[key])
                            break
                    term_name = item.get("name") or item.get("label")
                else:
                    term_id = str(item)

                if term_id and term_id in ID_TO_CATEGORY:
                    mapped = ID_TO_CATEGORY[term_id]
                    if mapped not in categories:
                        categories.append(mapped)
                elif term_name:
                    # Fallback to name if provided
                    cleaned = term_name.strip()
                    if cleaned and cleaned not in categories:
                        categories.append(cleaned)

            return ', '.join(categories) if categories else "Uncategorized"

        # Unknown structure: best-effort stringify
        return "Uncategorized"
        
    except:
        return "Uncategorized"

def test_care_type_sync(input_csv: str, limit: int, filter_seniorly: bool, filter_seniorplace: bool):
    """Test care type synchronization for a sample of listings.

    Args:
        input_csv: Path to CSV to read expected normalized_types from.
        limit: Max number of listings to test.
        filter_seniorly: If True, only test rows whose website contains seniorly.com.
    """
    
    print("🔍 TESTING CARE TYPE SYNCHRONIZATION")
    print("=" * 50)
    
    # Read the import file to get expected care types
    import_file = input_csv
    
    test_listings = []
    with open(import_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if limit > 0 and count >= limit:
                break
            
            # Support both our generated CSV and older formats
            title = (row.get('Title') or row.get('title') or '').strip()
            post_id = (row.get('ID') or row.get('Id') or row.get('id') or '').strip()
            normalized_types = (row.get('normalized_types') or '').strip()
            senior_place_url = (row.get('seniorplace_url') or row.get('senior_place_url') or '').strip()
            website = (row.get('seniorly_url') or row.get('website') or '').strip()
            
            # Optional Seniorly filter
            if filter_seniorly and 'seniorly.com' not in website.lower():
                continue

            # Optional Senior Place filter
            if filter_seniorplace:
                site = website.lower()
                sp_url = (senior_place_url or '').lower()
                if ('seniorplace.com' not in site) and ('seniorplace.com' not in sp_url):
                    continue

            # Only test listings that have care types (not "N/A" or empty)
            if normalized_types and normalized_types not in ['N/A (not Senior Place)', '']:
                # Extract slug from title for API lookup
                slug = title.lower().replace(' ', '-').replace('&', 'and').replace("'", '').replace('"', '')
                slug = ''.join(c for c in slug if c.isalnum() or c == '-')
                
                test_listings.append({
                    'title': title,
                    'id': post_id,
                    'expected_types': normalized_types,
                    'slug': slug,
                    'senior_place_url': senior_place_url
                })
                count += 1
    
    print(f"📊 Testing {len(test_listings)} listings with care types...")
    print()
    
    # Test each listing
    results = []
    for i, listing in enumerate(test_listings, 1):
        print(f"🔍 {i:2d}. Testing: {listing['title'][:40]}...")
        
        # Get current state from API: prefer ID to avoid slug collisions
        current_data = None
        if listing.get('id'):
            current_data = get_listing_from_api_by_id(listing['id'])
        if current_data is None:
            current_data = get_listing_from_api_by_slug(listing['slug'])
        
        if current_data:
            # Extract current care types
            current_types = "Unknown"
            if 'acf' in current_data and 'type' in current_data['acf']:
                current_types = decode_wordpress_type(current_data['acf']['type'])
            
            # Compare expected vs current
            expected = listing['expected_types']
            current = current_types
            
            status = "✅ SYNCED" if expected == current else "❌ MISMATCH"
            
            results.append({
                'title': listing['title'],
                'expected': expected,
                'current': current,
                'status': status,
                'senior_place_url': listing['senior_place_url']
            })
            
            print(f"     Expected: {expected}")
            print(f"     Current:  {current}")
            print(f"     Status:   {status}")
            
        else:
            print(f"     ❌ Could not fetch from API")
            results.append({
                'title': listing['title'],
                'expected': listing['expected_types'],
                'current': "API_ERROR",
                'status': "❌ API_ERROR",
                'senior_place_url': listing['senior_place_url']
            })
        
        print()
    
    # Generate summary report
    print("📊 SYNCHRONIZATION SUMMARY")
    print("=" * 50)
    
    synced_count = sum(1 for r in results if r['status'] == "✅ SYNCED")
    mismatch_count = sum(1 for r in results if r['status'] == "❌ MISMATCH")
    error_count = sum(1 for r in results if r['status'] == "❌ API_ERROR")
    
    print(f"✅ SYNCED:     {synced_count:2d}")
    print(f"❌ MISMATCH:   {mismatch_count:2d}")
    print(f"❌ API_ERROR:  {error_count:2d}")
    print(f"📊 TOTAL:      {len(results):2d}")
    
    # Show mismatches
    if mismatch_count > 0:
        print(f"\n🔍 MISMATCHES FOUND:")
        for r in results:
            if r['status'] == "❌ MISMATCH":
                print(f"  • {r['title'][:40]}")
                print(f"    Expected: {r['expected']}")
                print(f"    Current:  {r['current']}")
                print()
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"organized_csvs/CARE_TYPE_SYNC_TEST_{timestamp}.csv"
    
    with open(results_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'expected', 'current', 'status', 'senior_place_url'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"💾 Detailed results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Before/After care type sync test against WP API")
    parser.add_argument("--input", default="organized_csvs/01_WORDPRESS_IMPORT_READY.csv", help="Input CSV path")
    parser.add_argument("--limit", type=int, default=50, help="Max listings to test (0 = all)")
    parser.add_argument("--seniorly-only", action="store_true", help="Filter to listings with website containing seniorly.com")
    parser.add_argument("--seniorplace-only", action="store_true", help="Filter to listings with Senior Place URLs")
    args = parser.parse_args()

    test_care_type_sync(args.input, args.limit, args.seniorly_only, args.seniorplace_only)
