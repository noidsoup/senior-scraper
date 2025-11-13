#!/usr/bin/env python3
"""
Smart Seniorly classifier that recognizes the template issue but uses
capacity numbers and other specific indicators when available.

Key insight: Seniorly shows both "Board and Care Home" AND "Assisted Living Community"
on most pages as generic options, so we need to focus on:
1. Actual capacity numbers (most reliable)
2. Title patterns (somewhat reliable)
3. Photo analysis patterns (future enhancement)
4. Address patterns (commercial vs residential)
"""

import pandas as pd
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json

class SmartSeniorlyClassifier:
    def __init__(self):
        # Focus on title patterns since page content is too generic
        self.definite_home_patterns = [
            r'\badult care home\b',
            r'\bcare home\b',
            r'\bboard and care\b',
            r'\bresidential care\b',
            r'\bfamily care\b'
        ]
        
        self.definite_community_patterns = [
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
            r'\bcenter\b',
            r'\bfacility\b'
        ]
        
        # Known large community brands
        self.large_brands = [
            'aegis', 'brookdale', 'sunrise', 'atria', 'merrill gardens',
            'belmont village', 'acoya', 'watermark', 'holiday retirement'
        ]
        
        # Patterns that suggest larger facilities
        self.size_indicators = {
            'large': [r'\b(apartment|unit|suite)[s]?\b', r'\bmulti[- ]?story\b', r'\bcampus\b'],
            'small': [r'\bhome[- ]?like\b', r'\bresidential\b', r'\bintimate\b', r'\bcozy\b']
        }

    async def extract_capacity_and_context(self, session, url, title):
        """Extract capacity numbers and contextual clues"""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                all_text = soup.get_text().lower()
                
                # Extract capacity numbers with context
                capacity_info = {
                    'url': url,
                    'title': title,
                    'capacity_numbers': [],
                    'size_clues': [],
                    'address_type': 'unknown'
                }
                
                # Look for capacity with better context
                capacity_patterns = [
                    (r'(\d+)\s*bed[s]?\b', 'beds'),
                    (r'(\d+)\s*unit[s]?\b', 'units'),
                    (r'(\d+)\s*resident[s]?\b', 'residents'),
                    (r'(\d+)\s*room[s]?\b', 'rooms'),
                    (r'(\d+)\s*apartment[s]?\b', 'apartments'),
                    (r'(\d+)\s*suite[s]?\b', 'suites'),
                    (r'up\s*to\s*(\d+)', 'capacity'),
                    (r'accommodate[s]?\s*(\d+)', 'capacity'),
                    (r'(\d+)\s*senior[s]?\b', 'seniors')
                ]
                
                for pattern, context in capacity_patterns:
                    matches = re.findall(pattern, all_text)
                    for match in matches:
                        num = int(match)
                        if 1 <= num <= 200:  # Reasonable range
                            capacity_info['capacity_numbers'].append({
                                'number': num,
                                'context': context
                            })
                
                # Look for size clues
                for size_type, patterns in self.size_indicators.items():
                    for pattern in patterns:
                        if re.search(pattern, all_text):
                            capacity_info['size_clues'].append(f"{size_type}: {pattern}")
                
                # Analyze address for commercial vs residential patterns
                address_elem = soup.find('address') or soup.find(class_=re.compile(r'address', re.I))
                if address_elem:
                    address_text = address_elem.get_text().lower()
                    # Commercial indicators: suite, building, complex
                    if re.search(r'\b(suite|ste|building|bldg|complex|plaza)\b', address_text):
                        capacity_info['address_type'] = 'commercial'
                    # Residential indicators: typical street addresses
                    elif re.search(r'\b\d+\s+\w+\s+(street|st|road|rd|lane|ln|drive|dr|avenue|ave|way|circle|cir)\b', address_text):
                        capacity_info['address_type'] = 'residential'
                
                return capacity_info
                
        except Exception as e:
            print(f"Error extracting from {url}: {e}")
            return None

    def classify_with_context(self, title, capacity_info=None):
        """Classify using title + capacity + context"""
        score = 0
        reasons = []
        title_lower = title.lower()
        
        # Title-based classification (most reliable)
        for pattern in self.definite_home_patterns:
            if re.search(pattern, title_lower):
                score -= 4
                reasons.append(f"Title pattern: {pattern} (strong home indicator)")
        
        for pattern in self.definite_community_patterns:
            if re.search(pattern, title_lower):
                score += 3
                reasons.append(f"Title pattern: {pattern} (community indicator)")
        
        # Brand recognition
        for brand in self.large_brands:
            if brand in title_lower:
                score += 4
                reasons.append(f"Large community brand: {brand}")
        
        # Generic "Assisted Living" without "Home" suggests community
        if 'assisted living' in title_lower and not re.search(r'\bhome\b', title_lower):
            score += 2
            reasons.append("Generic 'Assisted Living' (likely community)")
        
        # Use capacity data if available
        if capacity_info and capacity_info.get('capacity_numbers'):
            max_capacity = max([c['number'] for c in capacity_info['capacity_numbers']])
            capacity_contexts = [c['context'] for c in capacity_info['capacity_numbers']]
            
            if max_capacity <= 6:
                score -= 3
                reasons.append(f"Small capacity: {max_capacity} ({', '.join(set(capacity_contexts))})")
            elif max_capacity <= 10:
                score -= 1
                reasons.append(f"Small-medium capacity: {max_capacity} ({', '.join(set(capacity_contexts))})")
            elif max_capacity >= 50:
                score += 4
                reasons.append(f"Large capacity: {max_capacity} ({', '.join(set(capacity_contexts))})")
            elif max_capacity >= 20:
                score += 2
                reasons.append(f"Medium-large capacity: {max_capacity} ({', '.join(set(capacity_contexts))})")
        
        # Address type
        if capacity_info and capacity_info.get('address_type') == 'commercial':
            score += 1
            reasons.append("Commercial address (community indicator)")
        elif capacity_info and capacity_info.get('address_type') == 'residential':
            score -= 1
            reasons.append("Residential address (home indicator)")
        
        # Size clues
        if capacity_info and capacity_info.get('size_clues'):
            large_clues = [c for c in capacity_info['size_clues'] if c.startswith('large:')]
            small_clues = [c for c in capacity_info['size_clues'] if c.startswith('small:')]
            
            if large_clues:
                score += 1
                reasons.append(f"Large facility clues: {len(large_clues)}")
            if small_clues:
                score -= 1
                reasons.append(f"Small facility clues: {len(small_clues)}")
        
        # Final classification
        if score <= -3:
            classification = "Assisted Living Home"
            confidence = "High" if score <= -5 else "Medium"
        elif score >= 3:
            classification = "Assisted Living Community"
            confidence = "High" if score >= 5 else "Medium"
        else:
            classification = "Needs Manual Review"
            confidence = "Low"
        
        return {
            'classification': classification,
            'confidence': confidence,
            'score': score,
            'reasons': reasons,
            'capacity_info': capacity_info
        }

