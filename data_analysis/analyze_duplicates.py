#!/usr/bin/env python3
"""
Analyze CSV for duplicate listings based on title and website fields.
Designed to find duplicates between Seniorly and Senior Place data sources.
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

def analyze_duplicates(csv_path):
    """Analyze CSV for potential duplicates"""
    print(f"Reading CSV: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    print(f"Total listings: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Check for different column name variations
    seniorplace_col = None
    seniorly_col = None
    website_col = None
    
    for col in df.columns:
        if 'seniorplace' in col.lower() and 'url' in col.lower():
            seniorplace_col = col
        elif 'seniorly' in col.lower() and 'url' in col.lower():
            seniorly_col = col
        elif col.lower() == 'website':
            website_col = col
    
    print(f"Found columns - Senior Place: {seniorplace_col}, Seniorly: {seniorly_col}, Website: {website_col}")
    
    # Show data source breakdown
    if seniorplace_col:
        has_seniorplace = df[seniorplace_col].notna().sum()
    else:
        has_seniorplace = 0
        
    if seniorly_col:
        has_seniorly = df[seniorly_col].notna().sum()
    else:
        has_seniorly = 0
        
    if website_col:
        has_website = df[website_col].notna().sum()
    else:
        has_website = 0
    
    if seniorplace_col and seniorly_col:
        has_both = ((df[seniorplace_col].notna()) & (df[seniorly_col].notna())).sum()
    else:
        has_both = 0
    
    print(f"\nData source breakdown:")
    print(f"  Has Senior Place URL: {has_seniorplace}")
    print(f"  Has Seniorly URL: {has_seniorly}")
    print(f"  Has Website field: {has_website}")
    print(f"  Has both URLs: {has_both}")
    
    # Prepare data for analysis
    df['normalized_title'] = df['Title'].apply(normalize_title)
    if seniorplace_col:
        df['seniorplace_domain'] = df[seniorplace_col].apply(extract_domain)
    if seniorly_col:
        df['seniorly_domain'] = df[seniorly_col].apply(extract_domain)
    if website_col:
        df['website_domain'] = df[website_col].apply(extract_domain)
    
    # Find potential duplicates
    duplicates = []
    
    print(f"\nAnalyzing for duplicates...")
    
    for i in range(len(df)):
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
            
            # Check for domain matches across all URL fields
            domain_match = False
            matched_domains = []
            
            # Get all domain values for each row
            row1_domains = []
            row2_domains = []
            
            if seniorplace_col and 'seniorplace_domain' in df.columns:
                if pd.notna(row1['seniorplace_domain']) and row1['seniorplace_domain']:
                    row1_domains.append(row1['seniorplace_domain'])
                if pd.notna(row2['seniorplace_domain']) and row2['seniorplace_domain']:
                    row2_domains.append(row2['seniorplace_domain'])
            
            if seniorly_col and 'seniorly_domain' in df.columns:
                if pd.notna(row1['seniorly_domain']) and row1['seniorly_domain']:
                    row1_domains.append(row1['seniorly_domain'])
                if pd.notna(row2['seniorly_domain']) and row2['seniorly_domain']:
                    row2_domains.append(row2['seniorly_domain'])
            
            if website_col and 'website_domain' in df.columns:
                if pd.notna(row1['website_domain']) and row1['website_domain']:
                    row1_domains.append(row1['website_domain'])
                if pd.notna(row2['website_domain']) and row2['website_domain']:
                    row2_domains.append(row2['website_domain'])
            
            # Check for any domain matches
            for domain1 in row1_domains:
                for domain2 in row2_domains:
                    if domain1 == domain2:
                        domain_match = True
                        matched_domains.append(domain1)
            
            # Determine data sources for each row
            source1 = []
            source2 = []
            
            if seniorplace_col and pd.notna(row1[seniorplace_col]):
                source1.append('Senior Place')
            if seniorly_col and pd.notna(row1[seniorly_col]):
                source1.append('Seniorly')
            if website_col and pd.notna(row1[website_col]):
                source1.append('Website')
                
            if seniorplace_col and pd.notna(row2[seniorplace_col]):
                source2.append('Senior Place')
            if seniorly_col and pd.notna(row2[seniorly_col]):
                source2.append('Seniorly')
            if website_col and pd.notna(row2[website_col]):
                source2.append('Website')
            
            # Consider it a potential duplicate if:
            # 1. High title similarity (>= 0.8) OR
            # 2. Domain match OR
            # 3. Moderate title similarity (>= 0.6) AND different data sources
            is_duplicate = False
            reason = ""
            
            if similarity >= 0.8:
                is_duplicate = True
                reason = f"High title similarity ({similarity:.2f})"
            elif domain_match:
                is_duplicate = True
                reason = f"Domain match: {', '.join(matched_domains)} (similarity: {similarity:.2f})"
            elif similarity >= 0.6 and len(set(source1).intersection(set(source2))) == 0:
                is_duplicate = True
                reason = f"Cross-source similarity ({similarity:.2f})"
            
            if is_duplicate:
                # Get representative URLs for display
                url1 = ""
                url2 = ""
                
                if seniorplace_col and pd.notna(row1[seniorplace_col]):
                    url1 = row1[seniorplace_col]
                elif seniorly_col and pd.notna(row1[seniorly_col]):
                    url1 = row1[seniorly_col]
                elif website_col and pd.notna(row1[website_col]):
                    url1 = row1[website_col]
                
                if seniorplace_col and pd.notna(row2[seniorplace_col]):
                    url2 = row2[seniorplace_col]
                elif seniorly_col and pd.notna(row2[seniorly_col]):
                    url2 = row2[seniorly_col]
                elif website_col and pd.notna(row2[website_col]):
                    url2 = row2[website_col]
                
                duplicates.append({
                    'Index1': i,
                    'Index2': j,
                    'Title1': row1['Title'],
                    'Title2': row2['Title'],
                    'Source1': ', '.join(source1) if source1 else 'Unknown',
                    'Source2': ', '.join(source2) if source2 else 'Unknown',
                    'URL1': url1,
                    'URL2': url2,
                    'Website1': row1[website_col] if website_col and pd.notna(row1[website_col]) else '',
                    'Website2': row2[website_col] if website_col and pd.notna(row2[website_col]) else '',
                    'Similarity': similarity,
                    'Reason': reason
                })
    
    print(f"\nFound {len(duplicates)} potential duplicate pairs:")
    print("=" * 100)
    
    for i, dup in enumerate(duplicates, 1):
        print(f"\nDuplicate #{i}:")
        print(f"  Row {dup['Index1']+1}: '{dup['Title1']}' ({dup['Source1']})")
        print(f"  Row {dup['Index2']+1}: '{dup['Title2']}' ({dup['Source2']})")
        print(f"  Similarity: {dup['Similarity']:.2f}")
        print(f"  Reason: {dup['Reason']}")
        print(f"  URL1: {dup['URL1']}")
        print(f"  URL2: {dup['URL2']}")
        if dup['Website1'] or dup['Website2']:
            print(f"  Website1: {dup['Website1']}")
            print(f"  Website2: {dup['Website2']}")
    
    # Save duplicates to CSV for review
    if duplicates:
        dup_df = pd.DataFrame(duplicates)
        output_file = csv_path.replace('.csv', '_DUPLICATES_ANALYSIS.csv')
        dup_df.to_csv(output_file, index=False)
        print(f"\nDuplicates analysis saved to: {output_file}")
    
    # Summary statistics
    cross_source_dupes = [d for d in duplicates if d['Source1'] != d['Source2']]
    same_source_dupes = [d for d in duplicates if d['Source1'] == d['Source2']]
    
    print(f"\nSummary:")
    print(f"  Total duplicate pairs: {len(duplicates)}")
    print(f"  Cross-source duplicates (Seniorly vs Senior Place): {len(cross_source_dupes)}")
    print(f"  Same-source duplicates: {len(same_source_dupes)}")
    
    return duplicates

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_duplicates.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    analyze_duplicates(csv_file)
