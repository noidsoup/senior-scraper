import csv
import asyncio
from playwright.async_api import async_playwright

INPUT_CSV = 'latest.csv'

async def test_seniorly_image(context, url):
    """
    Test scraping the first image from the gallery on a Seniorly page with detailed logging
    """
    print(f"[DEBUG] Accessing Seniorly URL: {url}")
    page = await context.new_page()
    
    try:
        response = await page.goto(url, timeout=15000)
        if response and response.status == 200:
            print(f"[DEBUG] ✓ Successfully loaded: {url}")
            
            # Wait for the page to load
            await page.wait_for_timeout(3000)
            
            # Look for any images first
            all_images = await page.query_selector_all('img')
            print(f"[DEBUG] Found {len(all_images)} total images on page")
            
            # Look for gallery container
            gallery_container = await page.query_selector('.image-gallery')
            if gallery_container:
                print(f"[DEBUG] ✓ Found .image-gallery container")
            else:
                print(f"[DEBUG] ✗ No .image-gallery container found")
            
            # Look for gallery items
            gallery_items = await page.query_selector_all('.gallery__item')
            print(f"[DEBUG] Found {len(gallery_items)} .gallery__item elements")
            
            # Look for gallery item images
            gallery_images = await page.query_selector_all('.gallery__item img')
            print(f"[DEBUG] Found {len(gallery_images)} images in .gallery__item elements")
            
            if gallery_images:
                for i, img in enumerate(gallery_images[:3]):  # Check first 3
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt')
                    loading = await img.get_attribute('loading')
                    print(f"[DEBUG] Gallery Image {i+1}:")
                    print(f"  src: {src}")
                    print(f"  alt: {alt}")
                    print(f"  loading: {loading}")
                    
                    if src and 'd354o3y6yz93dt.cloudfront.net' in src:
                        print(f"[SUCCESS] ✓ Found Seniorly CDN image: {src}")
                        await page.close()
                        return src
            
            # Look for the specific pattern from your example
            eager_img = await page.query_selector('.gallery__item img[loading="eager"]')
            if eager_img:
                src = await eager_img.get_attribute('src')
                print(f"[DEBUG] Found eager loading image: {src}")
                if src and 'd354o3y6yz93dt.cloudfront.net' in src:
                    print(f"[SUCCESS] ✓ Found eager loading Seniorly image: {src}")
                    await page.close()
                    return src
            else:
                print(f"[DEBUG] ✗ No img[loading='eager'] found in gallery items")
                
            print(f"[DEBUG] ✗ No suitable gallery image found")
                
        else:
            print(f"[DEBUG] ✗ Failed to load (status {response.status if response else 'None'}): {url}")
            
    except Exception as e:
        print(f"[DEBUG] ✗ Exception loading {url}: {e}")
    finally:
        await page.close()
    
    return None

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see what's happening
        context = await browser.new_context()
        
        # Read CSV and find first few Seniorly listings
        seniorly_listings = []
        
        with open(INPUT_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                website = row.get('website', '').strip()
                if 'seniorly.com' in website:
                    seniorly_listings.append({
                        'id': row.get('\ufeffID', '') or row.get('ID', ''),
                        'title': row.get('Title', ''),
                        'website': website,
                        'featured': row.get('Featured', '').strip()
                    })
                    if len(seniorly_listings) >= 3:  # Test first 3
                        break
        
        print(f"Found {len(seniorly_listings)} Seniorly listings to test")
        
        for i, listing in enumerate(seniorly_listings):
            print(f"\n{'='*80}")
            print(f"TESTING LISTING {i+1}/3")
            print(f"ID: {listing['id']}")
            print(f"Title: {listing['title']}")
            print(f"Website: {listing['website']}")
            print(f"Current Featured: {listing['featured']}")
            print(f"{'='*80}")
            
            # Test scraping
            new_image = await test_seniorly_image(context, listing['website'])
            
            if new_image:
                print(f"[RESULT] ✓ SUCCESS - New image found: {new_image}")
            else:
                print(f"[RESULT] ✗ FAILED - No image found")
            
            print()
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main()) 