async def run_smart_classification_sample():
    """Run smart classification on a larger sample"""
    
    # Load listings
    df = pd.read_csv('seniorly_listings_for_scraping.csv')
    
    # Test on a strategic sample
    sample_size = 50
    sample_df = df.sample(n=sample_size, random_state=42)
    
    classifier = SmartSeniorlyClassifier()
    
    # Create session
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    results = []
    
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        print(f"🧠 SMART CLASSIFICATION OF {sample_size} SENIORLY LISTINGS")
        print("=" * 60)
        
        for i, (_, row) in enumerate(sample_df.iterrows()):
            title = row['Title']
            url = row['seniorly_url_final']
            
            print(f"\n[{i+1}/{sample_size}] {title[:50]}")
            
            # Extract capacity and context
            capacity_info = await classifier.extract_capacity_and_context(session, url, title)
            
            # Classify
            result = classifier.classify_with_context(title, capacity_info)
            result['title'] = title
            result['url'] = url
            results.append(result)
            
            print(f"   → {result['classification']} ({result['confidence']})")
            if capacity_info and capacity_info.get('capacity_numbers'):
                capacities = [f"{c['number']} {c['context']}" for c in capacity_info['capacity_numbers']]
                print(f"   Capacity: {', '.join(capacities[:3])}")
            
            # Rate limiting
            await asyncio.sleep(1)
    
    # Analyze results
    homes = [r for r in results if r['classification'] == 'Assisted Living Home']
    communities = [r for r in results if r['classification'] == 'Assisted Living Community']
    manual = [r for r in results if r['classification'] == 'Needs Manual Review']
    
    print(f"\n📊 SMART CLASSIFICATION RESULTS:")
    print(f"   🏠 Homes: {len(homes)} ({len(homes)/len(results)*100:.1f}%)")
    print(f"   🏢 Communities: {len(communities)} ({len(communities)/len(results)*100:.1f}%)")
    print(f"   ❓ Manual Review: {len(manual)} ({len(manual)/len(results)*100:.1f}%)")
    
    # Show high-confidence results
    high_conf_homes = [h for h in homes if h['confidence'] == 'High']
    high_conf_communities = [c for c in communities if c['confidence'] == 'High']
    
    print(f"\n🎯 HIGH CONFIDENCE CLASSIFICATIONS:")
    print(f"   🏠 High confidence homes: {len(high_conf_homes)}")
    print(f"   🏢 High confidence communities: {len(high_conf_communities)}")
    
    # Save results
    with open('smart_classification_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return results

if __name__ == "__main__":
    asyncio.run(run_smart_classification_sample())
