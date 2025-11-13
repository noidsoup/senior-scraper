import asyncio
import re
from playwright.async_api import async_playwright
from urllib.parse import urljoin

async def test_mirabella():
    title = "Mirabella at ASU"
    location = "Tempe"
    
    # URL generation logic
    clean_title = title.lower()
    clean_title = re.sub(r'\s+(assisted living|memory care|senior care|care center|home|facility|residence|community|manor|village|gardens?|estates?|place|center|house)(\s|$)', '', clean_title)
    clean_title = re.sub(r'[^\w\s-]', '', clean_title)
    clean_title = re.sub(r'\s+', '-', clean_title.strip())
    clean_title = re.sub(r'-+', '-', clean_title)
    clean_title = clean_title.strip('-')
    
    clean_location = location.lower()
    clean_location = re.sub(r'[^\w\s-]', '', clean_location)
    clean_location = re.sub(r'\s+', '-', clean_location.strip())
    clean_location = re.sub(r'-+', '-', clean_location)
    clean_location = clean_location.strip('-')
    
    # Handle "at" pattern
    if ' at ' in title.lower():
        title_with_at = re.sub(r'\s+at\s+', '-at-', clean_title)
        print(f"Title with 'at': {title_with_at}")
    
    test_url = f"https://www.seniorly.com/assisted-living/arizona/{clean_location}/{clean_title}"
    print(f"Generated URL: {test_url}")
    
    # Test the actual scraping
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see what's happening
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"Trying URL: {test_url}")
            response = await page.goto(test_url, timeout=15000)
            if response and response.status == 200:
                print("✓ Page loaded successfully")
                
                await page.wait_for_timeout(3000)  # Wait for images to load
                
                # Try to find images
                image_selectors = [
                    '.gallery__item img',
                    'img[src*="d354o3y6yz93dt.cloudfront.net"]',
                    'img[loading="eager"]',
                ]
                
                for selector in image_selectors:
                    try:
                        img_elements = await page.query_selector_all(selector)
                        print(f"Found {len(img_elements)} images with selector: {selector}")
                        
                        for i, img in enumerate(img_elements):
                            src = await img.get_attribute('src')
                            alt = await img.get_attribute('alt')
                            print(f"  Image {i+1}: {src}")
                            print(f"  Alt text: {alt}")
                            
                            if src and ('d354o3y6yz93dt.cloudfront.net' in src or 'seniorly' in src):
                                print(f"✓ Found good image: {src}")
                                await browser.close()
                                return src
                                
                    except Exception as e:
                        print(f"Error with selector {selector}: {e}")
                        
            else:
                print(f"Failed to load page: {response.status if response else 'No response'}")
                
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            await browser.close()
    
    return None

if __name__ == '__main__':
    result = asyncio.run(test_mirabella())
    print(f"Final result: {result}") 