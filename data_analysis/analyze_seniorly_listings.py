#!/usr/bin/env python3
"""
Analyze Seniorly listings and attempt to match them with Senior Place listings
for category syncing. Match by title similarity and address.
"""

import csv
import re
from difflib import SequenceMatcher
from datetime import datetime

def clean_title_for_matching(title):
    """Clean title for better matching"""
    if not title:
        return ""
    
    # Convert to lowercase
    title = title.lower().strip()
    
    # Remove common suffixes/prefixes that might differ
    removals = [
        'assisted living', 'memory care', 'senior living', 'senior care',
        'retirement community', 'care center', 'care home', 'nursing home',
        'the ', ' the', 'at ', ' at', 'of ', ' of', 'in ', ' in',
        'llc', 'inc', 'ltd', 'corp', '&', 'and'
    ]
    
    for removal in removals:
        title = title.replace(removal, ' ')
    
    # Clean up extra spaces and punctuation
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    
    return title.strip()

def clean_address_for_matching(address):
    """Clean address for better matching"""
    if not address:
        return ""
    
    # Convert to lowercase and remove common variations
    address = address.lower().strip()
    
    # Remove common address variations
    replacements = {
        'street': 'st', 'avenue': 'ave', 'boulevard': 'blvd', 
        'drive': 'dr', 'road': 'rd', 'lane': 'ln', 'court': 'ct',
        'circle': 'cir', 'place': 'pl', 'way': 'wy'
    }
    
    for full, abbrev in replacements.items():
        address = address.replace(full, abbrev)
    
    # Extract just the street number and name (ignore city/state/zip)
    # Look for pattern like "123 Main St"
    match = re.search(r'(\d+\s+[^,]+)', address)
    if match:
        return match.group(1).strip()
    
    return address.split(',')[0].strip()

