#!/usr/bin/env python3
"""
Targeted Seniorly classifier based on their actual category system.

From Seniorly's own documentation:
- "Board and Care Home" = smaller, intimate single family homes  
- "Assisted Living" (without "Board and Care") = larger, hotel-like properties

This is the key distinction we should be looking for!
"""

import asyncio
import pandas as pd
import aiohttp
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path

class TargetedSeniorlyClassifier:
    def __init__(self):
        # Based on Seniorly's own definitions
        self.definite_home_indicators = [
            r'\bboard and care home\b',
            r'\bresidential care home\b', 
            r'\badult care home\b',
            r'\bcare home\b'
        ]
        
        # Title patterns that suggest communities
        self.community_title_patterns = [
            r'\bsenior living\b',
            r'\bassisted living community\b',
            r'\bretirement community\b',
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
        
        # Large community brands
        self.large_brands = [
            'aegis', 'brookdale', 'sunrise', 'atria', 'merrill gardens',
            'belmont village', 'acoya', 'watermark', 'holiday retirement'
        ]

    async def extract_seniorly_care_types(self, session, url):
        """Extract the specific care types listed on Seniorly page"""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                care_info = {
                    'url': url,
                    'care_types_listed': [],
                    'has_board_and_care': False,
                    'has_assisted_living': False,
                    'capacity_numbers': [],
                    'page_structure_clues': []
                }
                
                # Look for the care types section specifically
                # This should be in a section about "Care offered at [Facility Name]"
                care_section = soup.find('section', string=re.compile(r'care offered', re.I))
                if not care_section:
                    # Try other patterns
                    care_section = soup.find('div', class_=re.compile(r'care|service', re.I))
                
                all_text = soup.get_text().lower()
                
                # Look for specific care type mentions
                if 'board and care home' in all_text:
                    care_info['care_types_listed'].append('Board and Care Home')
                    care_info['has_board_and_care'] = True
                
                if 'assisted living' in all_text and 'board and care' not in all_text:
                    care_info['care_types_listed'].append('Assisted Living')
                    care_info['has_assisted_living'] = True
                elif 'assisted living' in all_text and 'board and care' in all_text:
                    # Both are mentioned - need to determine which is primary
                    care_info['care_types_listed'].extend(['Assisted Living', 'Board and Care Home'])
                    care_info['has_assisted_living'] = True
                    care_info['has_board_and_care'] = True
                
                # Look for capacity clues
                capacity_patterns = [
                    r'(\d+)\s*bed[s]?\b',
                    r'(\d+)\s*unit[s]?\b',
                    r'(\d+)\s*resident[s]?\b',
                    r'(\d+)\s*room[s]?\b',
                    r'up\s*to\s*(\d+)',
                    r'accommodate[s]?\s*(\d+)'
                ]
                
                for pattern in capacity_patterns:
                    matches = re.findall(pattern, all_text)
                    for match in matches:
                        num = int(match)
                        if 1 <= num <= 100:  # Reasonable range
                            care_info['capacity_numbers'].append(num)
                
                # Look for structural clues about size
                if re.search(r'\bhotel[- ]?like\b|\blarge\b|\bcampus\b', all_text):
                    care_info['page_structure_clues'].append('large_facility_language')
                
                if re.search(r'\bintimate\b|\bsmall\b|\bhome[- ]?like\b|\bfamily\b', all_text):
                    care_info['page_structure_clues'].append('small_facility_language')
                
                return care_info
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    def classify_with_seniorly_data(self, title, scraped_data=None):
        """Classify using Seniorly's own care type system"""
        score = 0
        reasons = []
        title_lower = title.lower()
        
        # Title-based classification
        for pattern in self.definite_home_indicators:
            if re.search(pattern, title_lower):
                score -= 4
                reasons.append(f"Title: '{pattern}' (strong home indicator)")
        
        for pattern in self.community_title_patterns:
            if re.search(pattern, title_lower):
                score += 3
                reasons.append(f"Title: '{pattern}' (community indicator)")
        
        # Brand recognition
        for brand in self.large_brands:
            if brand in title_lower:
                score += 4
                reasons.append(f"Known large brand: {brand}")
        
        # Use Seniorly's own care type data
        if scraped_data:
            if scraped_data.get('has_board_and_care') and not scraped_data.get('has_assisted_living'):
                score -= 5
                reasons.append("Seniorly lists: Board and Care Home only (strong home indicator)")
            elif scraped_data.get('has_assisted_living') and not scraped_data.get('has_board_and_care'):
                score += 4
                reasons.append("Seniorly lists: Assisted Living only (community indicator)")
            elif scraped_data.get('has_board_and_care') and scraped_data.get('has_assisted_living'):
                # Both listed - use other clues
                reasons.append("Seniorly lists: Both AL and Board & Care (mixed signals)")
            
            # Capacity data
            if scraped_data.get('capacity_numbers'):
                max_capacity = max(scraped_data['capacity_numbers'])
                if max_capacity <= 6:
                    score -= 3
                    reasons.append(f"Small capacity: {max_capacity} (home indicator)")
                elif max_capacity <= 10:
                    score -= 1
                    reasons.append(f"Small-medium capacity: {max_capacity}")
                elif max_capacity >= 50:
                    score += 4
                    reasons.append(f"Large capacity: {max_capacity} (community indicator)")
                elif max_capacity >= 20:
                    score += 2
                    reasons.append(f"Medium-large capacity: {max_capacity}")
            
            # Structural clues
            if 'large_facility_language' in scraped_data.get('page_structure_clues', []):
                score += 2
                reasons.append("Page describes large/hotel-like facility")
            if 'small_facility_language' in scraped_data.get('page_structure_clues', []):
                score -= 2
                reasons.append("Page describes small/intimate/home-like facility")
        
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
            'scraped_data': scraped_data
        }

