import csv
import asyncio
import re
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin

INPUT_CSV = 'Listings_Export_2025_June_26_2013_cleaned_with_prices.csv'
OUTPUT_CSV = 'Listings_Export_2025_June_26_2013_cleaned_with_updated_images_test.csv'

def get_seniorly_url_from_title_and_location(title, location):
    """
    Generate potential Seniorly URL from title and location
    """
    if not title or not location:
        return None
    
    # Clean up title - remove common suffixes and make URL-friendly
    clean_title = title.lower()
    clean_title = re.sub(r'\s+(assisted living|memory care|senior care|care center|home|facility|residence|community|manor|village|gardens?|estates?|place|center|house)(\s|$)', '', clean_title)
    clean_title = re.sub(r'[^\w\s-]', '', clean_title)  # Remove special chars except hyphens
    clean_title = re.sub(r'\s+', '-', clean_title.strip())  # Replace spaces with hyphens
    clean_title = re.sub(r'-+', '-', clean_title)  # Remove multiple consecutive hyphens
    clean_title = clean_title.strip('-')  # Remove leading/trailing hyphens
    
    # Clean up location
    clean_location = location.lower()
    clean_location = re.sub(r'[^\w\s-]', '', clean_location)
    clean_location = re.sub(r'\s+', '-', clean_location.strip())
    clean_location = re.sub(r'-+', '-', clean_location)
    clean_location = clean_location.strip('-')
    
    # Try different URL patterns that Seniorly might use
    possible_urls = []
    
    # For each care type, try multiple variations
    care_types = ['assisted-living', 'memory-care', 'independent-living', 'nursing-homes']
    
    for care_type in care_types:
        # Try exact match
        possible_urls.append(f"https://www.seniorly.com/{care_type}/arizona/{clean_location}/{clean_title}")
        
        # Try with 'at' prefix (common pattern like "mirabella-at-asu")
        if ' at ' in title.lower():
            title_with_at = re.sub(r'\s+at\s+', '-at-', title.lower())
            title_with_at = re.sub(r'[^\w\s-]', '', title_with_at)
            title_with_at = re.sub(r'\s+', '-', title_with_at.strip())
            title_with_at = re.sub(r'-+', '-', title_with_at).strip('-')
            possible_urls.append(f"https://www.seniorly.com/{care_type}/arizona/{clean_location}/{title_with_at}")
        
        # Try variations without certain words
        for word_to_remove in ['senior', 'care', 'living', 'assisted', 'memory']:
            title_without_word = re.sub(rf'\b{word_to_remove}\b', '', clean_title)
            title_without_word = re.sub(r'-+', '-', title_without_word).strip('-')
            if title_without_word and title_without_word != clean_title:
                possible_urls.append(f"https://www.seniorly.com/{care_type}/arizona/{clean_location}/{title_without_word}")
    
    return possible_urls

def has_seniorly_url(row):
    """Check if this row has a seniorly URL - if so, process it"""
    for key, val in row.items():
        if val and 'seniorly.com' in str(val):
            return True
    return False

def has_seniorplace_url(row):
    """Check if this row has a seniorplace URL - if so, skip it"""
    for key, val in row.items():
        if val and 'seniorplace.com/communities/show/' in str(val):
            return True
    return False

