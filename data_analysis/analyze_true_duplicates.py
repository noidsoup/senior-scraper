#!/usr/bin/env python3
"""
Find true duplicates: SAME title AND SAME address
Include all the fields for comparison
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

def find_true_duplicates():
    print("Reading dataset...")
    df = pd.read_csv('organized_csvs/Listings-Export-2025-August-28-1956.csv')
    print(f"Total listings: {len(df)}")
    
    # Normalize addresses for comparison
    df['normalized_address'] = df['address'].apply(normalize_address)
    
    # Find duplicates by BOTH title AND normalized address
    print("Finding duplicates with same title AND same address...")
    
    # Create a combined key for title + address
    df['title_address_key'] = df['Title'].str.strip() + '|||' + df['normalized_address']
    
    # Find records with duplicate title+address combinations
    true_duplicates = df[df.duplicated(subset=['title_address_key'], keep=False)].copy()
    true_duplicates = true_duplicates.sort_values(['Title', 'normalized_address'])
    
    print(f"Found {len(true_duplicates)} listings that are true duplicates (same title + same address)")
    
    # Create enhanced output with all comparison fields
    duplicate_records = []
    
    for _, row in true_duplicates.iterrows():
        source = 'seniorly' if 'seniorly' in str(row['website']) else 'seniorplace' if 'seniorplace' in str(row['website']) else 'other'
        
        duplicate_records.append({
            'ID': row['ID'],
            'Title': row['Title'],
            'Address': row['address'],
            'Website': row['website'],
            'Source': source,
            'Phone': row['phone'] if 'phone' in df.columns and pd.notna(row['phone']) else '',
            'Photos': row['photos'] if 'photos' in df.columns and pd.notna(row['photos']) else '',
            'Price': row['price'] if 'price' in df.columns and pd.notna(row['price']) else '',
            'Senior_Place_URL': row['_senior_place_url'] if '_senior_place_url' in df.columns and pd.notna(row['_senior_place_url']) else '',
            'Seniorly_URL': row['seniorly_url'] if 'seniorly_url' in df.columns and pd.notna(row['seniorly_url']) else '',
            'Content': row['Content'] if 'Content' in df.columns and pd.notna(row['Content']) else '',
            'Normalized_Address': row['normalized_address'],
            'Title_Address_Key': row['title_address_key']
        })
    
    # Save to CSV
    true_dupes_df = pd.DataFrame(duplicate_records)
    true_dupes_df.to_csv('organized_csvs/TRUE_DUPLICATES_SAME_TITLE_AND_ADDRESS.csv', index=False)
    
    print(f"Saved to: organized_csvs/TRUE_DUPLICATES_SAME_TITLE_AND_ADDRESS.csv")
    
    # Analysis and samples
    print("\\n=== ANALYSIS ===")
    
    # Group by title+address to show duplicate groups
    groups = true_dupes_df.groupby('Title_Address_Key')
    print(f"Number of unique facilities with duplicates: {len(groups)}")
    
    # Show sample duplicate groups
    print("\\nSample duplicate groups:")
    sample_count = 0
    for key, group in groups:
        if sample_count >= 10:
            break
        sample_count += 1
        
        title = group.iloc[0]['Title']
        address = group.iloc[0]['Address']
        
        print(f"\\n{sample_count}. '{title}' at {address}")
        print(f"   {len(group)} duplicates:")
        
        for _, row in group.iterrows():
            has_photos = 'Yes' if row['Photos'] else 'No'
            has_content = 'Yes' if row['Content'] else 'No'
            has_price = 'Yes' if row['Price'] else 'No'
            
            print(f"     ID {row['ID']}: {row['Source']} | Photos: {has_photos} | Content: {has_content} | Price: {has_price}")
    
    # Summary stats
    seniorplace_dupes = true_dupes_df[true_dupes_df['Source'] == 'seniorplace']
    seniorly_dupes = true_dupes_df[true_dupes_df['Source'] == 'seniorly']
    
    print(f"\\nSource breakdown:")
    print(f"  Senior Place duplicates: {len(seniorplace_dupes)}")
    print(f"  Seniorly duplicates: {len(seniorly_dupes)}")
    print(f"  Other/Unknown: {len(true_dupes_df) - len(seniorplace_dupes) - len(seniorly_dupes)}")
    
    # Cross-source analysis
    cross_source_groups = 0
    for key, group in groups:
        sources = group['Source'].unique()
        if len(sources) > 1:
            cross_source_groups += 1
    
    print(f"\\nCross-source duplicates (Senior Place + Seniorly): {cross_source_groups} facility groups")
    
    return true_dupes_df

if __name__ == "__main__":
    find_true_duplicates()