async def test_targeted_classification():
    """Test the targeted approach on key examples"""
    
    # Test URLs that should show clear distinctions
    test_urls = [
        ("Acacia Cove Assisted Living", "https://www.seniorly.com/assisted-living/arizona/glendale/acacia-cove-assisted-living"),
        ("A I Adult Care Home", "https://www.seniorly.com/assisted-living/arizona/scottsdale/a-i-adult-care-home"),
        ("Brookdale Desert Ridge", "https://www.seniorly.com/assisted-living/arizona/phoenix/brookdale-desert-ridge"),
        ("Belmont Village Senior Living Scottsdale", "https://www.seniorly.com/assisted-living/arizona/scottsdale/belmont-village-senior-living-scottsdale"),
        ("Savanna House", "https://www.seniorly.com/assisted-living/arizona/gilbert/savanna-house")
    ]
    
    classifier = TargetedSeniorlyClassifier()
    
    # Create session
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        print("🎯 TARGETED SENIORLY CLASSIFICATION TEST")
        print("=" * 60)
        print("Looking specifically for Seniorly's own care type distinctions")
        
        results = []
        
        for title, url in test_urls:
            print(f"\n📋 Testing: {title}")
            print(f"   URL: {url}")
            
            # Scrape the page
            scraped_data = await classifier.extract_seniorly_care_types(session, url)
            
            if scraped_data:
                # Classify using targeted algorithm
                result = classifier.classify_with_seniorly_data(title, scraped_data)
                results.append({
                    'title': title,
                    'url': url,
                    **result
                })
                
                print(f"   Classification: {result['classification']} ({result['confidence']} confidence)")
                print(f"   Score: {result['score']}")
                print(f"   Care types found: {scraped_data.get('care_types_listed', [])}")
                if scraped_data.get('capacity_numbers'):
                    print(f"   Capacity: {scraped_data['capacity_numbers']}")
                print(f"   Reasons: {', '.join(result['reasons'])}")
            else:
                print(f"   ❌ Failed to scrape")
            
            # Rate limiting
            await asyncio.sleep(2)
    
    # Save results
    if results:
        with open('targeted_seniorly_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: targeted_seniorly_test_results.json")
        
        # Summary
        homes = [r for r in results if r['classification'] == 'Assisted Living Home']
        communities = [r for r in results if r['classification'] == 'Assisted Living Community']
        
        print(f"\n📊 TARGETED CLASSIFICATION RESULTS:")
        print(f"   🏠 Homes: {len(homes)}")
        print(f"   🏢 Communities: {len(communities)}")
        print(f"   ❓ Manual Review: {len(results) - len(homes) - len(communities)}")

if __name__ == "__main__":
    asyncio.run(test_targeted_classification())
