#!/usr/bin/env python3
"""
Simple script to find duplicate titles in CSV
"""

import pandas as pd
import sys

def find_title_duplicates(csv_path):
    """Find duplicate titles"""
    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    
    print(f"Total listings: {len(df)}")
    
    # Find duplicate titles
    duplicates = df[df.duplicated(subset=['Title'], keep=False)].copy()
    duplicates = duplicates.sort_values('Title')
    
    print(f"Found {len(duplicates)} listings with duplicate titles")
    
    # Save results
    output_file = csv_path.replace('.csv', '_TITLE_DUPLICATES.csv')
    duplicates[['ID', 'Title', 'website']].to_csv(output_file, index=False)
    
    print(f"Saved to: {output_file}")
    
    # Show sample
    print("\nSample duplicates:")
    for title in duplicates['Title'].unique()[:10]:
        matches = duplicates[duplicates['Title'] == title]
        print(f"\n'{title}' ({len(matches)} copies):")
        for _, row in matches.iterrows():
            website = row['website'] if pd.notna(row['website']) else 'No website'
            print(f"  ID {row['ID']}: {website}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 simple_title_dupes.py <csv_file>")
        sys.exit(1)
    
    find_title_duplicates(sys.argv[1])
