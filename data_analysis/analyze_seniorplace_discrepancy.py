#!/usr/bin/env python3
"""
Analyze Senior Place listing discrepancies to understand the issue
"""

import csv
from collections import defaultdict

def analyze_discrepancy():
    """Analyze the current care type discrepancies with Senior Place data"""
    
    current_file = "/Users/nicholas/Repos/senior-scrapr/CURRENT Listings-Export-2025-August-27-1801.csv"
    
    print("🔍 SENIOR PLACE CARE TYPE DISCREPANCY ANALYSIS")
    print("=" * 60)
    
    # Count Senior Place listings and their current type assignments
    seniorplace_stats = {
        'total': 0,
        'multiple_types': 0,
        'single_type': 0,
        'no_types': 0,
        'type_combinations': defaultdict(int),
        'examples': []
    }
    
    with open(current_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            website = row.get('website', '').strip()
            
            # Only analyze Senior Place listings
            if 'seniorplace.com' in website.lower():
                seniorplace_stats['total'] += 1
                
                title = row.get('Title', '').strip()
                normalized_types = row.get('normalized_types', '').strip()
                
                if normalized_types:
                    types = [t.strip() for t in normalized_types.split(',')]
                    type_count = len(types)
                    
                    if type_count > 1:
                        seniorplace_stats['multiple_types'] += 1
                        # Track combinations causing issues
                        combination = ', '.join(sorted(types))
                        seniorplace_stats['type_combinations'][combination] += 1
                        
                        # Collect examples
                        if len(seniorplace_stats['examples']) < 10:
                            seniorplace_stats['examples'].append({
                                'title': title,
                                'types': combination,
                                'url': website,
                                'type_count': type_count
                            })
                    else:
                        seniorplace_stats['single_type'] += 1
                else:
                    seniorplace_stats['no_types'] += 1
    
    # Print analysis
    print(f"Total Senior Place listings: {seniorplace_stats['total']:,}")
    print(f"  Single care type: {seniorplace_stats['single_type']:,} ({seniorplace_stats['single_type']/seniorplace_stats['total']*100:.1f}%)")
    print(f"  Multiple care types: {seniorplace_stats['multiple_types']:,} ({seniorplace_stats['multiple_types']/seniorplace_stats['total']*100:.1f}%)")
    print(f"  No care types: {seniorplace_stats['no_types']:,} ({seniorplace_stats['no_types']/seniorplace_stats['total']*100:.1f}%)")
    print()
    
    print("🚨 PROBLEM: MULTIPLE CARE TYPES PER LISTING")
    print("=" * 50)
    print("Allison expects 1:1 mapping with Senior Place, but we have:")
    print()
    
    # Show most common problematic combinations
    print("Most common type combinations (causing discrepancy):")
    for combination, count in sorted(seniorplace_stats['type_combinations'].items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = count / seniorplace_stats['multiple_types'] * 100 if seniorplace_stats['multiple_types'] > 0 else 0
        print(f"  • {combination}: {count:,} listings ({pct:.1f}%)")
    print()
    
    print("EXAMPLES OF PROBLEMATIC LISTINGS:")
    print("-" * 40)
    for i, example in enumerate(seniorplace_stats['examples'][:5], 1):
        print(f"{i}. {example['title']}")
        print(f"   Current Types: {example['types']} ({example['type_count']} types)")
        print(f"   Senior Place URL: {example['url']}")
        print()
    
    print("🎯 SOLUTION APPROACH")
    print("=" * 25)
    print("1. Extract all Senior Place URLs from current data")
    print("2. Re-scrape each URL to get the PRIMARY care type only")
    print("3. Use our existing mapping system to convert to CMS categories")
    print("4. Update each listing to have SINGLE care type (not multiple)")
    print("5. Generate updated CSV for re-import")
    print()
    
    print("📊 IMPACT ESTIMATE")
    print("=" * 20)
    print(f"Listings to update: {seniorplace_stats['multiple_types']:,}")
    print(f"Percentage of total: {seniorplace_stats['multiple_types']/seniorplace_stats['total']*100:.1f}%")
    
    if seniorplace_stats['multiple_types'] > 0:
        print("\n⚠️  HIGH PRIORITY: This explains Allison's discrepancy!")
        print("She sees single care types on Senior Place, we show multiple.")
    else:
        print("\n✅ No multiple type issues found")
    
    return seniorplace_stats

if __name__ == "__main__":
    analyze_discrepancy()
