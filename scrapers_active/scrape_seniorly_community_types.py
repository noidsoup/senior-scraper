#!/usr/bin/env python3
"""
Scrape Seniorly detail pages to extract community information for better home vs community classification.

This scraper will visit each Seniorly listing page and extract:
1. Number of units/beds/capacity
2. Community type indicators (apartment-style, house-style, etc.)
3. Facility size indicators
4. Any explicit home vs community language

Based on this data, we can better classify listings as:
- Assisted Living Home (≤10 beds, house-style)
- Assisted Living Community (>10 beds, apartment-style, multiple buildings)
"""

import asyncio
import pandas as pd
import aiohttp
from bs4 import BeautifulSoup
import re
import json
import time
from urllib.parse import urljoin, urlparse
import sys
from pathlib import Path

class SeniorlyCommunityScraper:
    def __init__(self):
        self.session = None
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
    async def create_session(self):
        """Create aiohttp session with proper settings"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=connector
        )
    
    async def close_session(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
    
    def extract_capacity_info(self, soup, url):
        """Extract capacity, size, and type information from the page"""
        info = {
            'url': url,
            'capacity_beds': None,
            'capacity_units': None,
            'capacity_residents': None,
            'facility_type_indicators': [],
            'size_indicators': [],
            'community_vs_home_indicators': [],
            'raw_capacity_text': '',
            'page_title': '',
            'description_snippet': ''
        }
        
        # Get page title
        title_tag = soup.find('title')
        if title_tag:
            info['page_title'] = title_tag.get_text(strip=True)
        
        # Look for capacity information in various sections
        capacity_patterns = [
            r'(\d+)\s*bed[s]?',
            r'(\d+)\s*unit[s]?',
            r'(\d+)\s*resident[s]?',
            r'capacity[:\s]*(\d+)',
            r'accommodate[s]?\s*(\d+)',
            r'up\s*to\s*(\d+)',
            r'(\d+)\s*people',
            r'(\d+)\s*seniors?'
        ]
        
        # Search in various content areas
        content_areas = [
            soup.find('div', class_=re.compile(r'about|description|overview', re.I)),
            soup.find('section', class_=re.compile(r'details|info|about', re.I)),
            soup.find('div', class_=re.compile(r'content|main', re.I)),
            soup.find('article'),
            soup.find('main'),
        ]
        
        # Also check all text content
        all_text = soup.get_text()
        info['raw_capacity_text'] = all_text[:1000]  # First 1000 chars for analysis
        
        # Extract numbers from text
        for pattern in capacity_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                numbers = [int(m) for m in matches if m.isdigit()]
                if 'bed' in pattern:
                    info['capacity_beds'] = max(numbers) if numbers else None
                elif 'unit' in pattern:
                    info['capacity_units'] = max(numbers) if numbers else None
                elif 'resident' in pattern:
                    info['capacity_residents'] = max(numbers) if numbers else None
        
        # Look for facility type indicators
        type_indicators = [
            'apartment', 'apartments', 'apartment-style',
            'house', 'home-style', 'residential home',
            'campus', 'community', 'facility', 'center',
            'single-family', 'multi-story', 'building', 'buildings'
        ]
        
        for indicator in type_indicators:
            if re.search(r'\b' + re.escape(indicator) + r'\b', all_text, re.IGNORECASE):
                info['facility_type_indicators'].append(indicator)
        
        # Look for size indicators
        size_indicators = [
            'small', 'intimate', 'boutique', 'cozy',
            'large', 'spacious', 'extensive', 'comprehensive',
            'private', 'shared', 'semi-private'
        ]
        
        for indicator in size_indicators:
            if re.search(r'\b' + re.escape(indicator) + r'\b', all_text, re.IGNORECASE):
                info['size_indicators'].append(indicator)
        
        # Look for explicit community vs home language
        community_indicators = [
            'assisted living community',
            'senior living community', 
            'retirement community',
            'care community'
        ]
        
        home_indicators = [
            'assisted living home',
            'care home',
            'adult care home',
            'residential care home',
            'board and care'
        ]
        
        for indicator in community_indicators:
            if re.search(re.escape(indicator), all_text, re.IGNORECASE):
                info['community_vs_home_indicators'].append(f"COMMUNITY: {indicator}")
        
        for indicator in home_indicators:
            if re.search(re.escape(indicator), all_text, re.IGNORECASE):
                info['community_vs_home_indicators'].append(f"HOME: {indicator}")
        
        # Get description snippet
        desc_elem = soup.find('meta', {'name': 'description'}) or soup.find('p')
        if desc_elem:
            if desc_elem.name == 'meta':
                info['description_snippet'] = desc_elem.get('content', '')[:200]
            else:
                info['description_snippet'] = desc_elem.get_text(strip=True)[:200]
        
        return info
    
    async def scrape_listing(self, url, title="", retry_count=0):
        """Scrape a single Seniorly listing page"""
        if retry_count > 2:
            print(f"❌ Max retries exceeded for {title}")
            return None
            
        try:
            print(f"🔍 Scraping: {title[:40]:<40} | {url}")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    print(f"⚠️  HTTP {response.status} for {title}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract information
                info = self.extract_capacity_info(soup, url)
                info['scraped_title'] = title
                info['http_status'] = response.status
                
                return info
                
        except asyncio.TimeoutError:
            print(f"⏱️  Timeout for {title}, retrying...")
            await asyncio.sleep(2)
            return await self.scrape_listing(url, title, retry_count + 1)
            
        except Exception as e:
            print(f"❌ Error scraping {title}: {str(e)}")
            return None
    
    async def scrape_batch(self, urls_and_titles, batch_size=5):
        """Scrape a batch of listings with rate limiting"""
        results = []
        
        for i in range(0, len(urls_and_titles), batch_size):
            batch = urls_and_titles[i:i + batch_size]
            print(f"\n📦 Processing batch {i//batch_size + 1} ({len(batch)} listings)")
            
            # Create tasks for this batch
            tasks = []
            for url, title in batch:
                task = self.scrape_listing(url, title)
                tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"❌ Exception in batch: {result}")
                elif result:
                    results.append(result)
            
            # Rate limiting between batches
            if i + batch_size < len(urls_and_titles):
                print(f"⏱️  Waiting 3 seconds before next batch...")
                await asyncio.sleep(3)
        
        return results
    
    def analyze_results(self, results):
        """Analyze scraped results to suggest home vs community classifications"""
        print(f"\n📊 ANALYSIS OF {len(results)} SCRAPED LISTINGS")
        print("=" * 60)
        
        home_candidates = []
        community_candidates = []
        unclear = []
        
        for result in results:
            score = 0  # Positive = community, negative = home
            reasons = []
            
            # Capacity-based scoring
            beds = result.get('capacity_beds')
            units = result.get('capacity_units') 
            residents = result.get('capacity_residents')
            
            max_capacity = max(filter(None, [beds, units, residents]), default=0)
            
            if max_capacity > 20:
                score += 3
                reasons.append(f"Large capacity: {max_capacity}")
            elif max_capacity > 10:
                score += 1
                reasons.append(f"Medium capacity: {max_capacity}")
            elif max_capacity > 0 and max_capacity <= 6:
                score -= 2
                reasons.append(f"Small capacity: {max_capacity}")
            
            # Type indicators
            type_indicators = result.get('facility_type_indicators', [])
            if any(word in type_indicators for word in ['apartment', 'campus', 'facility', 'center']):
                score += 2
                reasons.append("Community-style indicators")
            if any(word in type_indicators for word in ['house', 'home-style', 'residential']):
                score -= 2
                reasons.append("Home-style indicators")
            
            # Explicit language
            explicit = result.get('community_vs_home_indicators', [])
            community_explicit = [x for x in explicit if x.startswith('COMMUNITY:')]
            home_explicit = [x for x in explicit if x.startswith('HOME:')]
            
            if community_explicit:
                score += 3
                reasons.append("Explicit community language")
            if home_explicit:
                score -= 3
                reasons.append("Explicit home language")
            
            # Classification
            result['classification_score'] = score
            result['classification_reasons'] = reasons
            
            if score >= 2:
                result['suggested_classification'] = 'Assisted Living Community'
                community_candidates.append(result)
            elif score <= -2:
                result['suggested_classification'] = 'Assisted Living Home'
                home_candidates.append(result)
            else:
                result['suggested_classification'] = 'Needs Manual Review'
                unclear.append(result)
        
        print(f"🏠 HOME candidates: {len(home_candidates)}")
        print(f"🏢 COMMUNITY candidates: {len(community_candidates)}")
        print(f"❓ UNCLEAR (needs manual review): {len(unclear)}")
        
        return {
            'home_candidates': home_candidates,
            'community_candidates': community_candidates,
            'unclear': unclear,
            'all_results': results
        }

async def main():
    # Load the CSV with Seniorly listings
    csv_file = 'seniorly_listings_for_scraping.csv'
    if not Path(csv_file).exists():
        print(f"❌ File not found: {csv_file}")
        print("Run create_seniorly_analysis.py first to generate the input file.")
        return
    
    df = pd.read_csv(csv_file)
    print(f"📊 Loaded {len(df)} Seniorly listings for scraping")
    
    # For testing, start with a small sample
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    sample_df = df.head(sample_size)
    
    print(f"🧪 Testing with {len(sample_df)} listings (use argument to change sample size)")
    
    # Prepare URLs and titles
    urls_and_titles = [
        (row['seniorly_url_final'], row['Title']) 
        for _, row in sample_df.iterrows()
    ]
    
    # Create scraper and run
    scraper = SeniorlyCommunityScraper()
    await scraper.create_session()
    
    try:
        results = await scraper.scrape_batch(urls_and_titles, batch_size=3)
        analysis = scraper.analyze_results(results)
        
        # Save results
        output_file = f'seniorly_scraping_results_sample_{sample_size}.json'
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Show some examples
        print(f"\n🏠 HOME EXAMPLES:")
        for result in analysis['home_candidates'][:3]:
            print(f"  {result['scraped_title'][:40]:<40} | Score: {result['classification_score']:+2d} | {', '.join(result['classification_reasons'])}")
        
        print(f"\n🏢 COMMUNITY EXAMPLES:")
        for result in analysis['community_candidates'][:3]:
            print(f"  {result['scraped_title'][:40]:<40} | Score: {result['classification_score']:+2d} | {', '.join(result['classification_reasons'])}")
            
    finally:
        await scraper.close_session()

if __name__ == "__main__":
    asyncio.run(main())
