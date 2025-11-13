#!/usr/bin/env python3
"""
Fix the state filter test to use the correct URL structure
Based on the actual website showing Arizona results working
"""

import requests
import json
from urllib.parse import urlencode

def test_correct_state_filters():
    """Test state filters using the correct URL structure"""
    print("🔧 CORRECTED STATE FILTER TEST")
    print("-" * 50)
    
    wp_site_url = "https://aplaceforseniorscms.kinsta.cloud"
    api_base = f"{wp_site_url}/wp-json/wp/v2"
    
    # Try different approaches to find the correct state filter structure
    
    # Approach 1: Check if there's a state taxonomy
    print("1. Testing state taxonomy endpoint...")
    try:
        response = requests.get(f"{api_base}/states", timeout=10)
        if response.status_code == 200:
            states = response.json()
            print(f"   ✅ Found {len(states)} states in taxonomy")
            for state in states[:5]:  # Show first 5
                state_name = state.get('name', 'Unknown')
                state_id = state.get('id', 'Unknown')
                count = state.get('count', 0)
                print(f"   - {state_name} (ID: {state_id}, Count: {count})")
        else:
            print(f"   ❌ States endpoint: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ States endpoint error: {str(e)[:50]}...")
    
    # Approach 2: Try state parameter with names
    print("\\n2. Testing state filter by name...")
    states_to_test = ['Arizona', 'Colorado', 'Utah', 'Idaho', 'New Mexico']
    
    for state in states_to_test:
        try:
            # Try multiple parameter formats
            test_urls = [
                f"{api_base}/listing?state={state}&per_page=5",
                f"{api_base}/listing?states={state}&per_page=5", 
                f"{api_base}/listing?meta_key=state&meta_value={state}&per_page=5",
                f"{api_base}/listing?filter[state]={state}&per_page=5"
            ]
            
            success = False
            for i, url in enumerate(test_urls):
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        listings = response.json()
                        count = len(listings)
                        if count > 0:
                            print(f"   ✅ {state}: {count} results (method {i+1})")
                            print(f"      URL: {url}")
                            success = True
                            break
                    elif response.status_code != 400:  # 400 is expected for wrong params
                        print(f"   ⚠️  {state} (method {i+1}): HTTP {response.status_code}")
                except:
                    continue
            
            if not success:
                print(f"   ❌ {state}: No working method found")
                
        except Exception as e:
            print(f"   ❌ {state}: Error - {str(e)[:30]}...")
    
    # Approach 3: Check for custom fields/meta
    print("\\n3. Testing meta field approaches...")
    try:
        # Get a sample listing to see what fields are available
        response = requests.get(f"{api_base}/listing?per_page=1", timeout=10)
        if response.status_code == 200:
            listings = response.json()
            if listings:
                sample = listings[0]
                
                # Check ACF fields
                acf = sample.get('acf', {})
                if acf:
                    print("   ACF fields found:")
                    for key, value in acf.items():
                        if 'state' in key.lower() or 'location' in key.lower():
                            print(f"   - {key}: {value}")
                
                # Check meta fields
                meta = sample.get('meta', {})
                if meta:
                    print("   Meta fields with 'state' or 'location':")
                    for key, value in meta.items():
                        if 'state' in key.lower() or 'location' in key.lower():
                            print(f"   - {key}: {value}")
                            
    except Exception as e:
        print(f"   ❌ Sample listing error: {e}")
    
    # Approach 4: Check what's actually working on your site
    print("\\n4. Reverse engineering from working site...")
    
    # Since your site shows 3,137 Arizona results, let's see if we can find them
    try:
        # Try getting all listings and filter by state in address
        response = requests.get(f"{api_base}/listing?per_page=100", timeout=15)
        if response.status_code == 200:
            listings = response.json()
            
            arizona_count = 0
            colorado_count = 0
            
            for listing in listings:
                # Check address for state
                title = listing.get('title', {}).get('rendered', '')
                
                # Try to find address in content or ACF
                acf = listing.get('acf', {})
                address = acf.get('address', '') if acf else ''
                
                if ', Az ' in address or 'Arizona' in address:
                    arizona_count += 1
                elif ', Co ' in address or 'Colorado' in address:
                    colorado_count += 1
            
            print(f"   From 100 sample listings:")
            print(f"   - Arizona addresses: {arizona_count}")
            print(f"   - Colorado addresses: {colorado_count}")
            
            if arizona_count > 0:
                print(f"   ✅ Address filtering could work for state detection")
            
    except Exception as e:
        print(f"   ❌ Sample analysis error: {e}")

if __name__ == "__main__":
    test_correct_state_filters()
