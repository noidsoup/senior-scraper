import csv
import asyncio
from playwright.async_api import async_playwright

INPUT_CSV = 'latest.csv'
OUTPUT_CSV = 'latest_with_updated_images.csv'

async def scrape_seniorly_image(context, url):
    """
    Scrape the first image from the gallery on a Seniorly page
    """
    print(f"[DEBUG] Accessing Seniorly URL: {url}")
    page = await context.new_page()
    
    try:
        response = await page.goto(url, timeout=15000)
        if response and response.status == 200:
            print(f"[DEBUG] Successfully loaded: {url}")
            
            # Wait for the page to load
            await page.wait_for_timeout(3000)
            
            # Look for the first image in the gallery
            try:
                # Look for all gallery images and find the best one
                gallery_images = await page.query_selector_all('.gallery__item img')
                
                for img in gallery_images:
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt')
                    
                    if not src or not alt:
                        continue
                    
                    # Skip placeholder images, street views, and lazy loading placeholders
                    if any(skip_pattern in src.lower() for skip_pattern in [
                        'data:image/gif',  # Lazy loading placeholder
                        'maps.googleapis.com',  # Google street view
                        'vectors/',  # SVG placeholders
                        'Small A_V2.svg'  # Specific placeholder
                    ]):
                        continue
                    
                    # Skip generic alt text
                    if any(skip_alt in alt.lower() for skip_alt in [
                        'google street view',
                        'seniorly image',
                        'acoya shea'  # Generic placeholder
                    ]):
                        continue
                    
                    # Found a good Seniorly CDN image
                    if 'd354o3y6yz93dt.cloudfront.net' in src and '/images/' in src:
                        print(f"[DEBUG] Found good gallery image: {src}")
                        print(f"[DEBUG] Alt text: {alt}")
                        await page.close()
                        return src
                
                print(f"[DEBUG] No suitable gallery image found on: {url}")
                
            except Exception as e:
                print(f"[DEBUG] Error finding gallery image: {e}")
                
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
        
        print(f"Processing {len(rows)} listings...")
        
        for i, row in enumerate(rows):
            print(f"\n[{i+1}/{len(rows)}] Processing: {row.get('Title', 'Unknown')}")
            
            # Get the website field
            website = row.get('website', '').strip()
            
            # Only process if website contains seniorly.com
            if not website or 'seniorly.com' not in website:
                print("[DEBUG] Skipping - not a Seniorly website")
                continue
            
            # Get current image
            current_image = row.get('Featured', '').strip()
            print(f"[DEBUG] Current Featured image: {current_image}")
            print(f"[DEBUG] Website: {website}")
            
            # Skip if current image is already a Seniorly CDN image
            if current_image and 'd354o3y6yz93dt.cloudfront.net' in current_image:
                print("[DEBUG] Skipping - already has Seniorly CDN image")
                continue
            
            # Try to scrape image from the Seniorly website
            new_image_url = await scrape_seniorly_image(context, website)
            
            if new_image_url:
                # Skip if the new image is the same as current (shouldn't happen but safety check)
                if new_image_url == current_image:
                    print("[DEBUG] Skipping - new image same as current")
                    continue
                    
                print(f"[SUCCESS] Found new image: {new_image_url}")
                row['Featured'] = new_image_url
                # Also update the Caption field to match
                row['Caption'] = new_image_url.split('/')[-1].split('.')[0] if '/' in new_image_url else ''
                updated.append({
                    'ID': row.get('\ufeffID', '') or row.get('ID', ''),  # Handle BOM
                    'Title': row.get('Title', ''),
                    'Website': website,
                    'Old_Image': current_image,
                    'New_Image': new_image_url
                })
            else:
                print("[DEBUG] No suitable image found - skipping")
        
        await browser.close()
        
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
            print(f"Website: {u['Website']}")
            print(f"Old Image: {u['Old_Image']}")
            print(f"New Image: {u['New_Image']}")

if __name__ == '__main__':
    asyncio.run(main()) 