def calculate_similarity(str1, str2):
    """Calculate similarity between two strings"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1, str2).ratio()

def extract_seniorly_url(row):
    """Extract Seniorly URL from various possible fields"""
    
    # Check website field
    website = row.get('website', '') or row.get('_website', '')
    if website and 'seniorly.com' in website:
        return website
    
    # Check seniorly_url field if it exists
    seniorly_url = row.get('seniorly_url', '') or row.get('_seniorly_url', '')
    if seniorly_url and 'seniorly.com' in seniorly_url:
        return seniorly_url
    
    return None

def extract_senior_place_url(row):
    """Extract Senior Place URL from various possible fields"""
    
    # Check website field
    website = row.get('website', '') or row.get('_website', '')
    if website and 'seniorplace.com' in website:
        return website
    
    # Check senior_place_url field
    sp_url = row.get('senior_place_url', '') or row.get('_senior_place_url', '')
    if sp_url and 'seniorplace.com' in sp_url:
        return sp_url
    
    return None

def analyze_seniorly_listings():
    """Analyze all Seniorly listings and attempt to match with Senior Place"""
    
    print("🔍 ANALYZING SENIORLY LISTINGS FOR SENIOR PLACE MATCHING")
    print("=" * 65)
    print("Finding all Seniorly listings and attempting to match with Senior Place")
    print()
    
    # Read all WordPress listings
    all_listings = []
    seniorly_listings = []
    senior_place_listings = []
    
    with open('Listings-Export-2025-August-29-1902.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            title = row.get('Title', '').strip('"')
            address = row.get('address', '') or row.get('_address', '')
            
            seniorly_url = extract_seniorly_url(row)
            senior_place_url = extract_senior_place_url(row)
            
            listing_data = {
                'wp_id': row.get('ID', ''),
                'title': title,
                'address': address,
                'website': row.get('website', ''),
                'senior_place_url_field': row.get('senior_place_url', ''),
                'seniorly_url': seniorly_url,
                'senior_place_url': senior_place_url,
                'current_type': row.get('type', ''),
                'city': row.get('location', '') or row.get('_location', ''),
                'state': row.get('state', '') or row.get('_state', '')
            }
            
            all_listings.append(listing_data)
            
            if seniorly_url:
                seniorly_listings.append(listing_data)
            
            if senior_place_url:
                senior_place_listings.append(listing_data)
    
    print(f"📊 ANALYSIS RESULTS:")
    print(f"  Total listings: {len(all_listings)}")
    print(f"  Seniorly listings: {len(seniorly_listings)}")
    print(f"  Senior Place listings: {len(senior_place_listings)}")
    print()
    
    # Attempt to match Seniorly listings with Senior Place listings
    matches = []
    unmatched_seniorly = []
    
    print("🔗 ATTEMPTING TO MATCH SENIORLY → SENIOR PLACE:")
    print()
    
    for i, seniorly in enumerate(seniorly_listings):
        print(f"📋 {i+1}/{len(seniorly_listings)}: {seniorly['title']}")
        print(f"    Address: {seniorly['address']}")
        print(f"    City/State: {seniorly['city']}, {seniorly['state']}")
        
        best_match = None
        best_score = 0.0
        
        # Clean seniorly data for matching
        seniorly_clean_title = clean_title_for_matching(seniorly['title'])
        seniorly_clean_address = clean_address_for_matching(seniorly['address'])
        
        # Try to match with Senior Place listings
        for sp in senior_place_listings:
            # Clean senior place data
            sp_clean_title = clean_title_for_matching(sp['title'])
            sp_clean_address = clean_address_for_matching(sp['address'])
            
            # Calculate title similarity
            title_similarity = calculate_similarity(seniorly_clean_title, sp_clean_title)
            
            # Calculate address similarity
            address_similarity = calculate_similarity(seniorly_clean_address, sp_clean_address)
            
            # Combined score (weighted toward title)
            combined_score = (title_similarity * 0.7) + (address_similarity * 0.3)
            
            # Also check if they're in the same city/state
            city_match = seniorly['city'].lower() == sp['city'].lower() if seniorly['city'] and sp['city'] else False
            state_match = seniorly['state'].lower() == sp['state'].lower() if seniorly['state'] and sp['state'] else False
            
            # Boost score if location matches
            if city_match and state_match:
                combined_score += 0.1
            elif city_match or state_match:
                combined_score += 0.05
            
            if combined_score > best_score and combined_score > 0.6:  # Minimum threshold
                best_score = combined_score
                best_match = sp
        
        if best_match:
            print(f"    ✅ MATCH FOUND! Score: {best_score:.2f}")
            print(f"       → {best_match['title']}")
            print(f"       → {best_match['address']}")
            print(f"       → {best_match['senior_place_url']}")
            
            matches.append({
                'seniorly_wp_id': seniorly['wp_id'],
                'seniorly_title': seniorly['title'],
                'seniorly_address': seniorly['address'],
                'seniorly_url': seniorly['seniorly_url'],
                'senior_place_wp_id': best_match['wp_id'],
                'senior_place_title': best_match['title'],
                'senior_place_address': best_match['address'],
                'senior_place_url': best_match['senior_place_url'],
                'match_score': best_score,
                'city': seniorly['city'],
                'state': seniorly['state']
            })
        else:
            print(f"    ❌ No match found")
            unmatched_seniorly.append(seniorly)
        
        print()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n🎯 MATCHING RESULTS:")
    print(f"  Seniorly listings: {len(seniorly_listings)}")
    print(f"  Successful matches: {len(matches)}")
    print(f"  Unmatched Seniorly: {len(unmatched_seniorly)}")
    print(f"  Match rate: {len(matches)/len(seniorly_listings)*100:.1f}%")
    print()
    
    # Save matches
    if matches:
        matches_file = f"organized_csvs/SENIORLY_TO_SENIORPLACE_MATCHES_{timestamp}.csv"
        with open(matches_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=matches[0].keys())
            writer.writeheader()
            writer.writerows(matches)
        
        print(f"💾 MATCHES SAVED: {matches_file}")
        
        print(f"\n📋 SAMPLE MATCHES:")
        for i, match in enumerate(matches[:5]):
            print(f"  {i+1}. {match['seniorly_title']}")
            print(f"     → {match['senior_place_title']}")
            print(f"     Score: {match['match_score']:.2f}")
            print(f"     SP URL: {match['senior_place_url']}")
            print()
    
    # Save unmatched for manual review
    if unmatched_seniorly:
        unmatched_file = f"organized_csvs/UNMATCHED_SENIORLY_LISTINGS_{timestamp}.csv"
        with open(unmatched_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['wp_id', 'title', 'address', 'city', 'state', 'seniorly_url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for listing in unmatched_seniorly:
                writer.writerow({
                    'wp_id': listing['wp_id'],
                    'title': listing['title'],
                    'address': listing['address'],
                    'city': listing['city'],
                    'state': listing['state'],
                    'seniorly_url': listing['seniorly_url']
                })
        
        print(f"💾 UNMATCHED SAVED: {unmatched_file}")
        
        print(f"\n📋 SAMPLE UNMATCHED:")
        for i, unmatched in enumerate(unmatched_seniorly[:5]):
            print(f"  {i+1}. {unmatched['title']}")
            print(f"     Address: {unmatched['address']}")
            print(f"     City: {unmatched['city']}, {unmatched['state']}")
            print()
    
    print(f"\n🚀 NEXT STEPS:")
    print(f"1. Review the matches file to verify accuracy")
    print(f"2. For matched listings, we can scrape Senior Place community types")
    print(f"3. Update Seniorly listings with the correct Senior Place categories")
    print(f"4. Review unmatched listings for manual matching if needed")

def main():
    print("🚀 Starting Seniorly → Senior Place matching analysis...")
    print()
    
    analyze_seniorly_listings()

if __name__ == "__main__":
    main()
