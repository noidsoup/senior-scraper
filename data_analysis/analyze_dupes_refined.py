#!/usr/bin/env python3
"""
Refined duplicate analysis:
1. Exact title matches (true duplicates)
2. Same address, different titles (possible different facilities at same location)
"""

import pandas as pd
import re

def normalize_address(addr):
    if pd.isna(addr):
        return ''
    addr = str(addr).lower().strip()
    addr = re.sub(r'\bwest\b', 'w', addr)
    addr = re.sub(r'\beast\b', 'e', addr) 
    addr = re.sub(r'\bnorth\b', 'n', addr)
    addr = re.sub(r'\bsouth\b', 's', addr)
    addr = re.sub(r'\bstreet\b', 'st', addr)
    addr = re.sub(r'\bavenue\b', 'ave', addr)
    addr = re.sub(r'\boulevard\b', 'blvd', addr)
    addr = re.sub(r'\blane\b', 'ln', addr)
    addr = re.sub(r'\bdrive\b', 'dr', addr)
    addr = re.sub(r'\broad\b', 'rd', addr)
    addr = re.sub(r'st\s+lane', 'st ln', addr)
    addr = re.sub(r'\s+', ' ', addr)
    addr = re.sub(r'[^\w\s]', '', addr)
    return addr.strip()

def analyze_refined_duplicates():
    # Read the full dataset
    print("Reading dataset...")
    df = pd.read_csv('organized_csvs/Listings-Export-2025-August-28-1956.csv')
    print(f"Total listings: {len(df)}")
    
    # Normalize addresses for grouping
    df['normalized_address'] = df['address'].apply(normalize_address)
    
    # 1. EXACT TITLE MATCHES
    print("\n=== 1. EXACT TITLE MATCHES ===")
    exact_title_dupes = df[df.duplicated(subset=['Title'], keep=False)].copy()
    exact_title_dupes = exact_title_dupes.sort_values('Title')
    
    print(f"Found {len(exact_title_dupes)} listings with exact title duplicates")
    
    exact_title_groups = []
    for title in exact_title_dupes['Title'].unique():
        group = exact_title_dupes[exact_title_dupes['Title'] == title]
        
        group_data = []
        for _, row in group.iterrows():
            source = 'seniorly' if 'seniorly' in str(row['website']) else 'seniorplace' if 'seniorplace' in str(row['website']) else 'other'
            group_data.append({
                'ID': row['ID'],
                'Title': row['Title'],
                'Address': row['address'],
                'Website': row['website'],
                'Source': source
            })
        
        exact_title_groups.extend(group_data)
    
    # Save exact title duplicates
    exact_df = pd.DataFrame(exact_title_groups)
    exact_df.to_csv('organized_csvs/EXACT_TITLE_DUPLICATES.csv', index=False)
    print(f"Saved to: organized_csvs/EXACT_TITLE_DUPLICATES.csv")
    
    # 2. SAME ADDRESS, DIFFERENT TITLES
    print("\n=== 2. SAME ADDRESS, DIFFERENT TITLES ===")
    
    # Group by normalized address
    address_groups = df[df['normalized_address'] != ''].groupby('normalized_address')
    
    same_address_different_titles = []
    
    for norm_addr, group in address_groups:
        if len(group) > 1:
            # Check if titles are different
            unique_titles = group['Title'].nunique()
            if unique_titles > 1:
                # This is same address with different titles
                for _, row in group.iterrows():
                    source = 'seniorly' if 'seniorly' in str(row['website']) else 'seniorplace' if 'seniorplace' in str(row['website']) else 'other'
                    same_address_different_titles.append({
                        'ID': row['ID'],
                        'Title': row['Title'],
                        'Address': row['address'],
                        'Website': row['website'],
                        'Source': source,
                        'Normalized_Address': norm_addr,
                        'Group_Size': len(group)
                    })
    
    # Save same address different titles
    same_addr_df = pd.DataFrame(same_address_different_titles)
    same_addr_df = same_addr_df.sort_values(['Address', 'Title'])
    same_addr_df.to_csv('organized_csvs/SAME_ADDRESS_DIFFERENT_TITLES.csv', index=False)
    print(f"Found {len(same_addr_df)} listings at same addresses with different titles")
    print(f"Saved to: organized_csvs/SAME_ADDRESS_DIFFERENT_TITLES.csv")
    
    # 3. SUMMARY ANALYSIS
    print("\n=== 3. SUMMARY ===")
    
    # Show sample exact title matches
    print("\\nSample Exact Title Matches:")
    exact_title_sample = exact_df.groupby('Title').head(10)  # First 10 unique titles
    for title in exact_title_sample['Title'].unique()[:5]:
        matches = exact_df[exact_df['Title'] == title]
        print(f"\\n'{title}' ({len(matches)} copies):")
        for _, row in matches.iterrows():
            print(f"  ID {row['ID']}: {row['Source']} | {row['Address'][:50]}...")
    
    # Show sample same address different titles
    print("\\nSample Same Address, Different Titles:")
    same_addr_sample = same_addr_df.groupby('Normalized_Address')
    sample_count = 0
    for norm_addr, group in same_addr_sample:
        if sample_count >= 5:
            break
        sample_count += 1
        print(f"\\nAddress: {group.iloc[0]['Address']}")
        for _, row in group.iterrows():
            print(f"  ID {row['ID']}: '{row['Title']}' ({row['Source']})")
    
    print(f"\\nFINAL COUNTS:")
    print(f"  Exact title duplicates: {len(exact_df)} listings")
    print(f"  Same address, different titles: {len(same_addr_df)} listings")
    print(f"  Unique titles with duplicates: {exact_df['Title'].nunique()}")
    print(f"  Unique addresses with multiple facilities: {same_addr_df['Normalized_Address'].nunique()}")

if __name__ == "__main__":
    analyze_refined_duplicates()
