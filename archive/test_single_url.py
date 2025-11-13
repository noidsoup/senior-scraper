#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

def is_placeholder_image(img_src):
    """Check if image is a placeholder that should be skipped"""
    if not img_src:
        return True
    
    # Common placeholder patterns
    placeholder_patterns = [
        'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP',  # 1x1 transparent gif
        'placeholder',
        'no-image',
        'default',
        'missing',
        'blank',
        'empty'
    ]
    
    img_src_lower = img_src.lower()
    return any(pattern in img_src_lower for pattern in placeholder_patterns)

def extract_first_gallery_image(url):
    """Extract the first image URL from a Seniorly page gallery"""
    try:
        print(f"Testing URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the gallery div
        gallery_div = soup.find('div', id='gallery')
        if not gallery_div or not isinstance(gallery_div, Tag):
            print("No gallery div found")
            return None
        
        print("Found gallery div")
        
        # Find all images in the gallery and look for the first real one
        all_imgs = gallery_div.find_all('img')
        if not all_imgs:
            print("No images found in gallery")
            return None
        
        print(f"Found {len(all_imgs)} images in gallery")
        
        for i, img in enumerate(all_imgs):
            print(f"Processing image {i+1}")
            
            # Ensure img is a Tag object
            if not isinstance(img, Tag):
                print("  Invalid img element type")
                continue
                
            # Get the src attribute
            img_src = img.get('src')
            if not img_src:
                print("  No src attribute")
                continue
            
            # Handle case where src might be a list
            if isinstance(img_src, list):
                if len(img_src) > 0:
                    img_src = img_src[0]
                else:
                    print("  Empty src list")
                    continue
            
            # Ensure img_src is a string
            if not isinstance(img_src, str):
                print("  Invalid src type")
                continue
            
            print(f"  Image src: {img_src}")
            
            # Skip data URLs and placeholders
            if img_src.startswith('data:'):
                print("  Skipping data URL")
                continue
                
            if is_placeholder_image(img_src):
                print("  Skipping placeholder image")
                continue
            
            # Handle relative URLs
            if img_src.startswith('//'):
                img_src = 'https:' + img_src
            elif img_src.startswith('/'):
                img_src = urljoin(url, img_src)
            
            # Skip street view images - prefer actual property photos
            if 'maps.googleapis.com' in img_src or 'streetview' in img_src.lower():
                print("  Skipping street view image")
                continue
            
            # Check if this looks like a real image URL
            if img_src.startswith('https://') and any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                print(f"SUCCESS: Found featured image: {img_src}")
                return img_src
            else:
                print("  Not a valid image URL")
        
        print("No real images found in gallery")
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # Test with a real Seniorly URL from your CSV
    test_url = "https://www.seniorly.com/assisted-living/arizona/scottsdale/a-i-adult-care-home"
    result = extract_first_gallery_image(test_url)
    
    if result:
        print(f"SUCCESS: Extracted featured image: {result}")
    else:
        print("FAILED: Could not extract image") 