async def scrape_seniorly_image(context, urls):
    """
    Try to scrape the main image from a Seniorly listing page
    """
    for url in urls:
        print(f"[DEBUG] Trying Seniorly URL: {url}")
        page = await context.new_page()
        try:
            response = await page.goto(url, timeout=15000)
            if response and response.status == 200:
                print(f"[DEBUG] Successfully loaded: {url}")
                
                # Wait for the page to load
                await page.wait_for_timeout(2000)
                
                # Try to find the main community image
                # Look for various selectors that might contain the main image
                image_selectors = [
                    '.gallery__item img',  # Main gallery image
                    'img[src*="d354o3y6yz93dt.cloudfront.net"]',  # Seniorly CDN images
                    'img[alt*="Mirabella"]',  # Images with community name
                    'img[alt*="Tempe"]',  # Images with location
                    'img[alt*="AZ"]',  # Images with state
                    'img[loading="eager"]',  # Primary images (usually loaded eagerly)
                    'img[alt*="community"]',
                    'img[alt*="assisted living"]',
                    'img[alt*="senior living"]',
                    '.community-image img',
                    '.hero-image img',
                    '.main-image img',
                    'img[src*="seniorly"]',
                    'div[class*="image"] img',
                    'main img',
                    'article img'
                ]
                
                for selector in image_selectors:
                    try:
                        img_element = await page.query_selector(selector)
                        if img_element:
                            src = await img_element.get_attribute('src')
                            if src:
                                # Make sure it's an absolute URL
                                if src.startswith('//'):
                                    src = 'https:' + src
                                elif src.startswith('/'):
                                    src = urljoin(url, src)
                                
                                # Check if it's a good quality image (not tiny/icon)
                                if ('d354o3y6yz93dt.cloudfront.net' in src or 'seniorly' in src) and not any(bad in src.lower() for bad in ['icon', 'logo', 'avatar', 'thumb']):
                                    print(f"[DEBUG] Found image: {src}")
                                    await page.close()
                                    return src
                    except Exception as e:
                        print(f"[DEBUG] Error with selector {selector}: {e}")
                        continue
                
                print(f"[DEBUG] No suitable image found on: {url}")
            else:
                print(f"[DEBUG] Failed to load (status {response.status if response else 'None'}): {url}")
                
        except Exception as e:
            print(f"[DEBUG] Exception loading {url}: {e}")
        finally:
            await page.close()
    
    return None

async def main():
    updated = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Read CSV
        rows = []
        header = []
        
        with open(INPUT_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            rows = list(reader)
        
        # Process only first 50 rows for testing
        test_rows = rows[:50]
        print(f"Processing {len(test_rows)} listings (test mode)...")
        
        for i, row in enumerate(test_rows):
            print(f"\n[{i+1}/{len(test_rows)}] Processing: {row.get('Title', 'Unknown')}")
            
            # Only process if this is a Seniorly listing
            if not has_seniorly_url(row):
                print("[DEBUG] Skipping - not a Seniorly listing")
                continue
            
            # Skip if this is a seniorplace listing (shouldn't happen but double check)
            if has_seniorplace_url(row):
                print("[DEBUG] Skipping - has seniorplace URL")
                continue
            
            # Get current image
            current_image = row.get('Featured', '')
            print(f"[DEBUG] Current image: {current_image}")
            # We'll process Seniorly listings regardless of current image to get better ones
            
            # Try to find Seniorly listing
            title = row.get('Title', '')
            location = row.get('location', '') or row.get('Locations', '')
            
            if not title or not location:
                print("[DEBUG] Skipping - missing title or location")
                continue
            
            # Get potential Seniorly URLs
            seniorly_urls = get_seniorly_url_from_title_and_location(title, location)
            if not seniorly_urls:
                print("[DEBUG] Skipping - could not generate Seniorly URLs")
                continue
            
            # Try to scrape image from Seniorly
            new_image_url = await scrape_seniorly_image(context, seniorly_urls)
            
            if new_image_url:
                print(f"[SUCCESS] Found new image: {new_image_url}")
                row['Featured'] = new_image_url
                # Also update the Caption field to match
                row['Caption'] = new_image_url.split('/')[-1].split('.')[0] if '/' in new_image_url else ''
                updated.append({
                    'ID': row.get('ID', ''),
                    'Title': title,
                    'Location': location,
                    'Old_Image': current_image,
                    'New_Image': new_image_url
                })
            else:
                print("[DEBUG] No suitable image found")
        
        await browser.close()
        
        # Update the original rows with any changes
        for i, updated_row in enumerate(test_rows):
            rows[i] = updated_row
        
        # Write updated CSV
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"SUMMARY: Updated {len(updated)} listings with new images")
        print(f"Output saved to: {OUTPUT_CSV}")
        print(f"{'='*60}")
        
        for u in updated:
            print(f"\nID: {u['ID']}")
            print(f"Title: {u['Title']}")
            print(f"Location: {u['Location']}")
            print(f"Old Image: {u['Old_Image']}")
            print(f"New Image: {u['New_Image']}")

if __name__ == '__main__':
    asyncio.run(main()) 