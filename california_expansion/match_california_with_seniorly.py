#!/usr/bin/env python3
"""
Match California Senior Place listings with Seniorly.com
Searches Seniorly for each California facility to find matching listings and extract better content
"""

import asyncio
import csv
import re
from typing import Optional, Dict, List
from playwright.async_api import async_playwright
from datetime import datetime
from urllib.parse import quote_plus

class CaliforniaSeniorlyMatcher:
    def __init__(self):
        self.matched_count = 0
        self.unmatched_count = 0
        self.processed_count = 0
        
    def clean_title_for_search(self, title: str) -> str:
        """Clean title for better search results"""
        # Remove common suffixes
        title = re.sub(r'\b(LLC|Inc|Corporation|Corp|Ltd|L\.L\.C\.)\b\.?', '', title, flags=re.IGNORECASE)
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        return title
    
    def normalize_for_comparison(self, text: str) -> str:
        """Normalize text for fuzzy matching"""
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Remove common words
        common_words = ['the', 'a', 'an', 'of', 'at', 'in', 'on', 'for']
        words = text.split()
        words = [w for w in words if w not in common_words]
        return ' '.join(words)
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Simple similarity score based on common words"""
        words1 = set(self.normalize_for_comparison(str1).split())
        words2 = set(self.normalize_for_comparison(str2).split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def search_seniorly(self, page, title: str, city: str, state: str) -> Optional[Dict]:
        """Search Seniorly.com for a facility"""
        try:
            clean_title = self.clean_title_for_search(title)
            
            # Build search query - try title + city first
            search_query = f"{clean_title} {city}"
            encoded_query = quote_plus(search_query)
            
            # Seniorly search URL
            search_url = f"https://www.seniorly.com/search?query={encoded_query}"
            
            await page.goto(search_url, timeout=30000)
            await page.wait_for_timeout(3000)  # Let results load
            
            # Look for search result cards
            result_selectors = [
                '.search-result',
                '.listing-card',
                'article',
                '[data-testid="search-result"]',
                'a[href*="/assisted-living/"]',
                'a[href*="/memory-care/"]',
                'a[href*="/independent-living/"]'
            ]
            
            for selector in result_selectors:
                results = await page.query_selector_all(selector)
                
                if results:
                    # Check first few results for best match
                    for i, result in enumerate(results[:5]):
                        try:
                            # Extract title
                            title_elem = await result.query_selector('h2, h3, .title, [class*="title"]')
                            if not title_elem:
                                continue
                            
                            found_title = await title_elem.inner_text()
                            found_title = found_title.strip()
                            
                            # Check similarity
                            similarity = self.calculate_similarity(title, found_title)
                            
                            if similarity > 0.5:  # Good match threshold
                                # Extract URL
                                link = await result.query_selector('a')
                                if link:
                                    href = await link.get_attribute('href')
                                    if href:
                                        if not href.startswith('http'):
                                            href = f"https://www.seniorly.com{href}"
                                        
                                        return {
                                            'seniorly_url': href,
                                            'seniorly_title': found_title,
                                            'similarity_score': similarity,
                                            'matched': True
                                        }
                        except Exception as e:
                            continue
            
            # No match found
            return {'matched': False}
            
        except Exception as e:
            print(f"    ❌ Search error: {e}")
            return {'matched': False}
    
    async def get_seniorly_content(self, page, url: str) -> Dict:
        """Get enhanced content from Seniorly listing page"""
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)
            
            content = {}
            
            # Get description
            desc_selectors = [
                '.community-description',
                '.listing-description',
                '.about-section',
                '[data-testid="description"]'
            ]
            
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text and len(text.strip()) > 50:
                            content['description'] = text.strip()
                            break
                except:
                    continue
            
            # Get images
            images = []
            img_selectors = [
                '.gallery__item img',
                'img[src*="seniorly"]',
                'img[src*="cloudfront"]'
            ]
            
            for selector in img_selectors:
                try:
                    imgs = await page.query_selector_all(selector)
                    for img in imgs[:5]:  # Limit to 5 images
                        src = await img.get_attribute('src')
                        if src and 'data:image' not in src:
                            if src.startswith('//'):
                                src = 'https:' + src
                            images.append(src)
                except:
                    continue
            
            if images:
                content['seniorly_images'] = images
            
            # Get phone
            try:
                phone_elem = await page.query_selector('a[href^="tel:"]')
                if phone_elem:
                    phone = await phone_elem.inner_text()
                    content['phone'] = re.sub(r'[^\d\-\(\)\+\s]', '', phone.strip())
            except:
                pass
            
            return content
            
        except Exception as e:
            print(f"    ❌ Content extraction error: {e}")
            return {}
    
    async def process_california_listings(self, input_file: str, output_file: str, limit: Optional[int] = None):
        """Process California listings and match with Seniorly"""
        
        print("🔗 CALIFORNIA + SENIORLY MATCHING")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Read California listings
        listings = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                listings.append(row)
        
        if limit:
            listings = listings[:limit]
        
        print(f"📊 Loaded {len(listings)} California listings")
        print()
        
        # Add new fields
        new_fields = ['seniorly_url', 'seniorly_title', 'seniorly_match_score', 
                      'seniorly_description', 'seniorly_images', 'seniorly_phone']
        new_fieldnames = list(fieldnames) + [f for f in new_fields if f not in fieldnames]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                for i, listing in enumerate(listings, 1):
                    title = listing.get('title', 'Unknown')
                    city = listing.get('location-name', '')
                    state = listing.get('state', 'CA')
                    
                    print(f"🔍 {i:4d}/{len(listings)} - {title[:50]:<50}", end=" ")
                    
                    # Search Seniorly
                    match_result = await self.search_seniorly(page, title, city, state)
                    
                    if match_result.get('matched'):
                        seniorly_url = match_result['seniorly_url']
                        
                        # Store match info
                        listing['seniorly_url'] = seniorly_url
                        listing['seniorly_title'] = match_result.get('seniorly_title', '')
                        listing['seniorly_match_score'] = f"{match_result.get('similarity_score', 0):.2f}"
                        
                        # Get enhanced content
                        content = await self.get_seniorly_content(page, seniorly_url)
                        
                        if content.get('description'):
                            listing['seniorly_description'] = content['description']
                        
                        if content.get('seniorly_images'):
                            listing['seniorly_images'] = ', '.join(content['seniorly_images'])
                        
                        if content.get('phone'):
                            listing['seniorly_phone'] = content['phone']
                        
                        self.matched_count += 1
                        print(f"✅ {match_result.get('similarity_score', 0):.0%}")
                    else:
                        self.unmatched_count += 1
                        print("❌")
                    
                    self.processed_count += 1
                    
                    # Progress updates and rate limiting
                    if i % 10 == 0:
                        await asyncio.sleep(2)
                        print(f"   📊 Progress: {self.matched_count} matched, {self.unmatched_count} unmatched")
                    
                    # Periodic saves
                    if i % 100 == 0:
                        print(f"   💾 Saving checkpoint...")
                        self._save_results(output_file, listings, new_fieldnames)
            
            finally:
                await browser.close()
        
        # Final save
        print()
        print("💾 Writing final results...")
        self._save_results(output_file, listings, new_fieldnames)
        
        print()
        print("🎉 MATCHING COMPLETE!")
        print("=" * 60)
        print(f"✅ Matched with Seniorly: {self.matched_count} listings")
        print(f"❌ Not found on Seniorly: {self.unmatched_count} listings")
        print(f"📊 Match rate: {self.matched_count / self.processed_count * 100:.1f}%")
        print(f"📄 Output file: {output_file}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _save_results(self, output_file: str, listings: List[Dict], fieldnames: List[str]):
        """Save results to CSV"""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(listings)

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Match California listings with Seniorly")
    parser.add_argument('--input', default='california_seniorplace_data.csv', help='Input CSV with California listings')
    parser.add_argument('--output', default='california_seniorplace_data_with_seniorly.csv', help='Output CSV with Seniorly matches')
    parser.add_argument('--limit', type=int, help='Limit number of listings (for testing)')
    
    args = parser.parse_args()
    
    matcher = CaliforniaSeniorlyMatcher()
    await matcher.process_california_listings(args.input, args.output, args.limit)

if __name__ == "__main__":
    asyncio.run(main())
