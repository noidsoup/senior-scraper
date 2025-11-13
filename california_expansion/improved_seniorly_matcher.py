#!/usr/bin/env python3
"""
Improved Seniorly Matcher for California Listings
Uses address as primary matching criteria with fuzzy name matching as secondary
"""

import asyncio
import csv
import re
from typing import Optional, Dict, List, Tuple
from playwright.async_api import async_playwright
from datetime import datetime
from urllib.parse import quote_plus

class ImprovedSeniorlyMatcher:
    def __init__(self):
        self.matched_count = 0
        self.unmatched_count = 0
        self.processed_count = 0
        
    def normalize_address(self, address: str) -> str:
        """Normalize address for matching"""
        if not address:
            return ""
        
        # Convert to lowercase
        address = address.lower().strip()
        
        # Standardize common abbreviations
        replacements = {
            r'\bstreet\b': 'st',
            r'\bavenue\b': 'ave', 
            r'\bboulevard\b': 'blvd',
            r'\bdrive\b': 'dr',
            r'\bplace\b': 'pl',
            r'\bway\b': 'wy',
            r'\bcircle\b': 'cir',
            r'\blane\b': 'ln',
            r'\broad\b': 'rd',
            r'\bunit\b': '#',
            r'\bapartment\b': 'apt',
            r'\bsuite\b': 'ste',
            r'\bnorth\b': 'n',
            r'\bsouth\b': 's', 
            r'\beast\b': 'e',
            r'\bwest\b': 'w',
            r'\bnortheast\b': 'ne',
            r'\bnorthwest\b': 'nw',
            r'\bsoutheast\b': 'se',
            r'\bsouthwest\b': 'sw'
        }
        
        for pattern, replacement in replacements.items():
            address = re.sub(pattern, replacement, address)
        
        # Remove punctuation and extra spaces
        address = re.sub(r'[^\w\s]', ' ', address)
        address = re.sub(r'\s+', ' ', address).strip()
        
        return address
    
    def normalize_name(self, name: str) -> str:
        """Normalize facility name for fuzzy matching"""
        if not name:
            return ""
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove common suffixes
        name = re.sub(r'\b(llc|inc|corporation|corp|ltd|l\.l\.c\.|assisted living|memory care|senior living|retirement home|care home)\b', '', name, flags=re.IGNORECASE)
        
        # Remove punctuation and extra spaces
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between two addresses"""
        if not addr1 or not addr2:
            return 0.0
        
        norm1 = self.normalize_address(addr1)
        norm2 = self.normalize_address(addr2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Split into words
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two facility names"""
        if not name1 or not name2:
            return 0.0
        
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Split into words
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def search_seniorly_by_address(self, page, address: str, city: str, state: str) -> List[Dict]:
        """Search Seniorly by address and return all potential matches"""
        try:
            # Build search query with address
            search_query = f"{address} {city} {state}"
            encoded_query = quote_plus(search_query)
            
            # Seniorly search URL
            search_url = f"https://www.seniorly.com/search?query={encoded_query}"
            
            await page.goto(search_url, timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Look for search result cards
            result_selectors = [
                '.search-result',
                '.listing-card', 
                'article',
                '[data-testid="search-result"]',
                'a[href*="/assisted-living/"]',
                'a[href*="/memory-care/"]',
                'a[href*="/independent-living/"]',
                '.community-card',
                '.facility-card'
            ]
            
            results = []
            for selector in result_selectors:
                elements = await page.query_selector_all(selector)
                
                for element in elements:
                    try:
                        # Extract title
                        title_elem = await element.query_selector('h1, h2, h3, h4, .title, [class*="title"], [class*="name"]')
                        if not title_elem:
                            continue
                        
                        found_title = await title_elem.inner_text()
                        found_title = found_title.strip()
                        
                        # Extract address
                        address_elem = await element.query_selector('.address, [class*="address"], .location, [class*="location"]')
                        found_address = ""
                        if address_elem:
                            found_address = await address_elem.inner_text()
                            found_address = found_address.strip()
                        
                        # Extract URL
                        link = await element.query_selector('a')
                        url = ""
                        if link:
                            url = await link.get_attribute('href')
                            if url and not url.startswith('http'):
                                url = f"https://www.seniorly.com{url}"
                        
                        # Extract pricing if available
                        pricing_elem = await element.query_selector('[class*="price"], [class*="cost"], [class*="rate"]')
                        pricing = ""
                        if pricing_elem:
                            pricing = await pricing_elem.inner_text()
                            pricing = pricing.strip()
                        
                        if found_title and url:
                            results.append({
                                'title': found_title,
                                'address': found_address,
                                'url': url,
                                'pricing': pricing
                            })
                    
                    except Exception as e:
                        continue
            
            return results
            
        except Exception as e:
            print(f"    ❌ Search error: {e}")
            return []
    
    async def find_best_match(self, page, sp_title: str, sp_address: str, sp_city: str, sp_state: str) -> Optional[Dict]:
        """Find the best matching Seniorly listing"""
        try:
            # Search Seniorly
            results = await self.search_seniorly_by_address(page, sp_address, sp_city, sp_state)
            
            if not results:
                return None
            
            best_match = None
            best_score = 0.0
            
            for result in results:
                # Calculate address similarity (primary)
                addr_similarity = self.calculate_address_similarity(sp_address, result['address'])
                
                # Calculate name similarity (secondary)
                name_similarity = self.calculate_name_similarity(sp_title, result['title'])
                
                # Combined score: 70% address, 30% name
                combined_score = (addr_similarity * 0.7) + (name_similarity * 0.3)
                
                # Require minimum thresholds
                if addr_similarity >= 0.3 and combined_score > best_score:  # Address must be at least 30% similar
                    best_score = combined_score
                    best_match = result
                    best_match['address_similarity'] = addr_similarity
                    best_match['name_similarity'] = name_similarity
                    best_match['combined_score'] = combined_score
            
            return best_match if best_score >= 0.4 else None  # Minimum 40% combined score
            
        except Exception as e:
            print(f"    ❌ Matching error: {e}")
            return None
    
    async def process_listings(self, input_file: str, output_file: str, sample_size: int = None):
        """Process California listings and find Seniorly matches"""
        print("🔍 IMPROVED SENIORLY MATCHING")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Load listings
        listings = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            listings = list(reader)
        
        if sample_size:
            listings = listings[:sample_size]
        
        print(f"📊 Processing {len(listings)} listings")
        print()
        
        # Process with Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            for i, listing in enumerate(listings):
                title = listing.get('title', '')
                address = listing.get('address', '')
                city = listing.get('city', '')
                state = listing.get('state', '')
                
                print(f"🔍 {i+1:4d}/{len(listings)} - {title[:50]:<50}", end=" ")
                
                # Find match
                match = await self.find_best_match(page, title, address, city, state)
                
                if match:
                    # Add Seniorly data to listing
                    listing['seniorly_url'] = match['url']
                    listing['seniorly_title'] = match['title']
                    listing['seniorly_address'] = match['address']
                    listing['seniorly_pricing'] = match['pricing']
                    listing['address_similarity'] = f"{match['address_similarity']:.2f}"
                    listing['name_similarity'] = f"{match['name_similarity']:.2f}"
                    listing['combined_score'] = f"{match['combined_score']:.2f}"
                    
                    self.matched_count += 1
                    print(f"✅ (addr:{match['address_similarity']:.2f}, name:{match['name_similarity']:.2f})")
                else:
                    listing['seniorly_url'] = ''
                    listing['seniorly_title'] = ''
                    listing['seniorly_address'] = ''
                    listing['seniorly_pricing'] = ''
                    listing['address_similarity'] = ''
                    listing['name_similarity'] = ''
                    listing['combined_score'] = ''
                    
                    self.unmatched_count += 1
                    print("❌")
                
                self.processed_count += 1
                
                # Small delay to be respectful
                await asyncio.sleep(0.5)
                
                # Progress update every 25 listings
                if (i + 1) % 25 == 0:
                    print(f"   📊 Progress: {self.matched_count} matched, {self.unmatched_count} unmatched")
            
            await browser.close()
        
        # Write results
        fieldnames = list(listings[0].keys()) if listings else []
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(listings)
        
        print()
        print("🎉 MATCHING COMPLETE!")
        print("=" * 60)
        print(f"✅ Successfully matched: {self.matched_count} listings")
        print(f"❌ Failed to match: {self.unmatched_count} listings")
        print(f"📊 Match rate: {(self.matched_count/self.processed_count)*100:.1f}%")
        print(f"📄 Output file: {output_file}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Match California listings with Seniorly")
    parser.add_argument('--input', default='california_seniorplace_data_DEDUPED.csv', help='Input CSV file')
    parser.add_argument('--output', default='california_seniorplace_data_with_seniorly_matches.csv', help='Output CSV file')
    parser.add_argument('--sample', type=int, help='Process only first N listings for testing')
    
    args = parser.parse_args()
    
    matcher = ImprovedSeniorlyMatcher()
    await matcher.process_listings(args.input, args.output, args.sample)

if __name__ == "__main__":
    asyncio.run(main())
