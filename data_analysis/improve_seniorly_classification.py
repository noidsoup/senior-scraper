#!/usr/bin/env python3
"""
Improved classification algorithm for Seniorly listings based on title analysis 
and capacity information extraction.

Since Seniorly uses generic page templates, we need to focus on:
1. The actual listing titles (which are more reliable indicators)
2. Specific capacity numbers when available
3. Known patterns from Arizona assisted living licensing

Key insights:
- "Adult Care Home" in title = likely home (≤10 residents)
- "Care Home" in title = likely home
- "Assisted Living" without "Home" = likely community
- Numbers in capacity extraction
"""

import pandas as pd
import json
import re
import sys
from pathlib import Path

class SeniorlyClassificationImprover:
    def __init__(self):
        self.home_title_indicators = [
            'adult care home',
            'care home', 
            'residential care',
            'board and care',
            'family care',
            'loving care',
            'tender care'
        ]
        
        self.community_title_indicators = [
            'senior living',
            'retirement community',
            'assisted living community',
            'senior community',
            'living center',
            'senior center',
            'manor',
            'village',
            'gardens',
            'plaza',
            'place',
            'heights',
            'ridge',
            'terrace'
        ]
        
        # Known large communities that might be mislabeled
        self.known_large_communities = [
            'abbington', 'acoya', 'aegis', 'belmont village', 
            'brookdale', 'sunrise', 'atria', 'merrill gardens'
        ]

    def classify_by_title(self, title):
        """
        Classify based on title analysis - more reliable than page content
        """
        title_lower = title.lower()
        score = 0
        reasons = []
        
        # Strong home indicators in title
        for indicator in self.home_title_indicators:
            if indicator in title_lower:
                score -= 3
                reasons.append(f"Title contains '{indicator}' (strong home indicator)")
        
        # Community indicators in title
        for indicator in self.community_title_indicators:
            if indicator in title_lower:
                score += 2
                reasons.append(f"Title contains '{indicator}' (community indicator)")
        
        # Known large community brands
        for brand in self.known_large_communities:
            if brand in title_lower:
                score += 3
                reasons.append(f"Known large community brand: {brand}")
        
        # Generic "assisted living" without "home" suggests community
        if 'assisted living' in title_lower and 'home' not in title_lower:
            score += 1
            reasons.append("Generic 'assisted living' without 'home'")
        
        # Numbers in title that might indicate size
        numbers = re.findall(r'\d+', title)
        if numbers:
            # Street addresses don't count, but unit numbers might
            large_numbers = [int(n) for n in numbers if int(n) > 50]
            if large_numbers:
                score += 1
                reasons.append(f"Large numbers in title: {large_numbers}")
        
        return score, reasons
    
    def classify_by_scraped_data(self, scraped_result):
        """
        Classify based on scraped capacity data
        """
        score = 0
        reasons = []
        
        # Get capacity numbers
        beds = scraped_result.get('capacity_beds')
        units = scraped_result.get('capacity_units')
        residents = scraped_result.get('capacity_residents')
        
        capacities = [c for c in [beds, units, residents] if c is not None]
        
        if capacities:
            max_capacity = max(capacities)
            
            if max_capacity <= 6:
                score -= 3
                reasons.append(f"Small capacity: {max_capacity} (strong home indicator)")
            elif max_capacity <= 10:
                score -= 1
                reasons.append(f"Small-medium capacity: {max_capacity} (home indicator)")
            elif max_capacity <= 20:
                score += 1
                reasons.append(f"Medium capacity: {max_capacity} (community indicator)")
            else:
                score += 3
                reasons.append(f"Large capacity: {max_capacity} (strong community indicator)")
        
        return score, reasons
    
    def final_classification(self, title, scraped_result=None):
        """
        Final classification combining title and scraped data
        """
        title_score, title_reasons = self.classify_by_title(title)
        
        scraped_score = 0
        scraped_reasons = []
        if scraped_result:
            scraped_score, scraped_reasons = self.classify_by_scraped_data(scraped_result)
        
        total_score = title_score + scraped_score
        all_reasons = title_reasons + scraped_reasons
        
        # Classification thresholds
        if total_score <= -2:
            classification = "Assisted Living Home"
            confidence = "High" if total_score <= -4 else "Medium"
        elif total_score >= 2:
            classification = "Assisted Living Community"  
            confidence = "High" if total_score >= 4 else "Medium"
        else:
            classification = "Needs Manual Review"
            confidence = "Low"
        
        return {
            'classification': classification,
            'confidence': confidence,
            'score': total_score,
            'title_score': title_score,
            'scraped_score': scraped_score,
            'reasons': all_reasons
        }

