#!/usr/bin/env python3
"""
Final Seniorly classifier that applies smart classification to all 1,478 listings.

Based on testing, the most reliable indicators are:
1. Capacity numbers (when available) - most reliable
2. Title patterns - moderately reliable  
3. Known brands - highly reliable for communities

Strategy: 
- Scrape capacity for unclear cases first
- Apply title-based classification for obvious cases
- Focus on high-confidence corrections only
"""

import pandas as pd
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json
import sys
from pathlib import Path

class FinalSeniorlyClassifier:
    def __init__(self):
        # These patterns are reliable based on testing
        self.definite_home_indicators = [
            r'\badult care home\b',
            r'\bcare home\b(?!\s+of)',  # "Care Home" but not "Care Home of [Place]"
            r'\board and care\b',
            r'\bresidential care\b',
            r'\bfamily care\b'
        ]
        
        self.definite_community_indicators = [
            r'\bsenior living\b',
            r'\bretirement community\b',
            r'\bassisted living community\b',
            r'\bmanor\b',
            r'\bvillage\b', 
            r'\bgardens\b',
            r'\bterrace\b',
            r'\bheights\b',
            r'\bridge\b',
            r'\bplaza\b',
            r'\bcenter\b(?!\s+care)',  # "Center" but not "Center Care"
            r'\bfacility\b'
        ]
        
        # Known large community brands (highly reliable)
        self.large_brands = [
            'aegis', 'brookdale', 'sunrise', 'atria', 'merrill gardens',
            'belmont village', 'acoya', 'watermark', 'holiday retirement',
            'inspirations', 'cadence', 'avenir'
        ]

    def classify_by_title_and_brand(self, title):
        """Fast classification based on title patterns and brands"""
        score = 0
        reasons = []
        title_lower = title.lower()
        
        # Strong home indicators
        for pattern in self.definite_home_indicators:
            if re.search(pattern, title_lower):
                score -= 4
                reasons.append(f"Title: {pattern} (strong home)")
        
        # Strong community indicators  
        for pattern in self.definite_community_indicators:
            if re.search(pattern, title_lower):
                score += 3
                reasons.append(f"Title: {pattern} (community)")
        
        # Brand recognition (very reliable)
        for brand in self.large_brands:
            if brand in title_lower:
                score += 4
                reasons.append(f"Brand: {brand} (large community)")
        
        # Generic "Assisted Living" without "Home" 
        if ('assisted living' in title_lower and 
            not re.search(r'\bhome\b', title_lower) and 
            score == 0):  # Only if no other indicators
            score += 1
            reasons.append("Generic AL (likely community)")
        
        return score, reasons

    async def get_capacity_for_unclear_cases(self, session, unclear_listings):
        """Get capacity data for listings that need it"""
        results = []
        
        for i, (title, url) in enumerate(unclear_listings):
            if i % 10 == 0:
                print(f"   Checking capacity {i+1}/{len(unclear_listings)}: {title[:40]}")
            
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        text = soup.get_text().lower()
                        
                        # Extract capacity numbers
                        capacity_numbers = []
                        patterns = [
                            r'(\d+)\s*bed[s]?\b',
                            r'(\d+)\s*unit[s]?\b',
                            r'(\d+)\s*resident[s]?\b',
                            r'(\d+)\s*room[s]?\b',
                            r'(\d+)\s*apartment[s]?\b',
                            r'up\s*to\s*(\d+)',
                            r'accommodate[s]?\s*(\d+)'
                        ]
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, text)
                            for match in matches:
                                num = int(match)
                                if 1 <= num <= 200:
                                    capacity_numbers.append(num)
                        
                        if capacity_numbers:
                            max_capacity = max(capacity_numbers)
                            results.append((title, url, max_capacity, capacity_numbers))
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                continue
        
        return results

