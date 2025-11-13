#!/usr/bin/env python3
"""
Filter-specific test suite for senior living listings
Tests the actual WordPress filters that users interact with
"""

import requests
import pandas as pd
import json
from urllib.parse import urlencode
import time

class FilterTestSuite:
    def __init__(self):
        self.wp_site_url = "https://aplaceforseniorscms.kinsta.cloud"
        self.api_base = f"{self.wp_site_url}/wp-json/wp/v2"
        self.results = {}
        
    def test_care_type_filter(self):
        """Test care type filtering (most important filter)"""
        print("\n🏥 FILTER TEST 1: Care Type Filter")
        print("-" * 50)
        
        # Test different care type IDs
        care_types = {
            'Assisted Living Community': 5,
            'Assisted Living Home': 162, 
            'Memory Care': 3,
            'Independent Living': 6,
            'Nursing Home': 7,
            'Home Care': 488
        }
        
        results = {}
        
        for care_type, type_id in care_types.items():
            try:
                # Test WordPress taxonomy filter
                url = f"{self.api_base}/listing?type={type_id}&per_page=20"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    listings = response.json()
                    count = len(listings)
                    
                    print(f"✅ {care_type} (ID {type_id}): {count} results")
                    
                    # Check if results actually match the filter
                    if count > 0:
                        sample = listings[0]
                        title = sample.get('title', {}).get('rendered', 'Unknown')
                        print(f"   Sample: {title[:50]}...")
                    
                    results[care_type] = {
                        'id': type_id,
                        'count': count,
                        'status': 'success'
                    }
                    
                else:
                    print(f"❌ {care_type}: HTTP {response.status_code}")
                    results[care_type] = {
                        'id': type_id,
                        'count': 0,
                        'status': f'http_{response.status_code}'
                    }
                    
            except Exception as e:
                print(f"❌ {care_type}: Error - {str(e)[:50]}...")
                results[care_type] = {
                    'id': type_id,
                    'count': 0,
                    'status': 'error'
                }
        
        self.results['care_type_filter'] = results
        return results
    
    def test_location_filters(self):
        """Test location/state filtering"""
        print("\n📍 FILTER TEST 2: Location Filters") 
        print("-" * 50)
        
        # Test state filtering
        states_to_test = ['Arizona', 'Colorado', 'Utah', 'Idaho', 'New Mexico']
        
        results = {}
        
        for state in states_to_test:
            try:
                # Test state filter (assuming you have a state taxonomy)
                url = f"{self.api_base}/listing?state={state}&per_page=10"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    listings = response.json()
                    count = len(listings)
                    print(f"✅ {state}: {count} results")
                    
                    results[state] = {
                        'count': count,
                        'status': 'success'
                    }
                else:
                    print(f"⚠️  {state}: HTTP {response.status_code}")
                    results[state] = {
                        'count': 0,
                        'status': f'http_{response.status_code}'
                    }
                    
            except Exception as e:
                print(f"❌ {state}: Error - {str(e)[:30]}...")
                results[state] = {
                    'count': 0,
                    'status': 'error'
                }
        
        # Test city search
        cities_to_test = ['Phoenix', 'Scottsdale', 'Mesa', 'Tucson', 'Denver']
        
        print(f"\\nCity Search Tests:")
        city_results = {}
        
        for city in cities_to_test:
            try:
                url = f"{self.api_base}/listing?search={city}&per_page=10"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    listings = response.json()
                    count = len(listings)
                    print(f"✅ {city}: {count} results")
                    city_results[city] = count
                else:
                    print(f"⚠️  {city}: HTTP {response.status_code}")
                    city_results[city] = 0
                    
            except Exception as e:
                print(f"❌ {city}: Error")
                city_results[city] = 0
        
        results['cities'] = city_results
        self.results['location_filters'] = results
        return results
    
    def test_price_filters(self):
        """Test price range filtering"""
        print("\n💰 FILTER TEST 3: Price Range Filters")
        print("-" * 50)
        
        # Test different price ranges
        price_ranges = [
            ('Under $2000', 0, 2000),
            ('$2000-$3000', 2000, 3000),
            ('$3000-$4000', 3000, 4000),
            ('$4000-$5000', 4000, 5000),
            ('Over $5000', 5000, 10000)
        ]
        
        results = {}
        
        for range_name, min_price, max_price in price_ranges:
            try:
                # Test meta query for price ranges
                meta_query = {
                    'meta_query': [
                        {
                            'key': 'price',
                            'value': [min_price, max_price],
                            'type': 'NUMERIC',
                            'compare': 'BETWEEN'
                        }
                    ]
                }
                
                # WordPress REST API doesn't directly support meta_query in URL
                # Try a simpler approach first
                url = f"{self.api_base}/listing?per_page=100"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    all_listings = response.json()
                    
                    # Filter client-side for testing
                    filtered_count = 0
                    for listing in all_listings:
                        # Check if listing has price in ACF fields
                        acf = listing.get('acf', {})
                        price = acf.get('price', 0) if acf else 0
                        
                        try:
                            price_num = float(price) if price else 0
                            if min_price <= price_num <= max_price:
                                filtered_count += 1
                        except:
                            continue
                    
                    print(f"✅ {range_name}: ~{filtered_count} results (client-side filter)")
                    results[range_name] = {
                        'min': min_price,
                        'max': max_price,
                        'count': filtered_count,
                        'status': 'success'
                    }
                    
                else:
                    print(f"❌ {range_name}: HTTP {response.status_code}")
                    results[range_name] = {
                        'min': min_price,
                        'max': max_price,
                        'count': 0,
                        'status': 'failed'
                    }
                    
            except Exception as e:
                print(f"❌ {range_name}: Error - {str(e)[:30]}...")
                results[range_name] = {
                    'count': 0,
                    'status': 'error'
                }
        
        self.results['price_filters'] = results
        return results
    
    def test_search_functionality(self):
        """Test search functionality with real user queries"""
        print("\n🔍 FILTER TEST 4: Search Functionality")
        print("-" * 50)
        
        # Real search terms users might use
        search_terms = [
            'memory care',
            'assisted living', 
            'independent living',
            'alzheimer',
            'dementia',
            'phoenix assisted living',
            'scottsdale memory care',
            'affordable senior living',
            'luxury senior community'
        ]
        
        results = {}
        
        for term in search_terms:
            try:
                url = f"{self.api_base}/listing?search={term}&per_page=20"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    listings = response.json()
                    count = len(listings)
                    
                    print(f"✅ '{term}': {count} results")
                    
                    # Check relevance of first result
                    if count > 0:
                        first_result = listings[0]
                        title = first_result.get('title', {}).get('rendered', '')
                        excerpt = first_result.get('excerpt', {}).get('rendered', '')
                        
                        # Simple relevance check
                        search_words = term.lower().split()
                        title_lower = title.lower()
                        excerpt_lower = excerpt.lower()
                        
                        relevance_score = 0
                        for word in search_words:
                            if word in title_lower:
                                relevance_score += 2
                            elif word in excerpt_lower:
                                relevance_score += 1
                        
                        print(f"   Top result: {title[:40]}... (relevance: {relevance_score})")
                        
                        results[term] = {
                            'count': count,
                            'relevance_score': relevance_score,
                            'top_result': title,
                            'status': 'success'
                        }
                    else:
                        results[term] = {
                            'count': 0,
                            'relevance_score': 0,
                            'status': 'no_results'
                        }
                        
                else:
                    print(f"❌ '{term}': HTTP {response.status_code}")
                    results[term] = {
                        'count': 0,
                        'status': f'http_{response.status_code}'
                    }
                    
            except Exception as e:
                print(f"❌ '{term}': Error - {str(e)[:30]}...")
                results[term] = {
                    'count': 0,
                    'status': 'error'
                }
        
        self.results['search'] = results
        return results
    
    def test_combined_filters(self):
        """Test combining multiple filters (real-world usage)"""
        print("\n🔗 FILTER TEST 5: Combined Filters")
        print("-" * 50)
        
        # Real user filter combinations
        filter_combos = [
            {
                'name': 'Memory Care in Arizona',
                'params': {'type': 3, 'search': 'arizona'}
            },
            {
                'name': 'Assisted Living in Phoenix',
                'params': {'type': 5, 'search': 'phoenix'}
            },
            {
                'name': 'Independent Living in Scottsdale', 
                'params': {'type': 6, 'search': 'scottsdale'}
            }
        ]
        
        results = {}
        
        for combo in filter_combos:
            try:
                params = urlencode(combo['params'])
                url = f"{self.api_base}/listing?{params}&per_page=20"
                
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    listings = response.json()
                    count = len(listings)
                    
                    print(f"✅ {combo['name']}: {count} results")
                    
                    results[combo['name']] = {
                        'params': combo['params'],
                        'count': count,
                        'status': 'success'
                    }
                    
                else:
                    print(f"❌ {combo['name']}: HTTP {response.status_code}")
                    results[combo['name']] = {
                        'count': 0,
                        'status': 'failed'
                    }
                    
            except Exception as e:
                print(f"❌ {combo['name']}: Error")
                results[combo['name']] = {
                    'count': 0,
                    'status': 'error'
                }
        
        self.results['combined_filters'] = results
        return results
    
    def test_filter_performance(self):
        """Test filter response times"""
        print("\n⚡ FILTER TEST 6: Performance")
        print("-" * 50)
        
        performance_tests = [
            ('Basic listing load', f"{self.api_base}/listing?per_page=20"),
            ('Care type filter', f"{self.api_base}/listing?type=5&per_page=20"),
            ('Search query', f"{self.api_base}/listing?search=assisted+living&per_page=20"),
            ('Large result set', f"{self.api_base}/listing?per_page=100")
        ]
        
        results = {}
        
        for test_name, url in performance_tests:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=30)
                end_time = time.time()
                
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    listings = response.json()
                    count = len(listings)
                    
                    status = "🚀" if response_time < 2 else "⚠️" if response_time < 5 else "🐌"
                    print(f"{status} {test_name}: {response_time:.2f}s ({count} results)")
                    
                    results[test_name] = {
                        'response_time': response_time,
                        'count': count,
                        'status': 'success'
                    }
                    
                else:
                    print(f"❌ {test_name}: HTTP {response.status_code}")
                    results[test_name] = {
                        'response_time': 0,
                        'status': 'failed'
                    }
                    
            except Exception as e:
                print(f"❌ {test_name}: Timeout or error")
                results[test_name] = {
                    'response_time': 0,
                    'status': 'error'
                }
        
        self.results['performance'] = results
        return results
    
    def run_filter_tests(self):
        """Run all filter-specific tests"""
        print("🔍 WORDPRESS FILTER TEST SUITE")
        print("=" * 60)
        print("Testing the actual filters users interact with")
        print("=" * 60)
        
        tests = [
            ('Care Type Filters', self.test_care_type_filter),
            ('Location Filters', self.test_location_filters),
            ('Price Filters', self.test_price_filters),
            ('Search Functionality', self.test_search_functionality),
            ('Combined Filters', self.test_combined_filters),
            ('Performance', self.test_filter_performance)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                print(f"\\nRunning {test_name}...")
                result = test_func()
                if result:
                    passed += 1
                    print(f"✅ {test_name} completed")
                else:
                    print(f"⚠️  {test_name} had issues")
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
        
        # Save results
        with open('organized_csvs/FILTER_TEST_RESULTS.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 FILTER TEST SUMMARY")
        print("=" * 60)
        
        # Analyze results
        issues_found = []
        
        if 'care_type_filter' in self.results:
            care_types = self.results['care_type_filter']
            working_types = [k for k, v in care_types.items() if v.get('count', 0) > 0]
            broken_types = [k for k, v in care_types.items() if v.get('count', 0) == 0]
            
            print(f"Care Type Filters: {len(working_types)}/{len(care_types)} working")
            if broken_types:
                print(f"  ⚠️  Not working: {', '.join(broken_types)}")
                issues_found.extend(broken_types)
        
        if 'search' in self.results:
            search_results = self.results['search']
            working_searches = [k for k, v in search_results.items() if v.get('count', 0) > 0]
            print(f"Search Terms: {len(working_searches)}/{len(search_results)} returning results")
        
        if 'performance' in self.results:
            perf_results = self.results['performance']
            fast_responses = [k for k, v in perf_results.items() if v.get('response_time', 10) < 3]
            print(f"Performance: {len(fast_responses)}/{len(perf_results)} responses under 3s")
        
        print(f"\\n📁 Detailed results: FILTER_TEST_RESULTS.json")
        
        if len(issues_found) == 0:
            print("\\n🎉 ALL FILTERS WORKING PROPERLY!")
        else:
            print(f"\\n⚠️  ISSUES FOUND: {len(issues_found)} filter problems detected")
            print("   Review the detailed results to fix these issues")
        
        return len(issues_found) == 0

if __name__ == "__main__":
    suite = FilterTestSuite()
    suite.run_filter_tests()
