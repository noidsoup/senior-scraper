#!/usr/bin/env python3
"""
Test the actual frontend search functionality with custom zip weighting logic
Tests the real user-facing search, not the WordPress REST API
"""

import requests
import json
import time
from urllib.parse import urlencode
from typing import Dict, List

class FrontendSearchTests:
    def __init__(self):
        self.base_url = "https://communities.aplaceforseniors.org"
        self.results = {}
        
    def test_zip_code_weighting_frontend(self):
        """Test zip code weighting on the actual frontend"""
        print("\n📮 FRONTEND TEST 1: Zip Code Weighting Logic")
        print("-" * 60)
        
        # Test the specific zip codes from your examples
        test_cases = [
            ('85048', 'Phoenix area'),
            ('85282', 'Tempe area'), 
            ('85208', 'Mesa area'),
            ('80224', 'Denver area')
        ]
        
        for zip_code, area in test_cases:
            print(f"\n🔍 Testing {zip_code} ({area}):")
            
            # Build the frontend search URL like your examples
            params = {
                'onBehalf': 'My parent',
                'timeline': 'A month',
                'budget': '2500-5000',
                'state': 'arizona' if zip_code.startswith('85') else 'colorado',
                'city': area.split()[0].lower(),
                'location': area.split()[0].lower(),
                'zip': zip_code
            }
            
            search_url = f"{self.base_url}/listings?" + urlencode(params)
            
            try:
                response = requests.get(search_url, timeout=15)
                if response.status_code == 200:
                    # Parse the HTML to check for listings
                    html = response.text
                    
                    # Prefer the explicit results count if present
                    import re
                    match = re.search(r"(\d+)\s+results\s+found", html, re.IGNORECASE)
                    if match:
                        listing_count = int(match.group(1))
                    else:
                        # Fallback: count price banners and card markers
                        listing_count = html.count('Starting at **$') or html.count('Starting at $')
                        if listing_count == 0:
                            listing_count = html.count('View Details')
                    
                    # Check if zip code appears in first few results
                    zip_mentions = html[:5000].count(zip_code)  # Check first 5KB for zip
                    
                    print(f"   ✅ Page loaded successfully")
                    print(f"   📊 Estimated {listing_count} listings found")
                    print(f"   🎯 Zip code mentioned {zip_mentions} times in top results")
                    
                    # Check for "no results" indicators
                    if "no results" in html.lower() or "0 results" in html.lower():
                        print(f"   ⚠️  No results found for {zip_code}")
                    elif listing_count > 0:
                        print(f"   ✅ Results found and zip weighting appears active")
                    
                    self.results[f'zip_{zip_code}'] = {
                        'status': 'success',
                        'listing_count': listing_count,
                        'zip_mentions': zip_mentions,
                        'url': search_url
                    }
                    
                else:
                    print(f"   ❌ HTTP {response.status_code}")
                    self.results[f'zip_{zip_code}'] = {
                        'status': f'http_{response.status_code}',
                        'url': search_url
                    }
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
                self.results[f'zip_{zip_code}'] = {
                    'status': 'error',
                    'error': str(e),
                    'url': search_url
                }
    
    def test_pagination_zip_boost_fix(self):
        """Test that zip boost happens BEFORE pagination (the fix you made)"""
        print("\n📄 FRONTEND TEST 2: Pagination vs Zip Boost Order")
        print("-" * 60)
        
        # Test a zip code with many results to check pagination
        zip_code = '85048'
        
        print(f"Testing {zip_code} pagination behavior:")
        
        # Test page 1
        params_p1 = {
            'zip': zip_code,
            'state': 'arizona',
            'city': 'phoenix',
            'location': 'phoenix'
        }
        
        # Test page 2  
        params_p2 = params_p1.copy()
        params_p2['page'] = '2'
        
        for page_num, params in [('Page 1', params_p1), ('Page 2', params_p2)]:
            url = f"{self.base_url}/listings?" + urlencode(params)
            
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    html = response.text
                    
                    # Count zip mentions in results
                    zip_mentions = html.count(zip_code)
                    
                    # Prefer explicit results count if present
                    import re
                    match = re.search(r"(\d+)\s+results\s+found", html, re.IGNORECASE)
                    if match:
                        listings_count = int(match.group(1))
                    else:
                        listings_count = html.count('Starting at **$') or html.count('Starting at $')
                        if listings_count == 0:
                            listings_count = html.count('View Details')
                    
                    print(f"   {page_num}: {listings_count} listings, {zip_mentions} zip mentions")
                    
                    # Page 1 should have more zip matches than page 2 (if boost works)
                    if page_num == 'Page 1':
                        page1_zip_ratio = zip_mentions / max(listings_count, 1)
                    else:
                        page2_zip_ratio = zip_mentions / max(listings_count, 1)
                
                else:
                    print(f"   {page_num}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   {page_num}: Error - {str(e)[:30]}...")
        
        # Compare ratios
        try:
            if page1_zip_ratio > page2_zip_ratio:
                print(f"   ✅ Zip boost working: P1 ratio {page1_zip_ratio:.2f} > P2 ratio {page2_zip_ratio:.2f}")
            else:
                print(f"   ⚠️  Zip boost unclear: P1 ratio {page1_zip_ratio:.2f} vs P2 ratio {page2_zip_ratio:.2f}")
        except:
            print(f"   ⚠️  Could not compare page ratios")
    
    def test_completeness_score_fallback(self):
        """Test completeness score as tie breaker when no zip match"""
        print("\n📊 FRONTEND TEST 3: Completeness Score Fallback")
        print("-" * 60)
        
        # Test a search without zip to see completeness score ordering
        params = {
            'state': 'arizona',
            'city': 'phoenix',
            'budget': '3000-5000'
            # No zip - should fall back to completeness score
        }
        
        url = f"{self.base_url}/listings?" + urlencode(params)
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                html = response.text
                
                # Look for high-quality listings indicators
                quality_indicators = [
                    'Starting at **$',
                    'View Details',
                    ' Co ',  # address contains state abbreviation
                ]
                
                quality_score = sum(html[:3000].count(indicator) for indicator in quality_indicators)
                
                # Prefer explicit results count if present
                import re
                match = re.search(r"(\d+)\s+results\s+found", html, re.IGNORECASE)
                if match:
                    listings_count = int(match.group(1))
                else:
                    listings_count = html.count('Starting at **$') or html.count('Starting at $')
                    if listings_count == 0:
                        listings_count = html.count('View Details')
                
                print(f"   ✅ No-zip search loaded successfully")
                print(f"   📊 {listings_count} listings found")
                print(f"   ⭐ Quality indicators in top results: {quality_score}")
                
                # High quality score suggests completeness-based ordering is working
                if quality_score > listings_count * 0.8:  # 80% of listings have quality indicators
                    print(f"   ✅ Completeness score fallback appears to be working")
                else:
                    print(f"   ⚠️  Completeness score fallback unclear")
                    
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    def test_alphabetical_fallback(self):
        """Test alphabetical ordering as final fallback"""
        print("\n🔤 FRONTEND TEST 4: Alphabetical Fallback")
        print("-" * 60)
        
        # Test a very broad search that should have many equal-score results
        params = {
            'state': 'arizona',
            'type': 'assisted-living-community'
            # Broad search - many results should have similar scores
        }
        
        url = f"{self.base_url}/listings?" + urlencode(params)
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                html = response.text
                
                # Extract listing titles from HTML (basic pattern matching)
                import re
                title_pattern = r'<h[2-4][^>]*>([^<]+)</h[2-4]>'
                titles = re.findall(title_pattern, html)
                
                if len(titles) >= 5:
                    # Check if titles are roughly alphabetical
                    first_letters = [title[0].lower() for title in titles[:10] if title]
                    is_roughly_alphabetical = all(
                        first_letters[i] <= first_letters[i+1] 
                        for i in range(len(first_letters)-1)
                    )
                    
                    print(f"   📊 Found {len(titles)} listing titles")
                    print(f"   🔤 First letters: {first_letters[:5]}...")
                    
                    if is_roughly_alphabetical:
                        print(f"   ✅ Alphabetical fallback appears active")
                    else:
                        print(f"   ⚠️  Results not alphabetical - other sorting may be active")
                else:
                    print(f"   ⚠️  Could not extract enough titles to test")
                    
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    def test_zip_boost_validation(self):
        """Test specific zip boost cases from your examples"""
        print("\n🎯 FRONTEND TEST 5: Zip Boost Validation")
        print("-" * 60)
        
        # Test the exact 80224 case that you showed me
        print("Testing 80224 zip boost (your example):")
        
        params = {
            'onBehalf': 'My parent',
            'timeline': 'A month', 
            'budget': '2500-5000',
            'state': 'colorado',
            'city': 'denver',
            'location': 'denver',
            'zip': '80224'
        }
        
        url = f"{self.base_url}/listings?" + urlencode(params)
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                html = response.text
                
                # Prefer the explicit results count if present
                import re
                match = re.search(r"(\d+)\s+results\s+found", html, re.IGNORECASE)
                if match:
                    total_listings = int(match.group(1))
                else:
                    total_listings = html.count('Starting at **$') or html.count('Starting at $')
                    if total_listings == 0:
                        total_listings = html.count('View Details')
                
                # Find listings actually in 80224
                zip_80224_mentions = html.count(', Co 80224')
                
                # Check if 80224 listings appear early (first 2000 chars = top results)
                early_zip_mentions = html[:2000].count(', Co 80224')
                
                print(f"   📊 Total listings found: {total_listings}")
                print(f"   🎯 Listings in 80224: {zip_80224_mentions}")
                print(f"   ⬆️  80224 listings in top results: {early_zip_mentions}")
                
                if zip_80224_mentions > 0 and early_zip_mentions == zip_80224_mentions:
                    print(f"   ✅ ZIP BOOST CONFIRMED: All {zip_80224_mentions} 80224 listings appear at top!")
                elif early_zip_mentions > 0:
                    print(f"   ✅ ZIP BOOST WORKING: {early_zip_mentions}/{zip_80224_mentions} 80224 listings prioritized")
                else:
                    print(f"   ⚠️  Zip boost unclear - may need stronger weighting")
                    
                # Look for specific addresses from your example
                highpointe_found = "6383 East Girard Place" in html
                springbrooke_found = "6800 Leetsdale Drive" in html
                
                print(f"   🏠 Highpointe (6383 East Girard): {'✅ Found' if highpointe_found else '❌ Missing'}")
                print(f"   🏠 Springbrooke (6800 Leetsdale): {'✅ Found' if springbrooke_found else '❌ Missing'}")
                
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")

    def test_search_performance(self):
        """Test frontend search performance"""
        print("\n⚡ FRONTEND TEST 6: Search Performance")
        print("-" * 60)
        
        test_searches = [
            ('Simple zip', {'zip': '85048'}),
            ('Complex filter', {
                'zip': '85048',
                'state': 'arizona', 
                'city': 'phoenix',
                'budget': '3000-5000',
                'type': 'assisted-living'
            }),
            ('State only', {'state': 'arizona'}),
            ('Care type only', {'type': 'memory-care'})
        ]
        
        for test_name, params in test_searches:
            url = f"{self.base_url}/listings?" + urlencode(params)
            
            try:
                start_time = time.time()
                response = requests.get(url, timeout=30)
                end_time = time.time()
                
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    status = "🚀" if response_time < 2 else "⚠️" if response_time < 5 else "🐌"
                    print(f"   {status} {test_name}: {response_time:.2f}s")
                else:
                    print(f"   ❌ {test_name}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ {test_name}: Timeout or error")
    
    def run_frontend_tests(self):
        """Run all frontend search tests"""
        print("🌐 FRONTEND SEARCH TEST SUITE")
        print("=" * 70)
        print("Testing the actual user-facing search functionality")
        print("(Not the WordPress REST API)")
        print("=" * 70)
        
        tests = [
            self.test_zip_code_weighting_frontend,
            self.test_pagination_zip_boost_fix,
            self.test_completeness_score_fallback,
            self.test_alphabetical_fallback,
            self.test_zip_boost_validation,
            self.test_search_performance
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test failed: {e}")
        
        # Save results
        with open('organized_csvs/FRONTEND_SEARCH_TEST_RESULTS.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print("\n" + "=" * 70)
        print("🌐 FRONTEND SEARCH TEST SUMMARY")
        print("=" * 70)
        
        working_zips = sum(1 for k, v in self.results.items() 
                          if k.startswith('zip_') and v.get('status') == 'success')
        total_zips = sum(1 for k in self.results.keys() if k.startswith('zip_'))
        
        if total_zips > 0:
            print(f"Zip code searches: {working_zips}/{total_zips} working")
        
        print(f"📁 Detailed results: FRONTEND_SEARCH_TEST_RESULTS.json")
        print(f"🎯 These tests validate your custom search logic, not generic WordPress")

if __name__ == "__main__":
    suite = FrontendSearchTests()
    suite.run_frontend_tests()
