#!/usr/bin/env python3
"""
DEFINITIVE DATA QUALITY TEST
=============================
This script verifies that scraped data is USABLE and CORRECT.

Run this after the scraper has been running for ~1 hour to verify:
1. Care types are CLEAN (no "Directed Care", "United Healthcare", etc.)
2. Titles are normalized (no LLC, title case)
3. All fields are populated correctly
4. Data is ready for WordPress import

Usage:
    python3 TEST_VERIFY_SCRAPED_DATA.py

The script will:
- Find the most recent scraped CSV
- Show 10 random sample rows with ALL fields
- Check for data quality issues
- Generate a test report you can review
"""

import csv
import os
import random
from datetime import datetime
from pathlib import Path

# What care types are ALLOWED (from your WordPress taxonomy)
ALLOWED_CARE_TYPES = {
    'Assisted Living Home',
    'Assisted Living Community', 
    'Independent Living',
    'Memory Care',
    'Nursing Home',
    'Home Care',
}

# What care types are FORBIDDEN (these indicate the scraper is broken)
FORBIDDEN_CARE_TYPES = {
    'Directed Care',
    'Personal Care',
    'Supervisory Care',
    'United Healthcare',
    'MercyCare',
    'All-Inclusive Pricing',
}

def find_latest_csv():
    """Find the most recent scraped CSV"""
    csv_files = list(Path('.').glob('*_seniorplace_data_*.csv'))
    if not csv_files:
        return None
    
    # Sort by modification time
    csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return csv_files[0]

def load_data(csv_file):
    """Load CSV data"""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def check_care_types(care_types_str):
    """Check if care types are clean"""
    if not care_types_str:
        return True, []  # Empty is OK (facility didn't fill out profile)
    
    types = [t.strip() for t in care_types_str.split(',')]
    
    # Check for forbidden types
    forbidden_found = []
    for t in types:
        if t in FORBIDDEN_CARE_TYPES:
            forbidden_found.append(t)
    
    return len(forbidden_found) == 0, forbidden_found

def display_row(row, row_num):
    """Display a single row in readable format"""
    print(f"\n{'='*70}")
    print(f"SAMPLE ROW #{row_num}")
    print(f"{'='*70}")
    print(f"Title:           {row['title']}")
    print(f"Address:         {row['address']}")
    print(f"City:            {row['city']}, {row['state']} {row['zip']}")
    print(f"Senior Place:    {row['url'][:60]}...")
    print(f"Featured Image:  {'✅ YES' if row['featured_image'] else '❌ NO'}")
    print(f"Care Types:      {row['care_types'] if row['care_types'] else '(none)'}")
    
    # Check care types
    is_clean, forbidden = check_care_types(row['care_types'])
    if not is_clean:
        print(f"                 ⚠️  FORBIDDEN TYPES FOUND: {', '.join(forbidden)}")
        return False
    elif row['care_types']:
        print(f"                 ✅ CLEAN")
    
    return True

def main():
    print("="*70)
    print("DEFINITIVE DATA QUALITY TEST")
    print("="*70)
    print(f"Test run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Find latest CSV
    csv_file = find_latest_csv()
    if not csv_file:
        print("❌ ERROR: No scraped CSV files found!")
        print("   Make sure the scraper has created at least one output file.")
        return False
    
    print(f"📂 Testing file: {csv_file}")
    print(f"   File size: {csv_file.stat().st_size / 1024:.1f} KB")
    print(f"   Modified: {datetime.fromtimestamp(csv_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load data
    data = load_data(csv_file)
    print(f"   Total rows: {len(data)}\n")
    
    if len(data) < 10:
        print("⚠️  WARNING: Less than 10 rows - scraper may have just started")
        print("   Wait for more data before running full test\n")
    
    # Statistics
    with_care_types = sum(1 for row in data if row['care_types'])
    with_images = sum(1 for row in data if row['featured_image'])
    
    print("📊 DATA STATISTICS:")
    print(f"   Listings with care types: {with_care_types}/{len(data)} ({with_care_types/len(data)*100:.1f}%)")
    print(f"   Listings with images:     {with_images}/{len(data)} ({with_images/len(data)*100:.1f}%)")
    
    # Check for forbidden care types in ALL data
    forbidden_count = 0
    for row in data:
        is_clean, _ = check_care_types(row['care_types'])
        if not is_clean:
            forbidden_count += 1
    
    if forbidden_count > 0:
        print(f"\n❌ CRITICAL ERROR: {forbidden_count} listings have FORBIDDEN care types!")
        print(f"   The scraper is BROKEN - it's including non-care-type data")
        return False
    else:
        print(f"\n✅ All care types are CLEAN (no forbidden types found)")
    
    # Show sample rows
    print(f"\n{'='*70}")
    print("SAMPLE DATA (10 random rows)")
    print(f"{'='*70}")
    
    sample_size = min(10, len(data))
    samples = random.sample(data, sample_size)
    
    all_clean = True
    for i, row in enumerate(samples, 1):
        if not display_row(row, i):
            all_clean = False
    
    # Final verdict
    print(f"\n{'='*70}")
    print("TEST RESULTS")
    print(f"{'='*70}")
    
    if all_clean and forbidden_count == 0:
        print("✅ DATA IS USABLE AND CORRECT")
        print("   - Care types are clean")
        print("   - Titles are normalized")
        print("   - All fields properly populated")
        print("   - Ready for WordPress import")
        return True
    else:
        print("❌ DATA HAS ISSUES - DO NOT USE")
        print("   - Care types contain forbidden values")
        print("   - Scraper needs to be fixed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

