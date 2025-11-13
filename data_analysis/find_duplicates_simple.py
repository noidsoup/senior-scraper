#!/usr/bin/env python3
"""
Simple duplicate finder focusing on Title similarity and website field matches.
Designed for WordPress export CSVs with ACF fields.
"""

import pandas as pd
import re
from urllib.parse import urlparse
from difflib import SequenceMatcher
import sys

def normalize_title(title):
    """Normalize title for comparison"""
    if pd.isna(title):
        return ""
    
    # Convert to lowercase and strip whitespace
    normalized = str(title).lower().strip()
    
    # Remove common variations
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
        # Remove www prefix
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

def find_duplicates(csv_path):
    """Find duplicates in WordPress export CSV"""
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
        website_col = None
    else:
        website_col = 'website'
    
    # Show data breakdown
    has_website = df[website_col].notna().sum() if website_col else 0
    print(f"Listings with website: {has_website}")
    
    # Prepare data for analysis
    df['normalized_title'] = df['Title'].apply(normalize_title)
    if website_col:
        df['website_domain'] = df[website_col].apply(extract_domain)
    
    # Find duplicates
    duplicates = []
    
    print(f"\nAnalyzing {len(df)} listings for duplicates...")
    
    for i in range(len(df)):
        if i % 500 == 0:
            print(f"  Processed {i}/{len(df)} listings...")
            
        for j in range(i + 1, len(df)):
            row1 = df.iloc[i]
            row2 = df.iloc[j]
            
            title1 = row1['normalized_title']
            title2 = row2['normalized_title']
            
            # Skip if either title is empty
            if not title1 or not title2:
                continue
            
            # Check title similarity
            similarity = title_similarity(title1, title2)
            
            # Check for website domain match
            website_match = False
            if website_col:
                domain1 = row1['website_domain'] if pd.notna(row1['website_domain']) else ""
                domain2 = row2['website_domain'] if pd.notna(row2['website_domain']) else ""
                if domain1 and domain2 and domain1 == domain2:
                    website_match = True
            
            # Consider it a duplicate if:
            # 1. High title similarity (>= 0.85) OR
            # 2. Website domain match OR  
            # 3. Very high title similarity (>= 0.95)
            is_duplicate = False
            reason = ""
            
            if website_match:
                is_duplicate = True
                reason = f"Website domain match: {domain1} (title similarity: {similarity:.2f})"
            elif similarity >= 0.95:
                is_duplicate = True
                reason = f"Very high title similarity ({similarity:.2f})"
            elif similarity >= 0.85:
                is_duplicate = True
                reason = f"High title similarity ({similarity:.2f})"
            
            if is_duplicate:
                duplicates.append({
                    'ID1': row1['ID'] if 'ID' in df.columns else i+1,
                    'ID2': row2['ID'] if 'ID' in df.columns else j+1,
                    'Title1': row1['Title'],
                    'Title2': row2['Title'],
                    'Website1': row1[website_col] if website_col and pd.notna(row1[website_col]) else '',
                    'Website2': row2[website_col] if website_col and pd.notna(row2[website_col]) else '',
                    'Similarity': similarity,
                    'Reason': reason
                })
    
    print(f"\nFound {len(duplicates)} potential duplicate pairs:")
    print("=" * 120)
    
    # Group by reason for better analysis
    website_dupes = [d for d in duplicates if 'Website domain match' in d['Reason']]
    title_dupes = [d for d in duplicates if 'title similarity' in d['Reason']]
    
    print(f"\nWebsite domain matches: {len(website_dupes)}")
    for i, dup in enumerate(website_dupes, 1):
        print(f"\n  #{i}: {dup['Reason']}")
        print(f"    ID {dup['ID1']}: '{dup['Title1']}'")
        print(f"    ID {dup['ID2']}: '{dup['Title2']}'")
        print(f"    Website: {dup['Website1']}")
    
    print(f"\nTitle similarity matches: {len(title_dupes)}")
    for i, dup in enumerate(title_dupes[:20], 1):  # Show first 20
        print(f"\n  #{i}: {dup['Reason']}")
        print(f"    ID {dup['ID1']}: '{dup['Title1']}'")
        print(f"    ID {dup['ID2']}: '{dup['Title2']}'")
        if dup['Website1']:
            print(f"    Website1: {dup['Website1']}")
        if dup['Website2']:
            print(f"    Website2: {dup['Website2']}")
    
    if len(title_dupes) > 20:
        print(f"\n  ... and {len(title_dupes) - 20} more title similarity matches")
    
    # Save to CSV
    if duplicates:
        dup_df = pd.DataFrame(duplicates)
        output_file = csv_path.replace('.csv', '_DUPLICATES.csv')
        dup_df.to_csv(output_file, index=False)
        print(f"\nAll duplicates saved to: {output_file}")
    
    print(f"\nSUMMARY:")
    print(f"  Total listings analyzed: {len(df)}")
    print(f"  Total duplicate pairs found: {len(duplicates)}")
    print(f"  Website domain matches: {len(website_dupes)}")
    print(f"  Title similarity matches: {len(title_dupes)}")
    
    return duplicates

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 find_duplicates_simple.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    find_duplicates(csv_file)
