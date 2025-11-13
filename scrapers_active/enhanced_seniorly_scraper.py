#!/usr/bin/env python3
"""
Enhanced Seniorly Scraper
Scrapes Seniorly.com for better images and descriptions that can be AI-rewritten.
Designed to work with existing listings to enhance their content.
"""

import asyncio
import json
import csv
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from playwright.async_api import async_playwright
from datetime import datetime
from urllib.parse import urljoin, urlparse
import aiohttp

class EnhancedSeniorlyScraper:
    def __init__(self):
        self.session = None
        self.processed_count = 0
        self.successful_count = 0
        self.failed_count = 0
        
    async def init_session(self):
        """Initialize aiohttp session for faster requests"""
        self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    def extract_seniorly_urls(self, row: Dict[str, str]) -> List[str]:
        """Extract all possible Seniorly URLs from a row"""
        urls = []
        for key, value in row.items():
            if value and 'seniorly.com' in str(value).lower():
                # Clean and validate URL
                url = str(value).strip().strip('"\'')
                if url.startswith('http') and 'seniorly.com' in url:
                    urls.append(url)
        return urls
    
    async def scrape_seniorly_images(self, page, url: str) -> List[str]:
        """Scrape high-quality images from Seniorly listing"""
        try:
            response = await page.goto(url, timeout=30000)
            if not response or response.status != 200:
                return []
            
            await page.wait_for_timeout(3000)  # Let page load
            
            images = []
            
            # Multiple selectors for different image types
            image_selectors = [
                # Main gallery images (highest priority)
                '.gallery__item img',
                '.photo-gallery img',
                '.image-gallery img',
                
                # Hero/featured images
                '.hero-image img',
                '.featured-image img',
                '.main-image img',
                
                # Seniorly CDN images (high quality)
                'img[src*="d354o3y6yz93dt.cloudfront.net"]',
                'img[src*="seniorly"]',
                
                # Community images
                '.community-image img',
                '.listing-image img',
                'img[alt*="community"]',
                'img[alt*="assisted living"]',
                'img[alt*="senior living"]',
                
                # General high-quality images
                'img[loading="eager"]',  # Usually primary images
                'main img',
                'article img'
            ]
            
            for selector in image_selectors:
                try:
                    img_elements = await page.query_selector_all(selector)
                    for img in img_elements:
                        src = await img.get_attribute('src')
                        if src:
                            # Make absolute URL
                            if src.startswith('//'):
                                src = 'https:' + src
                            elif src.startswith('/'):
                                src = urljoin(url, src)
                            
                            # Quality filters
                            if self.is_high_quality_image(src):
                                images.append(src)
                                
                except Exception as e:
                    continue
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img in images:
                if img not in seen:
                    seen.add(img)
                    unique_images.append(img)
            
            return unique_images[:10]  # Limit to top 10 images
            
        except Exception as e:
            print(f"❌ Error scraping images from {url}: {e}")
            return []
    
    def is_high_quality_image(self, src: str) -> bool:
        """Filter for high-quality images"""
        src_lower = src.lower()
        
        # Exclude low-quality indicators
        bad_indicators = ['icon', 'logo', 'avatar', 'thumb', 'small', 'tiny', 'placeholder']
        if any(bad in src_lower for bad in bad_indicators):
            return False
        
        # Prefer Seniorly CDN images
        if 'd354o3y6yz93dt.cloudfront.net' in src_lower or 'seniorly' in src_lower:
            return True
        
        # Check for reasonable dimensions in URL (if present)
        dimension_match = re.search(r'(\d{3,4})x(\d{3,4})', src)
        if dimension_match:
            width, height = int(dimension_match.group(1)), int(dimension_match.group(2))
            return width >= 400 and height >= 300
        
        return True  # Default to include if no clear exclusion criteria
    
    async def scrape_seniorly_description(self, page, url: str) -> Dict[str, str]:
        """Scrape description and key details from Seniorly listing"""
        try:
            response = await page.goto(url, timeout=30000)
            if not response or response.status != 200:
                return {}
            
            await page.wait_for_timeout(3000)
            
            content = {}
            
            # Main description selectors
            description_selectors = [
                '.community-description',
                '.listing-description', 
                '.about-section',
                '.description',
                '[data-testid="description"]',
                '.content-section p',
                'main .text-content',
                'article .description'
            ]
            
            for selector in description_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 50:  # Meaningful description
                            content['description'] = text.strip()
                            break
                except:
                    continue
            
            # Amenities/features
            amenities = []
            amenity_selectors = [
                '.amenities li',
                '.features li',
                '.services li',
                '[data-testid="amenities"] li',
                '.amenity-list li'
            ]
            
            for selector in amenity_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for elem in elements:
                        text = await elem.inner_text()
                        if text and text.strip():
                            amenities.append(text.strip())
                except:
                    continue
            
            if amenities:
                content['amenities'] = amenities[:20]  # Limit amenities
            
            # Care types/services
            care_types = []
            care_selectors = [
                '.care-types li',
                '.services-offered li', 
                '[data-testid="care-types"] li',
                '.care-services li'
            ]
            
            for selector in care_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for elem in elements:
                        text = await elem.inner_text()
                        if text and text.strip():
                            care_types.append(text.strip())
                except:
                    continue
            
            if care_types:
                content['care_types'] = care_types
            
            # Contact info
            try:
                phone_elem = await page.query_selector('a[href^="tel:"], .phone, [data-testid="phone"]')
                if phone_elem:
                    phone = await phone_elem.inner_text()
                    content['phone'] = re.sub(r'[^\d\-\(\)\+\s]', '', phone.strip())
            except:
                pass
            
            return content
            
        except Exception as e:
            print(f"❌ Error scraping description from {url}: {e}")
            return {}
    
    async def enhance_single_listing(self, page, listing: Dict[str, str]) -> Dict[str, str]:
        """Enhance a single listing with Seniorly data"""
        seniorly_urls = self.extract_seniorly_urls(listing)
        
        if not seniorly_urls:
            return listing
        
        enhanced = listing.copy()
        all_images = []
        best_description = ""
        all_amenities = []
        
        # Try each Seniorly URL
        for url in seniorly_urls:
            try:
                # Scrape images
                images = await self.scrape_seniorly_images(page, url)
                all_images.extend(images)
                
                # Scrape content
                content = await self.scrape_seniorly_description(page, url)
                
                # Use the best description found
                if content.get('description') and len(content['description']) > len(best_description):
                    best_description = content['description']
                
                # Collect amenities
                if content.get('amenities'):
                    all_amenities.extend(content['amenities'])
                
                # Add other content
                if content.get('phone') and not enhanced.get('phone'):
                    enhanced['phone'] = content['phone']
                
            except Exception as e:
                print(f"⚠️ Error processing {url}: {e}")
                continue
        
        # Update listing with enhanced content
        if all_images:
            # Use best image as featured, store others in photos
            enhanced['featured_image'] = all_images[0]
            if len(all_images) > 1:
                enhanced['photos'] = ', '.join(all_images[1:6])  # Up to 5 additional photos
        
        if best_description:
            enhanced['description'] = best_description
            enhanced['seniorly_description'] = best_description  # Keep original for AI rewriting
        
        if all_amenities:
            # Remove duplicates and join
            unique_amenities = list(dict.fromkeys(all_amenities))  # Preserve order
            enhanced['amenities'] = ', '.join(unique_amenities[:15])  # Limit to 15
        
        return enhanced
    
    async def process_listings_file(self, input_file: str, output_file: str, limit: Optional[int] = None):
        """Process a CSV file of listings and enhance with Seniorly data"""
        
        print("🌟 ENHANCED SENIORLY SCRAPER")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Input: {input_file}")
        print(f"Output: {output_file}")
        print()
        
        # Read input file
        listings = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                listings.append(row)
        
        if limit:
            listings = listings[:limit]
        
        print(f"📊 Loaded {len(listings)} listings to process")
        
        # Add new fields for enhanced content
        enhanced_fields = ['seniorly_description', 'phone']
        new_fieldnames = list(fieldnames)
        for field in enhanced_fields:
            if field not in new_fieldnames:
                new_fieldnames.append(field)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                enhanced_listings = []
                
                for i, listing in enumerate(listings, 1):
                    title = listing.get('title', 'Unknown')[:50]
                    print(f"🔍 {i:4d}/{len(listings)} - {title:<50}", end=" ")
                    
                    seniorly_urls = self.extract_seniorly_urls(listing)
                    if not seniorly_urls:
                        print("⚠️ No Seniorly URL")
                        enhanced_listings.append(listing)
                        continue
                    
                    enhanced = await self.enhance_single_listing(page, listing)
                    enhanced_listings.append(enhanced)
                    
                    # Check if enhancement was successful
                    if (enhanced.get('seniorly_description') or 
                        enhanced.get('featured_image') != listing.get('featured_image') or
                        enhanced.get('amenities') != listing.get('amenities')):
                        self.successful_count += 1
                        print("✅")
                    else:
                        self.failed_count += 1
                        print("❌")
                    
                    self.processed_count += 1
                    
                    # Rate limiting and progress updates
                    if i % 10 == 0:
                        await asyncio.sleep(2)
                        print(f"   📊 Progress: {self.successful_count} enhanced, {self.failed_count} failed")
                
            finally:
                await browser.close()
        
        # Write enhanced data
        print()
        print("💾 Writing enhanced data...")
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(enhanced_listings)
        
        print()
        print("🎉 SENIORLY ENHANCEMENT COMPLETE!")
        print("=" * 60)
        print(f"✅ Successfully enhanced: {self.successful_count} listings")
        print(f"❌ Failed to enhance: {self.failed_count} listings") 
        print(f"📄 Output file: {output_file}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Seniorly scraper for better images and descriptions")
    parser.add_argument('--input', required=True, help='Input CSV file with listings')
    parser.add_argument('--output', required=True, help='Output CSV file for enhanced listings')
    parser.add_argument('--limit', type=int, help='Limit number of listings to process (for testing)')
    
    args = parser.parse_args()
    
    scraper = EnhancedSeniorlyScraper()
    await scraper.init_session()
    
    try:
        await scraper.process_listings_file(args.input, args.output, args.limit)
    finally:
        await scraper.close_session()

if __name__ == "__main__":
    asyncio.run(main())