def analyze_all_seniorly_listings():
    """
    Analyze all 1,478 Seniorly listings using improved classification
    """
    # Load the original data
    csv_file = 'seniorly_listings_for_scraping.csv'
    if not Path(csv_file).exists():
        print(f"❌ File not found: {csv_file}")
        return
    
    df = pd.read_csv(csv_file)
    classifier = SeniorlyClassificationImprover()
    
    print(f"🔍 IMPROVED CLASSIFICATION OF ALL {len(df)} SENIORLY LISTINGS")
    print("=" * 60)
    
    # Load scraped results if available
    scraped_data = {}
    scraped_file = 'seniorly_scraping_results_sample_25.json'
    if Path(scraped_file).exists():
        with open(scraped_file, 'r') as f:
            scraped_results = json.load(f)
            for result in scraped_results['all_results']:
                scraped_data[result['scraped_title']] = result
        print(f"📊 Using scraped data for {len(scraped_data)} listings")
    
    # Classify all listings
    results = []
    home_count = 0
    community_count = 0
    manual_review_count = 0
    
    for _, row in df.iterrows():
        title = row['Title']
        scraped_result = scraped_data.get(title)
        
        classification_result = classifier.final_classification(title, scraped_result)
        
        result = {
            'ID': row['ID'],
            'Title': title,
            'URL': row['seniorly_url_final'],
            'Current_Type': row['type'],
            'State': row['States'],
            'Location': row['Locations'],
            **classification_result
        }
        
        results.append(result)
        
        if classification_result['classification'] == 'Assisted Living Home':
            home_count += 1
        elif classification_result['classification'] == 'Assisted Living Community':
            community_count += 1
        else:
            manual_review_count += 1
    
    # Summary
    print(f"\n📊 CLASSIFICATION RESULTS:")
    print(f"🏠 Assisted Living Home: {home_count} ({home_count/len(results)*100:.1f}%)")
    print(f"🏢 Assisted Living Community: {community_count} ({community_count/len(results)*100:.1f}%)")
    print(f"❓ Needs Manual Review: {manual_review_count} ({manual_review_count/len(results)*100:.1f}%)")
    
    # Show examples
    homes = [r for r in results if r['classification'] == 'Assisted Living Home']
    communities = [r for r in results if r['classification'] == 'Assisted Living Community']
    
    print(f"\n🏠 HOME EXAMPLES (High Confidence):")
    high_conf_homes = [h for h in homes if h['confidence'] == 'High']
    for home in high_conf_homes[:10]:
        print(f"  {home['Title'][:50]:<50} | Score: {home['score']:+2d} | {', '.join(home['reasons'][:2])}")
    
    print(f"\n🏢 COMMUNITY EXAMPLES (High Confidence):")
    high_conf_communities = [c for c in communities if c['confidence'] == 'High']
    for community in high_conf_communities[:10]:
        print(f"  {community['Title'][:50]:<50} | Score: {community['score']:+2d} | {', '.join(community['reasons'][:2])}")
    
    # Export results
    results_df = pd.DataFrame(results)
    
    # Export homes for review
    homes_df = results_df[results_df['classification'] == 'Assisted Living Home']
    homes_df.to_csv('seniorly_classified_as_HOMES.csv', index=False)
    
    # Export communities for review  
    communities_df = results_df[results_df['classification'] == 'Assisted Living Community']
    communities_df.to_csv('seniorly_classified_as_COMMUNITIES.csv', index=False)
    
    # Export manual review cases
    manual_df = results_df[results_df['classification'] == 'Needs Manual Review']
    manual_df.to_csv('seniorly_needs_MANUAL_REVIEW.csv', index=False)
    
    print(f"\n💾 EXPORTS COMPLETE:")
    print(f"  seniorly_classified_as_HOMES.csv ({len(homes_df)} listings)")
    print(f"  seniorly_classified_as_COMMUNITIES.csv ({len(communities_df)} listings)")
    print(f"  seniorly_needs_MANUAL_REVIEW.csv ({len(manual_df)} listings)")
    
    print(f"\n🎯 NEXT STEPS:")
    print(f"1. Review the HIGH CONFIDENCE classifications above")
    print(f"2. Spot-check some of the exported files")
    print(f"3. Create WordPress import CSV with corrected classifications")
    print(f"4. Import the corrections to fix the historical mislabeling")

if __name__ == "__main__":
    analyze_all_seniorly_listings()