def run_final_classification():
    """Apply final classification to all 1,478 Seniorly listings"""
    
    # Load all listings
    df = pd.read_csv('seniorly_listings_for_scraping.csv')
    classifier = FinalSeniorlyClassifier()
    
    print(f"🎯 FINAL CLASSIFICATION OF ALL {len(df)} SENIORLY LISTINGS")
    print("=" * 60)
    
    results = []
    clear_homes = []
    clear_communities = []
    unclear_for_scraping = []
    
    # Phase 1: Title-based classification
    print("\n📋 Phase 1: Title and brand-based classification...")
    
    for _, row in df.iterrows():
        title = row['Title']
        url = row['seniorly_url_final']
        current_type = row['type']
        
        score, reasons = classifier.classify_by_title_and_brand(title)
        
        if score <= -3:
            classification = "Assisted Living Home"
            confidence = "High" if score <= -5 else "Medium"
            clear_homes.append({
                'ID': row['ID'],
                'Title': title,
                'URL': url,
                'Current_Type': current_type,
                'Classification': classification,
                'Confidence': confidence,
                'Score': score,
                'Reasons': reasons
            })
        elif score >= 3:
            classification = "Assisted Living Community"
            confidence = "High" if score >= 5 else "Medium"
            clear_communities.append({
                'ID': row['ID'],
                'Title': title,
                'URL': url,
                'Current_Type': current_type,
                'Classification': classification,
                'Confidence': confidence,
                'Score': score,
                'Reasons': reasons
            })
        else:
            # Unclear case - candidate for scraping
            unclear_for_scraping.append((title, url))
            results.append({
                'ID': row['ID'],
                'Title': title,
                'URL': url,
                'Current_Type': current_type,
                'Classification': 'Needs Manual Review',
                'Confidence': 'Low',
                'Score': score,
                'Reasons': reasons
            })
    
    print(f"   🏠 Clear homes: {len(clear_homes)}")
    print(f"   🏢 Clear communities: {len(clear_communities)}")
    print(f"   ❓ Unclear (for capacity check): {len(unclear_for_scraping)}")
    
    # Combine clear results
    all_results = clear_homes + clear_communities + results
    
    # Phase 2: Capacity-based classification for sample of unclear cases
    print(f"\n📋 Phase 2: Checking capacity for sample of unclear cases...")
    
    # Check capacity for a sample to improve classifications
    sample_size = min(100, len(unclear_for_scraping))  # Reasonable sample
    sample_unclear = unclear_for_scraping[:sample_size]
    
    if sample_unclear:
        async def check_capacities():
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                return await classifier.get_capacity_for_unclear_cases(session, sample_unclear)
        
        capacity_results = asyncio.run(check_capacities())
        
        # Update classifications based on capacity
        for title, url, max_capacity, all_capacities in capacity_results:
            # Find the corresponding result
            for result in all_results:
                if result['Title'] == title:
                    if max_capacity <= 6:
                        result['Classification'] = 'Assisted Living Home'
                        result['Confidence'] = 'High'
                        result['Score'] = -4
                        result['Reasons'].append(f'Small capacity: {max_capacity}')
                    elif max_capacity <= 10:
                        result['Classification'] = 'Assisted Living Home'
                        result['Confidence'] = 'Medium'
                        result['Score'] = -2
                        result['Reasons'].append(f'Small capacity: {max_capacity}')
                    elif max_capacity >= 50:
                        result['Classification'] = 'Assisted Living Community'
                        result['Confidence'] = 'High'
                        result['Score'] = 4
                        result['Reasons'].append(f'Large capacity: {max_capacity}')
                    elif max_capacity >= 20:
                        result['Classification'] = 'Assisted Living Community'
                        result['Confidence'] = 'Medium'
                        result['Score'] = 2
                        result['Reasons'].append(f'Medium capacity: {max_capacity}')
                    break
        
        print(f"   ✅ Got capacity data for {len(capacity_results)} listings")
    
    # Final summary
    final_homes = [r for r in all_results if r['Classification'] == 'Assisted Living Home']
    final_communities = [r for r in all_results if r['Classification'] == 'Assisted Living Community']
    final_manual = [r for r in all_results if r['Classification'] == 'Needs Manual Review']
    
    print(f"\n📊 FINAL CLASSIFICATION SUMMARY:")
    print(f"   🏠 Homes: {len(final_homes)} ({len(final_homes)/len(all_results)*100:.1f}%)")
    print(f"   🏢 Communities: {len(final_communities)} ({len(final_communities)/len(all_results)*100:.1f}%)")
    print(f"   ❓ Manual Review: {len(final_manual)} ({len(final_manual)/len(all_results)*100:.1f}%)")
    
    # High confidence counts
    high_conf_homes = [h for h in final_homes if h['Confidence'] == 'High']
    high_conf_communities = [c for c in final_communities if c['Confidence'] == 'High']
    
    print(f"\n🎯 HIGH CONFIDENCE CLASSIFICATIONS:")
    print(f"   🏠 High confidence homes: {len(high_conf_homes)}")
    print(f"   🏢 High confidence communities: {len(high_conf_communities)}")
    
    # Export results
    results_df = pd.DataFrame(all_results)
    results_df.to_csv('FINAL_seniorly_classifications.csv', index=False)
    
    # Export high-confidence corrections for WordPress
    corrections = []
    for result in all_results:
        current_is_home = '162' in str(result['Current_Type'])  # Currently classified as home
        
        if (result['Classification'] == 'Assisted Living Community' and 
            result['Confidence'] in ['High', 'Medium'] and 
            current_is_home):
            # Community that's currently labeled as home - needs correction
            corrections.append({
                'ID': result['ID'],
                'Title': result['Title'],
                'Current': 'Home (162)',
                'New': 'Community (5)',
                'Confidence': result['Confidence'],
                'Score': result['Score'],
                'Reasons': ', '.join(result['Reasons'][:3])
            })
    
    if corrections:
        corrections_df = pd.DataFrame(corrections)
        corrections_df.to_csv('FINAL_wp_corrections.csv', index=False)
        
        # Create WordPress import format
        wp_import = pd.DataFrame({
            'ID': corrections_df['ID'],
            'type': '5',  # Assisted Living Community
            'normalized_types': 'Assisted Living Community',
            '_type': '5'
        })
        wp_import.to_csv('FINAL_WP_IMPORT_corrections.csv', index=False)
        
        print(f"\n💾 CORRECTIONS READY:")
        print(f"   Analysis: FINAL_wp_corrections.csv ({len(corrections)} corrections)")
        print(f"   WordPress import: FINAL_WP_IMPORT_corrections.csv")
    
    print(f"\n✅ Complete analysis saved to: FINAL_seniorly_classifications.csv")
    return len(corrections) if corrections else 0

if __name__ == "__main__":
    corrections_count = run_final_classification()
    print(f"\n🎯 READY TO IMPORT: {corrections_count} high-confidence corrections")
