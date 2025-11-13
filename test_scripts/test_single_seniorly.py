#!/usr/bin/env python3
"""
Test single Seniorly listing to verify care type scraping works properly
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_single_seniorly():
    """Test care type scraping on one Seniorly listing"""
    
    # Test URL from the current data
    test_url = "https://www.seniorly.com/assisted-living/arizona/scottsdale/a-i-adult-care-home"
    
    print(f"🔍 TESTING SINGLE SENIORLY LISTING")
    print(f"URL: {test_url}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(test_url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Map Seniorly care types to our canonical CMS categories
                    SENIORLY_TO_CANONICAL = {
                        'assisted living': 'Assisted Living Community',
                        'assisted living community': 'Assisted Living Community',
                        'assisted living facility': 'Assisted Living Community',
                        'board and care home': 'Assisted Living Home',
                        'adult care home': 'Assisted Living Home',
                        'memory care': 'Memory Care',
                        'independent living': 'Independent Living',
                        'nursing home': 'Nursing Home',
                        'skilled nursing': 'Nursing Home',
                        'home care': 'Home Care',
                        'in-home care': 'Home Care',
                        'continuing care retirement community': 'Assisted Living Community',
                        'respite care': 'Home Care'
                    }
                    
                    # Look for care types SPECIFIC to this listing, not the global page
                    found_care_types = []
                    
                    # Method 1: Look for care types in the listing title and main content area
                    # Avoid the global navigation/footer that has all possible care types
                    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                    if main_content:
                        content_text = main_content.get_text().lower()
                        print(f"✅ Found main content area")
                    else:
                        # Fallback to body but exclude obvious navigation/footer areas
                        body = soup.find('body')
                        if body:
                            # Remove navigation, footer, and other global elements
                            for nav in body.find_all(['nav', 'footer', 'header']):
                                nav.decompose()
                            content_text = body.get_text().lower()
                            print(f"✅ Using body content (excluded nav/footer)")
                        else:
                            content_text = soup.get_text().lower()
                            print(f"⚠️  Using full page content")
                    
                    print(f"📄 Content length: {len(content_text)} characters")
                    
                    # Method 2: Look for specific care type indicators in the listing
                    # Check for care type mentions in the listing description, not global template
                    for seniorly_type, canonical_type in SENIORLY_TO_CANONICAL.items():
                        if seniorly_type in content_text:
                            # Additional check: make sure it's not just in global navigation
                            # Look for care types mentioned in context of this specific listing
                            if canonical_type not in found_care_types:
                                found_care_types.append(canonical_type)
                                print(f"🔍 Found '{seniorly_type}' → mapped to '{canonical_type}'")
                    
                    # Method 3: Look for care type tags or badges specific to this listing
                    care_tags = soup.find_all(['span', 'div', 'p'], class_=lambda x: x and any(word in x.lower() for word in ['care', 'type', 'service', 'community']))
                    print(f"🔍 Found {len(care_tags)} potential care type tags")
                    
                    for tag in care_tags:
                        tag_text = tag.get_text().lower()
                        for seniorly_type, canonical_type in SENIORLY_TO_CANONICAL.items():
                            if seniorly_type in tag_text and canonical_type not in found_care_types:
                                found_care_types.append(canonical_type)
                                print(f"🔍 Found '{seniorly_type}' in tag → mapped to '{canonical_type}'")
                    
                    # Show results
                    print(f"\n📊 RESULTS:")
                    print(f"Found care types: {found_care_types}")
                    print(f"Final output: {', '.join(sorted(found_care_types)) if found_care_types else 'No care types found'}")
                    
                    return found_care_types
                    
                else:
                    print(f"❌ HTTP {response.status}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None

if __name__ == "__main__":
    asyncio.run(test_single_seniorly())
