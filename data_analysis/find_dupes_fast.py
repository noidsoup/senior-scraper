#!/usr/bin/env python3
"""
Fast duplicate finder - focuses on exact matches first, then targeted similarity checks.
"""

import pandas as pd
import re
from urllib.parse import urlparse
from difflib import SequenceMatcher
import sys
from collections import defaultdict

def normalize_title(title):
    """Normalize title for comparison"""
    if pd.isna(title):
        return ""
    
    normalized = str(title).lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
    normalized = re.sub(r'\b(inc|llc|ltd|corp|corporation)\b', '', normalized)  # Remove business suffixes
    normalized = re.sub(r'\b(the|a|an)\b', '', normalized)  # Remove articles
    normalized = re.sub(r'\s+', ' ', normalized).strip()  # Clean up spaces again
    
    return normalized

def extract_domain(url):
    """Extract domain from URL for comparison"""
    if pd.isna(url) or not url:
        return ""
    try:
        parsed = urlparse(str(url))
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return ""

def title_similarity(title1, title2):
    """Calculate similarity between two titles"""
    if not title1 or not title2:
        return 0.0
    return SequenceMatcher(None, title1, title2).ratio()

def find_duplicates_fast(csv_path):
    """Fast duplicate detection using grouping strategies"""
    print(f"Reading CSV: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    print(f"Total listings: {len(df)}")
    
    # Check for required columns
    if 'Title' not in df.columns:
        print("ERROR: No 'Title' column found")
        return
    
    if 'website' not in df.columns:
        print("WARNING: No 'website' column found")
        return
    
    # Show data breakdown
    has_website = df['website'].notna().sum()
    unique_websites = df['website'].dropna().nunique()
    print(f"Listings with website: {has_website}")
    print(f"Unique website domains: {unique_websites}")
    
    duplicates = []
    
    # PHASE 1: Find exact website domain matches
    print("\nPhase 1: Finding exact website domain matches...")
    df['website_domain'] = df['website'].apply(extract_domain)
    
    # Group by website domain
    domain_groups = df.groupby('website_domain')
    exact_website_matches = 0
    
    for domain, group in domain_groups:
        if domain and len(group) > 1:  # Skip empty domains and single entries
            exact_website_matches += len(group)
            print(f"  Domain '{domain}': {len(group)} listings")
            
            # Add all pairs within this domain group
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    row1 = group.iloc[i]
                    row2 = group.iloc[j]
                    
                    duplicates.append({
                        'ID1': row1['ID'],
                        'ID2': row2['ID'],
                        'Title1': row1['Title'],
                        'Title2': row2['Title'],
                        'Website1': row1['website'],
                        'Website2': row2['website'],
                        'Similarity': title_similarity(normalize_title(row1['Title']), normalize_title(row2['Title'])),
                        'Reason': f"Exact website domain match: {domain}"
                    })
    
    print(f"Found {exact_website_matches} listings with duplicate website domains")
    
    # PHASE 2: Find high title similarity matches (but only for entries without website matches)
    print("\nPhase 2: Finding high title similarity matches...")
    
    # Get IDs that already have website matches
    website_matched_ids = set()
    for dup in duplicates:
        website_matched_ids.add(dup['ID1'])
        website_matched_ids.add(dup['ID2'])
    
    # Filter to entries without website matches
    remaining_df = df[~df['ID'].isin(website_matched_ids)].copy()
    print(f"Checking {len(remaining_df)} remaining listings for title similarity...")
    
    # Group by normalized title for efficiency
    remaining_df['normalized_title'] = remaining_df['Title'].apply(normalize_title)
    title_groups = remaining_df.groupby('normalized_title')
    
    title_matches = 0
    for norm_title, group in title_groups:
        if norm_title and len(group) > 1:  # Skip empty titles and single entries
            title_matches += len(group)
            print(f"  Exact title match '{norm_title[:50]}...': {len(group)} listings")
            
            # Add all pairs within this title group
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    row1 = group.iloc[i]
                    row2 = group.iloc[j]
                    
                    duplicates.append({
                        'ID1': row1['ID'],
                        'ID2': row2['ID'],
                        'Title1': row1['Title'],
                        'Title2': row2['Title'],
                        'Website1': row1['website'] if pd.notna(row1['website']) else '',
                        'Website2': row2['website'] if pd.notna(row2['website']) else '',
                        'Similarity': 1.0,  # Exact match after normalization
                        'Reason': "Exact title match (after normalization)"
                    })
    
    print(f"Found {title_matches} listings with exact title matches")
    
    # PHASE 3: Sample check for near-miss title similarities (limited scope)
    print("\nPhase 3: Sample check for near-miss title similarities...")
    
    # Take a smaller sample for similarity checking to avoid O(n²) explosion
    sample_size = min(1000, len(remaining_df))
    sample_df = remaining_df.sample(n=sample_size) if len(remaining_df) > sample_size else remaining_df
    
    similarity_matches = 0
    for i in range(len(sample_df)):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(sample_df)} sample listings...")
            
        for j in range(i + 1, len(sample_df)):
            row1 = sample_df.iloc[i]
            row2 = sample_df.iloc[j]
            
            similarity = title_similarity(row1['normalized_title'], row2['normalized_title'])
            
            if similarity >= 0.9:  # Very high similarity threshold
                similarity_matches += 1
                duplicates.append({
                    'ID1': row1['ID'],
                    'ID2': row2['ID'],
                    'Title1': row1['Title'],
                    'Title2': row2['Title'],
                    'Website1': row1['website'] if pd.notna(row1['website']) else '',
                    'Website2': row2['website'] if pd.notna(row2['website']) else '',
                    'Similarity': similarity,
                    'Reason': f"High title similarity ({similarity:.2f})"
                })
    
    print(f"Found {similarity_matches} high similarity matches in sample")
    
    # RESULTS
    print(f"\n" + "="*80)
    print(f"DUPLICATE ANALYSIS COMPLETE")
    print(f"="*80)
    
    website_dupes = [d for d in duplicates if 'website domain match' in d['Reason']]
    title_dupes = [d for d in duplicates if 'title match' in d['Reason']]
    similarity_dupes = [d for d in duplicates if 'similarity' in d['Reason']]
    
    print(f"\nWebsite domain duplicates: {len(website_dupes)}")
    for i, dup in enumerate(website_dupes, 1):
        print(f"  {i}. IDs {dup['ID1']}-{dup['ID2']}: {dup['Reason']}")
        print(f"     '{dup['Title1'][:60]}{'...' if len(dup['Title1']) > 60 else ''}'")
        print(f"     '{dup['Title2'][:60]}{'...' if len(dup['Title2']) > 60 else ''}'")
        print(f"     Website: {dup['Website1']}")
        print()
    
    print(f"\nExact title duplicates: {len(title_dupes)}")
    for i, dup in enumerate(title_dupes[:10], 1):  # Show first 10
        print(f"  {i}. IDs {dup['ID1']}-{dup['ID2']}: {dup['Title1']}")
        if dup['Website1']:
            print(f"     Website1: {dup['Website1']}")
        if dup['Website2']:
            print(f"     Website2: {dup['Website2']}")
        print()
    
    if len(title_dupes) > 10:
        print(f"  ... and {len(title_dupes) - 10} more exact title matches")
    
    print(f"\nHigh similarity duplicates: {len(similarity_dupes)}")
    for i, dup in enumerate(similarity_dupes, 1):
        print(f"  {i}. IDs {dup['ID1']}-{dup['ID2']}: {dup['Reason']}")
        print(f"     '{dup['Title1'][:60]}{'...' if len(dup['Title1']) > 60 else ''}'")
        print(f"     '{dup['Title2'][:60]}{'...' if len(dup['Title2']) > 60 else ''}'")
        print()
    
    # Save to CSV
    if duplicates:
        dup_df = pd.DataFrame(duplicates)
        output_file = csv_path.replace('.csv', '_DUPLICATES_FAST.csv')
        dup_df.to_csv(output_file, index=False)
        print(f"\nAll {len(duplicates)} duplicate pairs saved to: {output_file}")
    
    print(f"\nFINAL SUMMARY:")
    print(f"  Total listings: {len(df)}")
    print(f"  Total duplicate pairs: {len(duplicates)}")
    print(f"  Website domain matches: {len(website_dupes)}")
    print(f"  Exact title matches: {len(title_dupes)}")
    print(f"  High similarity matches: {len(similarity_dupes)}")
    
    return duplicates

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 find_dupes_fast.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    find_duplicates_fast(csv_file)
