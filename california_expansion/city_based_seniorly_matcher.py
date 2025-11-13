#!/usr/bin/env python3
"""
City-Based Seniorly Matcher for California Listings
Searches Seniorly by city, then matches facilities within city results
"""

import asyncio
import csv
import re
from typing import Optional, Dict, List, Tuple
from playwright.async_api import async_playwright
from datetime import datetime
from urllib.parse import quote_plus
from collections import defaultdict
from pathlib import Path

class CityBasedSeniorlyMatcher:
    def __init__(self):
        self.matched_count = 0
        self.unmatched_count = 0
        self.processed_count = 0
        self.city_cache = {}  # Cache city results to avoid re-scraping
        
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
    
    def parse_address_components(self, address: str) -> dict:
        """Parse address into components: street, city, state, zip"""
        if not address:
            return {}
        
        # Split by comma to get main parts
        parts = [p.strip() for p in address.split(',')]
        
        result = {}
        if len(parts) >= 3:
            result['street'] = parts[0].lower().strip()
            result['city'] = parts[1].lower().strip()
            state_zip = parts[2].lower().strip()
            
            # Split state and zip
            state_zip_parts = state_zip.split()
            if len(state_zip_parts) >= 2:
                result['state'] = state_zip_parts[0]
                result['zip'] = state_zip_parts[1]
            else:
                result['state'] = state_zip
                result['zip'] = ''
        
        return result
    
    def calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate precise address similarity with component matching"""
        if not addr1 or not addr2:
            return 0.0
        
        comp1 = self.parse_address_components(addr1)
        comp2 = self.parse_address_components(addr2)
        
        if not comp1 or not comp2:
            return 0.0
        
        # Check exact matches for critical components first
        city_match = comp1.get('city', '') == comp2.get('city', '')
        state_match = comp1.get('state', '') == comp2.get('state', '')
        zip_match = comp1.get('zip', '') == comp2.get('zip', '')
        
        # If city, state, or zip don't match, it's not the same address
        if not city_match or not state_match:
            return 0.0
        
        # If zip codes exist and don't match, it's not the same address
        if comp1.get('zip') and comp2.get('zip') and not zip_match:
            return 0.0
        
        # Now check street address similarity
        street1 = comp1.get('street', '')
        street2 = comp2.get('street', '')
        
        if not street1 or not street2:
            return 0.0
        
        # Normalize street addresses
        street1_norm = self.normalize_address(street1)
        street2_norm = self.normalize_address(street2)
        
        # Calculate street similarity
        words1 = set(street1_norm.split())
        words2 = set(street2_norm.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        street_similarity = len(intersection) / len(union) if union else 0.0
        
        # Street similarity must be high (0.7+) for a match
        if street_similarity < 0.7:
            return 0.0
        
        # Return high score for exact city/state/zip + good street match
        return 0.8 + (street_similarity * 0.2)  # 0.8-1.0 range
    
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
    
    async def scrape_city_facilities(self, page, city: str, state: str) -> List[Dict]:
        """Scrape all facilities from a Seniorly city page (all care types)"""
        try:
            city_slug = city.lower().replace(' ', '-')
            
            print(f"    🏙️  Scraping {city}, {state}...")
            
            facilities = []
            seen_urls = set()  # Track unique facilities
            
            # Check ALL care type pages from Seniorly footer
            care_types = [
                'assisted-living',
                'independent-living',
                'board-and-care-homes',
                'memory-care',
                'home-care',
                'respite-care',
                'active-adult',
                'continuing-care-retirement-communities',
                'nursing-homes'
            ]
            
            for care_type in care_types:
                # Paginate through all pages for this care type
                page_num = 1
                while True:
                    city_url = f"https://www.seniorly.com/{care_type}/{state.lower()}/{city_slug}"
                    if page_num > 1:
                        city_url += f"?page={page_num}"
                    
                    try:
                        await page.goto(city_url, timeout=30000)
                        await page.wait_for_timeout(2000)
                    except Exception as e:
                        # City might not have this care type, skip it
                        break
                    
                    # Look for article tags (these contain facility cards)
                    articles = await page.query_selector_all('article')
                    
                    for article in articles:
                        try:
                            # Get all text from the article
                            text = await article.inner_text()
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            
                            if len(lines) < 2:
                                continue
                            
                            # Parse the text content
                            # Format is typically:
                            # Line 0: "Verified" or similar badge
                            # Line 1: Facility Name
                            # Line 2: Street Address, City, State Zip
                            # Line 3: Care Types
                            # Line N: Pricing (contains "From $")
                            
                            found_title = ""
                            found_address = ""
                            pricing = ""
                            care_type = ""
                            url = ""
                            
                            # Find title (first substantial line that's not "Verified")
                            for line in lines:
                                if line and len(line) > 5 and line not in ['Verified', 'See details']:
                                    found_title = line
                                    break
                            
                            # Find address (line with street indicators and state)
                            for line in lines:
                                if any(word in line.lower() for word in ['street', 'avenue', 'drive', 'road', 'boulevard', 'st ', ' st,', 'ave ', ' ave,', 'dr ', ' dr,', 'blvd']) and ' CA ' in line:
                                    found_address = line
                                    break
                            
                            # Find pricing (line with "From $")
                            for line in lines:
                                if 'From $' in line or line.startswith('$'):
                                    pricing = line.replace('From ', '').strip()
                                    break
                            
                            # Find care types (line with Assisted Living, Memory Care, etc.)
                            for line in lines:
                                if any(care in line for care in ['Assisted Living', 'Memory Care', 'Independent Living', 'Board and Care']):
                                    care_type = line
                                    break
                            
                            # Extract URL from link
                            link = await article.query_selector('a[href*="/assisted-living/"], a[href*="/memory-care/"], a[href*="/independent-living/"], a[href*="/board-and-care-homes/"]')
                            if link:
                                url = await link.get_attribute('href')
                                if url and not url.startswith('http'):
                                    url = f"https://www.seniorly.com{url}"
                            
                            # Only add if we have title and URL, and haven't seen this facility
                            if found_title and url and url not in seen_urls:
                                seen_urls.add(url)
                                facilities.append({
                                    'title': found_title,
                                    'address': found_address if found_address else f"{city}, {state}",
                                    'url': url,
                                    'pricing': pricing,
                                    'care_type': care_type,
                                    'city': city,
                                    'state': state
                                })
                        
                        except Exception as e:
                            continue
                    
                    # Check if there are more pages
                    next_button = await page.query_selector('button:has-text("Next"), a:has-text("Next"), [aria-label*="next"]')
                    if not next_button or not await next_button.is_visible():
                        # No more pages
                        break
                    
                    page_num += 1
            
            print(f"    ✅ Found {len(facilities)} facilities in {city}")
            return facilities
            
        except Exception as e:
            print(f"    ❌ Error scraping {city}: {e}")
            return []
    
    async def get_city_facilities(self, page, city: str, state: str) -> List[Dict]:
        """Get facilities for a city (with caching)"""
        cache_key = f"{city},{state}".lower()
        
        if cache_key in self.city_cache:
            print(f"    📋 Using cached data for {city}, {state}")
            return self.city_cache[cache_key]
        
        facilities = await self.scrape_city_facilities(page, city, state)
        self.city_cache[cache_key] = facilities
        return facilities
    
    async def find_best_match(self, page, sp_title: str, sp_address: str, sp_city: str, sp_state: str) -> Optional[Dict]:
        """Find the best matching Seniorly listing"""
        try:
            # Get all facilities for this city
            city_facilities = await self.get_city_facilities(page, sp_city, sp_state)
            
            if not city_facilities:
                return None
            
            best_match = None
            best_score = 0.0
            
            # Debug: show first few facilities
            print(f"    🔍 Checking {len(city_facilities)} facilities...")
            for i, facility in enumerate(city_facilities[:3]):  # Show first 3 for debugging
                print(f"      {i+1}. {facility['title'][:40]} | {facility['address'][:40]}")
            
            for facility in city_facilities:
                # Calculate address similarity (primary)
                addr_similarity = self.calculate_address_similarity(sp_address, facility['address'])
                
                # Calculate name similarity (secondary)
                name_similarity = self.calculate_name_similarity(sp_title, facility['title'])
                
                # Combined score: 70% address, 30% name
                combined_score = (addr_similarity * 0.7) + (name_similarity * 0.3)
                
                # Debug: show scores for first few
                if len([f for f in city_facilities if city_facilities.index(f) < 3]) > 0 and city_facilities.index(facility) < 3:
                    print(f"      Scores: addr={addr_similarity:.2f}, name={name_similarity:.2f}, combined={combined_score:.2f}")
                
                # Require minimum thresholds - very high for accuracy
                if addr_similarity >= 0.8 and combined_score > best_score:  # Very high address threshold for accuracy
                    best_score = combined_score
                    best_match = facility
                    best_match['address_similarity'] = addr_similarity
                    best_match['name_similarity'] = name_similarity
                    best_match['combined_score'] = combined_score
            
            return best_match if best_score >= 0.8 else None  # Very high minimum score for accuracy
            
        except Exception as e:
            print(f"    ❌ Matching error: {e}")
            return None
    
    async def process_listings(self, input_file: str, output_file: str, sample_size: int = None):
        """Process California listings and find Seniorly matches"""
        import sys
        print("🔍 CITY-BASED SENIORLY MATCHING", flush=True)
        print("=" * 60, flush=True)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(flush=True)
        
        # Load listings
        listings = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            listings = list(reader)
        
        if sample_size:
            listings = listings[:sample_size]
        
        print(f"📊 Processing {len(listings)} listings", flush=True)
        
        # Load from checkpoint if it exists
        checkpoint_file = f"{output_file}.checkpoint"
        processed_urls = set()
        if Path(checkpoint_file).exists():
            print(f"🔄 Resuming from checkpoint: {checkpoint_file}")
            with open(checkpoint_file, 'r', encoding='utf-8') as cf:
                reader = csv.DictReader(cf)
                checkpoint_data = list(reader)
                for row in checkpoint_data:
                    processed_urls.add(row.get('url', ''))
                    # Update the listing with checkpoint data
                    for listing in listings:
                        if listing.get('url') == row.get('url'):
                            listing.update(row)
                            break
            print(f"   📊 Loaded {len(processed_urls)} already processed listings")
        
        print()
        
        # Group by city for efficiency
        city_groups = defaultdict(list)
        for listing in listings:
            city = listing.get('location-name', '')  # Use location-name field
            city_groups[city].append(listing)
        
        print(f"🏙️  Found {len(city_groups)} unique cities", flush=True)
        print(flush=True)
        
        print("🌐 Launching browser...", flush=True)
        # Process with Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            print("✅ Browser launched", flush=True)
            
            for city, city_listings in city_groups.items():
                if not city:
                    continue
                
                print(f"🏙️  Processing {city} ({len(city_listings)} listings)")
                
                for i, listing in enumerate(city_listings):
                    title = listing.get('title', '')
                    address = listing.get('address', '')
                    state = listing.get('state', '')
                    city = listing.get('location-name', '')  # Use location-name field
                    listing_url = listing.get('url', '')
                    
                    # Skip if already processed
                    if listing_url in processed_urls:
                        print(f"  ⏭️  {i+1:3d}/{len(city_listings)} - {title[:40]:<40} (skipped - already processed)")
                        continue
                    
                    print(f"  🔍 {i+1:3d}/{len(city_listings)} - {title[:40]:<40}", end=" ")
                    
                    # Find match
                    match = await self.find_best_match(page, title, address, city, state)
                    
                    if match:
                        # Add Seniorly data to listing
                        listing['seniorly_url'] = match['url']
                        listing['seniorly_title'] = match['title']
                        listing['seniorly_address'] = match['address']
                        listing['seniorly_pricing'] = match['pricing']
                        listing['seniorly_care_type'] = match['care_type']
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
                        listing['seniorly_care_type'] = ''
                        listing['address_similarity'] = ''
                        listing['name_similarity'] = ''
                        listing['combined_score'] = ''
                        
                        self.unmatched_count += 1
                        print("❌")
                    
                    self.processed_count += 1
                    processed_urls.add(listing_url)
                    
                    # Small delay to be respectful
                    await asyncio.sleep(0.3)
                    
                    # Save checkpoint every 50 listings
                    if self.processed_count % 50 == 0:
                        print(f"\n  💾 Saving checkpoint at {self.processed_count} listings...")
                        fieldnames = list(listings[0].keys()) if listings else []
                        with open(checkpoint_file, 'w', newline='', encoding='utf-8') as cf:
                            writer = csv.DictWriter(cf, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(listings)
                        print(f"  ✅ Checkpoint saved")
                
                print(f"  📊 {city} complete: {self.matched_count} total matches so far")
                print()
            
            await browser.close()
        
        # Write results
        fieldnames = list(listings[0].keys()) if listings else []
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(listings)
        
        print("🎉 MATCHING COMPLETE!")
        print("=" * 60)
        print(f"✅ Successfully matched: {self.matched_count} listings")
        print(f"❌ Failed to match: {self.unmatched_count} listings")
        print(f"📊 Match rate: {(self.matched_count/self.processed_count)*100:.1f}%")
        print(f"📄 Output file: {output_file}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Match California listings with Seniorly using city-based approach")
    parser.add_argument('--input', default='california_seniorplace_data_DEDUPED.csv', help='Input CSV file')
    parser.add_argument('--output', default='california_seniorplace_data_with_seniorly_matches.csv', help='Output CSV file')
    parser.add_argument('--sample', type=int, help='Process only first N listings for testing')
    
    args = parser.parse_args()
    
    matcher = CityBasedSeniorlyMatcher()
    await matcher.process_listings(args.input, args.output, args.sample)

if __name__ == "__main__":
    asyncio.run(main())
