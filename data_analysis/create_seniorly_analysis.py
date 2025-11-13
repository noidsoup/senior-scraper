#!/usr/bin/env python3
"""
Create comprehensive analysis of Seniorly listings needing home vs community classification.
"""

import pandas as pd
import sys
from urllib.parse import urlparse

def main():
    csv_file = "/Users/nicholas/Repos/senior-scrapr/Listings-Export-2025-August-29-1902.csv"
    
    print("🔍 SENIORLY LISTINGS ANALYSIS")
    print("=" * 50)
    
    # Load data
    df = pd.read_csv(csv_file)
    print(f"📊 Total listings in export: {len(df)}")
    
    # Find Seniorly listings
    seniorly_mask = (
        df['website'].str.contains('seniorly.com', na=False, case=False) |
        df['seniorly_url'].str.contains('seniorly.com', na=False, case=False)
    )
    
    seniorly_df = df[seniorly_mask].copy()
    print(f"🎯 Seniorly listings found: {len(seniorly_df)}")
    
    # Consolidate Seniorly URLs
    seniorly_df['seniorly_url_final'] = seniorly_df.apply(
        lambda row: (
            row['website'] if pd.notna(row['website']) and 'seniorly.com' in str(row['website']) 
            else row['seniorly_url'] if pd.notna(row['seniorly_url']) and 'seniorly.com' in str(row['seniorly_url'])
            else ''
        ), axis=1
    )
    
    # Analyze current types (the serialized PHP arrays)
    print(f"\n🏷️  CURRENT TYPE CLASSIFICATIONS:")
    type_analysis = seniorly_df['type'].value_counts()
    for type_val, count in type_analysis.head(5).items():
        # Try to decode the PHP serialized array
        if 'i:162' in str(type_val):
            print(f"  Assisted Living Home (ID 162): {count}")
        elif 'i:5' in str(type_val):
            print(f"  Assisted Living Community (ID 5): {count}")
        elif 'i:3' in str(type_val):
            print(f"  Memory Care (ID 3): {count}")
        else:
            print(f"  Other/Unknown: {count}")
    
    # Geographic distribution
    print(f"\n🗺️  GEOGRAPHIC DISTRIBUTION:")
    state_counts = seniorly_df['States'].value_counts()
    for state, count in state_counts.items():
        print(f"  {state}: {count}")
    
    # Check for Senior Place overlap
    has_sp_url = seniorly_df['senior_place_url'].notna() & (seniorly_df['senior_place_url'] != '')
    print(f"\n🔗 SENIOR PLACE OVERLAP:")
    print(f"  Also have Senior Place URLs: {has_sp_url.sum()}")
    print(f"  Seniorly-only listings: {len(seniorly_df) - has_sp_url.sum()}")
    
    # Export for scraping
    columns_for_scraping = [
        'ID', 'Title', 'seniorly_url_final', 'type', 'States', 'Locations', 
        'address', 'price', 'senior_place_url'
    ]
    
    scraping_df = seniorly_df[columns_for_scraping].copy()
    scraping_df = scraping_df[scraping_df['seniorly_url_final'] != '']  # Only ones with valid URLs
    
    output_file = 'seniorly_listings_for_scraping.csv'
    scraping_df.to_csv(output_file, index=False)
    
    print(f"\n💾 EXPORT COMPLETE:")
    print(f"  File: {output_file}")
    print(f"  Records: {len(scraping_df)}")
    print(f"  Ready for scraping to improve home vs community classification")
    
    # Show sample URLs for testing
    print(f"\n🔍 SAMPLE URLs FOR TESTING:")
    for i, row in scraping_df.head(5).iterrows():
        print(f"  {row['Title'][:40]:<40} | {row['seniorly_url_final']}")

if __name__ == "__main__":
    main()
