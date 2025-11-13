#!/usr/bin/env python3
"""
Targeted tests for specific user-reported problems:
1. Community type mapping sync issues between Senior Place and WordPress
2. Zip code search weighting problems (85048 case and others)
3. Care type accuracy validation
"""

import requests
import pandas as pd
import json
import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import time

class SpecificProblemTests:
    def __init__(self):
        self.wp_site_url = "https://aplaceforseniorscms.kinsta.cloud"
        self.api_base = f"{self.wp_site_url}/wp-json/wp/v2"
        self.results = {}
        
        # Community type mappings from codebase
        self.seniorplace_mapping = {
            "assisted living facility": "Assisted Living Community",
            "assisted living home": "Assisted Living Home",
            "independent living": "Independent Living", 
            "memory care": "Memory Care",
            "skilled nursing": "Nursing Home",
            "continuing care retirement community": "Assisted Living Community",
            "in-home care": "Home Care",
            "home health": "Home Care",
            "hospice": "Home Care",
            "respite care": "Assisted Living Community",
        }
        
        self.wp_term_ids = {
            "Assisted Living Community": 5,
            "Assisted Living Home": 162,
            "Independent Living": 6,
            "Memory Care": 3,
            "Nursing Home": 7,
            "Home Care": 488,
        }

    def test_zip_code_weighting_issue(self):
        """Test the specific zip code 85048 weighting problem"""
        print("\n📮 PROBLEM TEST 1: Zip Code 85048 Weighting Issue")
        print("-" * 60)
        print("Testing the reported issue: 85048 first result correct, then alphabetical")
        
        # Test the specific problem zip code
        test_zip = "85048"
        
        try:
            # Search for zip code 85048
            url = f"{self.api_base}/listing?search={test_zip}&per_page=20"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Found {len(results)} results for zip {test_zip}")
                
                # Analyze result ordering
                zip_relevance_scores = []
                title_alphabetical_scores = []
                
                for i, listing in enumerate(results):
                    title = listing.get('title', {}).get('rendered', '')
                    
                    # Get address from ACF if available
                    acf = listing.get('acf', {})
                    address = acf.get('address', '') if acf else ''
                    
                    # Check zip code relevance (should be in address)
                    zip_in_address = test_zip in address
                    zip_score = 10 if zip_in_address else 0
                    
                    # Check if results are alphabetically ordered (bad)
                    alpha_score = ord(title[0].lower()) if title else 0
                    
                    zip_relevance_scores.append(zip_score)
                    title_alphabetical_scores.append(alpha_score)
                    
                    status = "🎯" if zip_in_address else "❌"
                    print(f"  {i+1:2d}. {status} {title[:50]}...")
                    if address:
                        print(f"      Address: {address[:60]}...")
                
                # Analyze patterns
                first_result_correct = zip_relevance_scores[0] > 0 if zip_relevance_scores else False
                subsequent_by_zip = all(score > 0 for score in zip_relevance_scores[1:5]) if len(zip_relevance_scores) > 1 else True
                
                # Check if subsequent results are alphabetically ordered
                alpha_ordered = all(title_alphabetical_scores[i] <= title_alphabetical_scores[i+1] 
                                  for i in range(len(title_alphabetical_scores)-1))
                
                print(f"\n📊 Analysis:")
                print(f"   First result has correct zip: {'✅' if first_result_correct else '❌'}")
                print(f"   Results 2-5 have correct zip: {'✅' if subsequent_by_zip else '❌'}")
                print(f"   Results appear alphabetically ordered: {'❌' if alpha_ordered else '✅'}")
                
                if first_result_correct and not subsequent_by_zip:
                    print(f"   🚨 CONFIRMED BUG: First result correct, subsequent results wrong!")
                    
                self.results['zip_85048'] = {
                    'total_results': len(results),
                    'first_correct': first_result_correct,
                    'subsequent_correct': subsequent_by_zip,
                    'alphabetically_ordered': alpha_ordered,
                    'bug_confirmed': first_result_correct and not subsequent_by_zip
                }
                
            else:
                print(f"❌ Search failed: HTTP {response.status_code}")
                self.results['zip_85048'] = {'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            print(f"❌ Error testing zip {test_zip}: {e}")
            self.results['zip_85048'] = {'error': str(e)}
    
    def test_multiple_zip_codes(self):
        """Test zip code weighting for multiple zip codes"""
        print("\n📮 PROBLEM TEST 2: Multiple Zip Code Weighting")
        print("-" * 60)
        
        # Test various Arizona zip codes
        test_zips = ['85048', '85260', '85028', '85364', '85395', '85251']
        
        zip_results = {}
        
        for zip_code in test_zips:
            try:
                url = f"{self.api_base}/listing?search={zip_code}&per_page=10"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    results = response.json()
                    
                    # Count how many results actually contain this zip
                    relevant_count = 0
                    for listing in results:
                        acf = listing.get('acf', {})
                        address = acf.get('address', '') if acf else ''
                        if zip_code in address:
                            relevant_count += 1
                    
                    relevance_rate = (relevant_count / len(results)) * 100 if results else 0
                    
                    print(f"  {zip_code}: {len(results)} results, {relevant_count} relevant ({relevance_rate:.1f}%)")
                    
                    zip_results[zip_code] = {
                        'total': len(results),
                        'relevant': relevant_count,
                        'relevance_rate': relevance_rate
                    }
                    
                else:
                    print(f"  {zip_code}: HTTP {response.status_code}")
                    zip_results[zip_code] = {'error': f'HTTP {response.status_code}'}
                    
            except Exception as e:
                print(f"  {zip_code}: Error - {str(e)[:30]}...")
                zip_results[zip_code] = {'error': str(e)}
        
        # Analyze overall zip search quality
        working_zips = [z for z in zip_results.values() if 'relevance_rate' in z]
        if working_zips:
            avg_relevance = sum(z['relevance_rate'] for z in working_zips) / len(working_zips)
            print(f"\n📊 Overall zip search relevance: {avg_relevance:.1f}%")
            
            if avg_relevance < 50:
                print(f"   🚨 POOR ZIP RELEVANCE: Less than 50% of results match searched zip!")
            elif avg_relevance < 80:
                print(f"   ⚠️  MODERATE ZIP RELEVANCE: Could be improved")
            else:
                print(f"   ✅ GOOD ZIP RELEVANCE")
        
        self.results['zip_multiple'] = zip_results
    
    def test_community_type_mapping_sync(self):
        """Test community type mapping synchronization issues"""
        print("\n🏥 PROBLEM TEST 3: Community Type Mapping Sync")
        print("-" * 60)
        print("Testing if WordPress types match Senior Place types correctly")
        
        # Get sample listings from each care type
        type_issues = {}
        
        for wp_type_name, wp_type_id in self.wp_term_ids.items():
            try:
                # Get listings of this type
                url = f"{self.api_base}/listing?type={wp_type_id}&per_page=20"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    listings = response.json()
                    print(f"\n🔍 Testing {wp_type_name} (ID {wp_type_id}): {len(listings)} listings")
                    
                    # Check if listings actually match this type
                    type_mismatches = []
                    
                    for listing in listings[:5]:  # Check first 5
                        title = listing.get('title', {}).get('rendered', '')
                        acf = listing.get('acf', {})
                        
                        # Get the actual WordPress taxonomy terms
                        wp_types = listing.get('type', [])
                        
                        # Check if this listing's title suggests a different type
                        title_lower = title.lower()
                        suggested_type = None
                        
                        if 'memory care' in title_lower:
                            suggested_type = 'Memory Care'
                        elif 'independent living' in title_lower:
                            suggested_type = 'Independent Living'
                        elif 'nursing' in title_lower or 'skilled nursing' in title_lower:
                            suggested_type = 'Nursing Home'
                        elif 'home care' in title_lower:
                            suggested_type = 'Home Care'
                        elif 'assisted living' in title_lower:
                            if 'home' in title_lower:
                                suggested_type = 'Assisted Living Home'
                            else:
                                suggested_type = 'Assisted Living Community'
                        
                        if suggested_type and suggested_type != wp_type_name:
                            type_mismatches.append({
                                'title': title,
                                'assigned_type': wp_type_name,
                                'suggested_type': suggested_type
                            })
                            print(f"    ⚠️  '{title[:40]}...' assigned as {wp_type_name} but suggests {suggested_type}")
                    
                    if type_mismatches:
                        type_issues[wp_type_name] = type_mismatches
                        print(f"    🚨 Found {len(type_mismatches)} potential mismatches")
                    else:
                        print(f"    ✅ No obvious type mismatches found")
                        
                else:
                    print(f"❌ {wp_type_name}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error testing {wp_type_name}: {e}")
        
        self.results['type_mapping_issues'] = type_issues
    
    def test_senior_place_vs_wordpress_types(self):
        """Test Senior Place vs WordPress type consistency"""
        print("\n🔄 PROBLEM TEST 4: Senior Place vs WordPress Type Consistency")
        print("-" * 60)
        
        try:
            # Get listings that have Senior Place URLs
            url = f"{self.api_base}/listing?per_page=50"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                listings = response.json()
                
                sp_listings = []
                for listing in listings:
                    acf = listing.get('acf', {})
                    website = acf.get('website', '') if acf else ''
                    
                    if 'seniorplace.com' in website:
                        sp_listings.append(listing)
                
                print(f"Found {len(sp_listings)} Senior Place listings to test")
                
                consistency_issues = []
                
                for listing in sp_listings[:10]:  # Test first 10
                    title = listing.get('title', {}).get('rendered', '')
                    acf = listing.get('acf', {})
                    website = acf.get('website', '') if acf else ''
                    
                    # Get WordPress assigned types
                    wp_types = listing.get('type', [])
                    
                    # Extract Senior Place ID from URL for potential lookup
                    sp_id_match = re.search(r'/communities/show/([a-f0-9-]+)', website)
                    sp_id = sp_id_match.group(1) if sp_id_match else None
                    
                    print(f"  📋 {title[:40]}...")
                    print(f"     WP Types: {wp_types}")
                    print(f"     SP ID: {sp_id}")
                    
                    # This is where we'd need to compare with actual Senior Place data
                    # For now, flag for manual review
                    consistency_issues.append({
                        'title': title,
                        'website': website,
                        'wp_types': wp_types,
                        'sp_id': sp_id
                    })
                
                self.results['sp_wp_consistency'] = consistency_issues
                print(f"\n📊 Collected {len(consistency_issues)} listings for consistency review")
                
            else:
                print(f"❌ Failed to get listings: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error in consistency test: {e}")
    
    def test_marigold_duplicate_case(self):
        """Test the specific Marigold duplicate case mentioned in memory"""
        print("\n🔍 PROBLEM TEST 5: Marigold Duplicate Case Analysis")
        print("-" * 60)
        print("Testing the Marigold duplicates (posts 8610/10521) issue")
        
        try:
            # Search for Marigold
            url = f"{self.api_base}/listing?search=marigold&per_page=10"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                results = response.json()
                print(f"Found {len(results)} Marigold-related results")
                
                marigold_listings = []
                for listing in results:
                    title = listing.get('title', {}).get('rendered', '')
                    if 'marigold' in title.lower():
                        
                        acf = listing.get('acf', {})
                        address = acf.get('address', '') if acf else ''
                        website = acf.get('website', '') if acf else ''
                        content = listing.get('content', {}).get('rendered', '') if listing.get('content') else ''
                        
                        marigold_listings.append({
                            'id': listing.get('id'),
                            'title': title,
                            'address': address,
                            'website': website,
                            'content_length': len(content.strip()) if content else 0,
                            'source': 'seniorplace' if 'seniorplace' in website else 'seniorly' if 'seniorly' in website else 'other'
                        })
                
                # Check for address duplicates (the specific issue)
                if len(marigold_listings) >= 2:
                    print(f"\nAnalyzing {len(marigold_listings)} Marigold listings:")
                    
                    for i, listing in enumerate(marigold_listings):
                        print(f"  {i+1}. ID {listing['id']}: {listing['title']}")
                        print(f"     Address: {listing['address']}")
                        print(f"     Source: {listing['source']}")
                        print(f"     Content: {listing['content_length']} chars")
                        
                        # Check if addresses match (the reported issue)
                        for j, other in enumerate(marigold_listings[i+1:], i+1):
                            if listing['address'] and other['address']:
                                if listing['address'].strip().lower() == other['address'].strip().lower():
                                    print(f"     🚨 DUPLICATE ADDRESS with listing {j+1}!")
                                    print(f"        Different content/titles affecting search ranking")
                
                self.results['marigold_case'] = marigold_listings
                
            else:
                print(f"❌ Marigold search failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error in Marigold test: {e}")
    
    def test_search_relevance_vs_alphabetical(self):
        """Test if search results prioritize relevance over alphabetical order"""
        print("\n🔍 PROBLEM TEST 6: Search Relevance vs Alphabetical Order")
        print("-" * 60)
        print("Testing if search results are improperly sorted alphabetically")
        
        test_searches = [
            ('85048', 'zip code relevance'),
            ('memory care', 'care type relevance'),
            ('phoenix', 'location relevance'),
            ('assisted living', 'care type relevance')
        ]
        
        for search_term, expected_relevance in test_searches:
            try:
                url = f"{self.api_base}/listing?search={search_term}&per_page=10"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    results = response.json()
                    
                    print(f"\n🔍 Testing '{search_term}' ({expected_relevance}):")
                    
                    titles = []
                    relevance_scores = []
                    
                    for i, listing in enumerate(results):
                        title = listing.get('title', {}).get('rendered', '')
                        titles.append(title)
                        
                        # Calculate simple relevance score
                        title_lower = title.lower()
                        acf = listing.get('acf', {})
                        address = acf.get('address', '') if acf else ''
                        
                        score = 0
                        if search_term.lower() in title_lower:
                            score += 10
                        if search_term.lower() in address.lower():
                            score += 5
                        
                        relevance_scores.append(score)
                        
                        print(f"    {i+1:2d}. (Score: {score:2d}) {title[:50]}...")
                    
                    # Check if results are sorted by relevance (good) or alphabetically (bad)
                    is_relevance_sorted = all(relevance_scores[i] >= relevance_scores[i+1] 
                                            for i in range(len(relevance_scores)-1))
                    
                    is_alphabetical = all(titles[i].lower() <= titles[i+1].lower() 
                                        for i in range(len(titles)-1))
                    
                    if is_relevance_sorted:
                        print(f"    ✅ Results appear sorted by relevance")
                    elif is_alphabetical:
                        print(f"    🚨 Results appear alphabetically sorted (BAD!)")
                    else:
                        print(f"    ⚠️  Results have mixed/unclear sorting")
                    
                else:
                    print(f"❌ Search '{search_term}' failed: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error testing '{search_term}': {e}")
    
    def run_targeted_tests(self):
        """Run all targeted problem tests"""
        print("🎯 TARGETED PROBLEM TEST SUITE")
        print("=" * 70)
        print("Testing specific user-reported issues:")
        print("- Zip code 85048 weighting problem")
        print("- Community type mapping sync issues")
        print("- Search relevance vs alphabetical ordering")
        print("=" * 70)
        
        tests = [
            self.test_zip_code_weighting_issue,
            self.test_multiple_zip_codes,
            self.test_community_type_mapping_sync,
            self.test_senior_place_vs_wordpress_types,
            self.test_marigold_duplicate_case,
            self.test_search_relevance_vs_alphabetical
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test failed with error: {e}")
        
        # Save detailed results
        with open('organized_csvs/TARGETED_PROBLEM_TEST_RESULTS.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Summary
        print("\n" + "=" * 70)
        print("🎯 TARGETED PROBLEM TEST SUMMARY")
        print("=" * 70)
        
        # Analyze key issues
        if 'zip_85048' in self.results:
            zip_result = self.results['zip_85048']
            if zip_result.get('bug_confirmed'):
                print("🚨 CONFIRMED: Zip code 85048 weighting issue")
            else:
                print("✅ Zip code 85048 appears to be working correctly")
        
        if 'type_mapping_issues' in self.results:
            type_issues = self.results['type_mapping_issues']
            total_issues = sum(len(issues) for issues in type_issues.values())
            if total_issues > 0:
                print(f"🚨 FOUND: {total_issues} potential community type mapping issues")
            else:
                print("✅ Community type mappings appear consistent")
        
        print(f"\n📁 Detailed results saved to: TARGETED_PROBLEM_TEST_RESULTS.json")
        
        return self.results

if __name__ == "__main__":
    suite = SpecificProblemTests()
    suite.run_targeted_tests()
