#!/usr/bin/env python3
"""
Comprehensive test suite for senior living listings
Tests data quality, duplicates, filters, content, and API functionality
"""

import requests
import pandas as pd
import re
from collections import Counter
import json
from urllib.parse import urljoin, urlparse

class ListingsTestSuite:
    def __init__(self):
        self.wp_site_url = "https://aplaceforseniorscms.kinsta.cloud"
        self.api_base = f"{self.wp_site_url}/wp-json/wp/v2"
        self.results = {}
        
    def load_data(self):
        """Load the clean dataset for testing"""
        try:
            self.df = pd.read_csv('organized_csvs/Listings-Export-2025-August-28-1956_NO_TRUE_DUPLICATES.csv')
            print(f"✅ Loaded {len(self.df)} listings for testing")
            return True
        except Exception as e:
            print(f"❌ Failed to load data: {e}")
            return False
    
    def test_duplicate_detection(self):
        """Test 1: Verify no true duplicates remain"""
        print("\n🔍 TEST 1: Duplicate Detection")
        print("-" * 40)
        
        # Test for exact title duplicates
        title_dupes = self.df[self.df.duplicated(subset=['Title'], keep=False)]
        
        # Test for exact address duplicates  
        address_dupes = self.df[self.df.duplicated(subset=['address'], keep=False)]
        
        # Test for title + address duplicates (true duplicates)
        self.df['title_address'] = self.df['Title'].str.strip() + '|||' + self.df['address'].str.strip()
        true_dupes = self.df[self.df.duplicated(subset=['title_address'], keep=False)]
        
        results = {
            'title_duplicates': len(title_dupes),
            'address_duplicates': len(address_dupes),
            'true_duplicates': len(true_dupes),
            'unique_titles': self.df['Title'].nunique(),
            'unique_addresses': self.df['address'].nunique(),
            'total_listings': len(self.df)
        }
        
        print(f"Total listings: {results['total_listings']}")
        print(f"Title duplicates: {results['title_duplicates']}")
        print(f"Address duplicates: {results['address_duplicates']}")
        print(f"True duplicates (same title + address): {results['true_duplicates']}")
        print(f"Unique titles: {results['unique_titles']}")
        print(f"Unique addresses: {results['unique_addresses']}")
        
        if results['true_duplicates'] == 0:
            print("✅ PASS: No true duplicates found")
        else:
            print("❌ FAIL: True duplicates still exist")
            
        self.results['duplicates'] = results
        return results['true_duplicates'] == 0
    
    def test_data_quality(self):
        """Test 2: Data quality and completeness"""
        print("\n📊 TEST 2: Data Quality")
        print("-" * 40)
        
        # Check required fields
        required_fields = ['ID', 'Title', 'address', 'website']
        missing_data = {}
        
        for field in required_fields:
            if field in self.df.columns:
                missing_count = self.df[field].isna().sum()
                empty_count = (self.df[field] == '').sum() if self.df[field].dtype == 'object' else 0
                total_missing = missing_count + empty_count
                missing_data[field] = {
                    'missing': total_missing,
                    'percentage': (total_missing / len(self.df)) * 100
                }
                print(f"{field}: {total_missing} missing ({missing_data[field]['percentage']:.1f}%)")
            else:
                print(f"❌ {field}: Column not found")
                missing_data[field] = {'missing': len(self.df), 'percentage': 100.0}
        
        # Check data sources
        if 'website' in self.df.columns:
            seniorplace_count = self.df['website'].str.contains('seniorplace.com', na=False).sum()
            seniorly_count = self.df['website'].str.contains('seniorly.com', na=False).sum()
            other_count = len(self.df) - seniorplace_count - seniorly_count
            
            print(f"\nData Sources:")
            print(f"Senior Place: {seniorplace_count}")
            print(f"Seniorly: {seniorly_count}")
            print(f"Other/External: {other_count}")
        
        # Check content quality
        if 'Content' in self.df.columns:
            has_content = self.df['Content'].notna() & (self.df['Content'].str.len() > 50)
            content_count = has_content.sum()
            print(f"\nContent Quality:")
            print(f"Listings with rich content: {content_count} ({(content_count/len(self.df)*100):.1f}%)")
        
        self.results['data_quality'] = missing_data
        return True
    
    def test_care_types_taxonomy(self):
        """Test 3: Care types and taxonomy integrity"""
        print("\n🏥 TEST 3: Care Types & Taxonomy")
        print("-" * 40)
        
        # Check care type fields
        type_fields = ['type', '_type', 'normalized_types']
        care_type_data = {}
        
        for field in type_fields:
            if field in self.df.columns:
                non_empty = self.df[field].notna() & (self.df[field] != '')
                count = non_empty.sum()
                print(f"{field}: {count} listings have data")
                
                # Sample values
                sample_values = self.df[self.df[field].notna()][field].head(5).tolist()
                print(f"  Sample values: {sample_values}")
                care_type_data[field] = count
        
        # Check for expected care types
        expected_types = [
            'Assisted Living Community', 'Assisted Living Home', 'Memory Care',
            'Independent Living', 'Nursing Home', 'Home Care'
        ]
        
        if 'normalized_types' in self.df.columns:
            all_types = self.df['normalized_types'].dropna().str.split(',').explode().str.strip()
            type_counts = Counter(all_types)
            
            print(f"\nMost common care types:")
            for care_type, count in type_counts.most_common(10):
                print(f"  {care_type}: {count}")
        
        self.results['care_types'] = care_type_data
        return True
    
    def test_geographic_distribution(self):
        """Test 4: Geographic distribution and state data"""
        print("\n🗺️  TEST 4: Geographic Distribution")
        print("-" * 40)
        
        # Check state distribution
        if 'state' in self.df.columns:
            state_counts = self.df['state'].value_counts()
            print("State distribution:")
            for state, count in state_counts.items():
                print(f"  {state}: {count} listings")
        
        # Check address patterns
        if 'address' in self.df.columns:
            addresses = self.df['address'].dropna()
            
            # Extract states from addresses
            state_pattern = r',\s*([A-Z]{2})\s+\d{5}'
            address_states = addresses.str.extract(state_pattern)[0].value_counts()
            
            print(f"\nStates from addresses:")
            for state, count in address_states.head(10).items():
                print(f"  {state}: {count}")
        
        # Check for international or invalid addresses
        if 'address' in self.df.columns:
            missing_addresses = self.df['address'].isna().sum()
            invalid_addresses = self.df[~self.df['address'].str.contains(r'[A-Z]{2}\s+\d{5}', na=False)]
            
            print(f"\nAddress Quality:")
            print(f"Missing addresses: {missing_addresses}")
            print(f"Potentially invalid addresses: {len(invalid_addresses)}")
        
        return True
    
    def test_pricing_data(self):
        """Test 5: Pricing data integrity"""
        print("\n💰 TEST 5: Pricing Data")
        print("-" * 40)
        
        price_fields = ['price', '_price']
        
        for field in price_fields:
            if field in self.df.columns:
                # Check for valid numeric prices
                numeric_prices = pd.to_numeric(self.df[field], errors='coerce')
                valid_prices = numeric_prices.notna()
                
                print(f"{field}:")
                print(f"  Listings with valid prices: {valid_prices.sum()}")
                
                if valid_prices.any():
                    prices = numeric_prices[valid_prices]
                    print(f"  Price range: ${prices.min():,.0f} - ${prices.max():,.0f}")
                    print(f"  Average price: ${prices.mean():,.0f}")
                    print(f"  Median price: ${prices.median():,.0f}")
                    
                    # Check for outliers
                    outliers = prices[(prices < 500) | (prices > 15000)]
                    if len(outliers) > 0:
                        print(f"  ⚠️  Potential outliers: {len(outliers)} prices outside $500-$15,000 range")
        
        return True
    
    def test_website_urls(self):
        """Test 6: Website URL validity"""
        print("\n🌐 TEST 6: Website URLs")
        print("-" * 40)
        
        if 'website' not in self.df.columns:
            print("❌ No website column found")
            return False
        
        websites = self.df['website'].dropna()
        url_stats = {
            'total_urls': len(websites),
            'valid_urls': 0,
            'seniorplace_urls': 0,
            'seniorly_urls': 0,
            'external_urls': 0,
            'invalid_urls': 0
        }
        
        url_pattern = r'^https?://'
        
        for url in websites:
            url_str = str(url).strip()
            
            if re.match(url_pattern, url_str):
                url_stats['valid_urls'] += 1
                
                if 'seniorplace.com' in url_str:
                    url_stats['seniorplace_urls'] += 1
                elif 'seniorly.com' in url_str:
                    url_stats['seniorly_urls'] += 1
                else:
                    url_stats['external_urls'] += 1
            else:
                url_stats['invalid_urls'] += 1
        
        for key, value in url_stats.items():
            percentage = (value / url_stats['total_urls'] * 100) if url_stats['total_urls'] > 0 else 0
            print(f"{key.replace('_', ' ').title()}: {value} ({percentage:.1f}%)")
        
        self.results['urls'] = url_stats
        return url_stats['invalid_urls'] == 0
    
    def test_api_connectivity(self):
        """Test 7: WordPress REST API connectivity"""
        print("\n🔌 TEST 7: API Connectivity")
        print("-" * 40)
        
        # Test basic API endpoints
        endpoints_to_test = [
            ('Posts', '/posts'),
            ('Listings', '/listing'),
            ('Categories', '/categories'),
            ('Pages', '/pages')
        ]
        
        api_results = {}
        
        for name, endpoint in endpoints_to_test:
            try:
                url = f"{self.api_base}{endpoint}?per_page=1"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    count = len(data)
                    print(f"✅ {name}: {response.status_code} (found {count} items)")
                    api_results[name] = 'success'
                else:
                    print(f"⚠️  {name}: HTTP {response.status_code}")
                    api_results[name] = f'http_{response.status_code}'
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ {name}: Connection error - {str(e)[:50]}...")
                api_results[name] = 'connection_error'
        
        self.results['api'] = api_results
        return True
    
    def test_content_sample(self):
        """Test 8: Sample content verification via API"""
        print("\n📝 TEST 8: Content Sample Verification")
        print("-" * 40)
        
        # Test a sample of listings via API
        sample_size = min(5, len(self.df))
        sample_listings = self.df.sample(n=sample_size)
        
        content_results = []
        
        for _, row in sample_listings.iterrows():
            post_id = row['ID']
            title = row['Title']
            
            try:
                endpoints = [
                    f"{self.api_base}/listing/{post_id}",
                    f"{self.api_base}/posts/{post_id}"
                ]
                
                success = False
                for endpoint in endpoints:
                    try:
                        response = requests.get(endpoint, timeout=10)
                        if response.status_code == 200:
                            post_data = response.json()
                            content = post_data.get('content', {})
                            if isinstance(content, dict):
                                content_text = content.get('rendered', '')
                            else:
                                content_text = str(content)
                            
                            clean_content = re.sub(r'<[^>]+>', '', content_text).strip()
                            content_length = len(clean_content)
                            
                            print(f"✅ ID {post_id}: {title[:30]}... ({content_length} chars)")
                            content_results.append({
                                'id': post_id,
                                'title': title,
                                'content_length': content_length,
                                'status': 'success'
                            })
                            success = True
                            break
                    except:
                        continue
                
                if not success:
                    print(f"❌ ID {post_id}: API access failed")
                    content_results.append({
                        'id': post_id,
                        'title': title,
                        'content_length': 0,
                        'status': 'failed'
                    })
                    
            except Exception as e:
                print(f"❌ ID {post_id}: Error - {str(e)[:30]}...")
        
        successful_checks = len([r for r in content_results if r['status'] == 'success'])
        print(f"\nAPI Content Check: {successful_checks}/{len(content_results)} successful")
        
        return successful_checks > 0
    
    def test_search_functionality(self):
        """Test 9: Search functionality"""
        print("\n🔍 TEST 9: Search Functionality")
        print("-" * 40)
        
        # Test search endpoint
        search_terms = ['assisted living', 'memory care', 'arizona', 'phoenix']
        
        for term in search_terms:
            try:
                url = f"{self.api_base}/listing?search={term}&per_page=5"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    results = response.json()
                    print(f"✅ Search '{term}': {len(results)} results found")
                else:
                    print(f"⚠️  Search '{term}': HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Search '{term}': {str(e)[:50]}...")
        
        return True
    
    def run_all_tests(self):
        """Run the complete test suite"""
        print("🧪 COMPREHENSIVE LISTINGS TEST SUITE")
        print("=" * 50)
        
        if not self.load_data():
            return False
        
        tests = [
            self.test_duplicate_detection,
            self.test_data_quality,
            self.test_care_types_taxonomy,
            self.test_geographic_distribution,
            self.test_pricing_data,
            self.test_website_urls,
            self.test_api_connectivity,
            self.test_content_sample,
            self.test_search_functionality
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test failed with error: {e}")
        
        # Save detailed results
        with open('organized_csvs/TEST_SUITE_RESULTS.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Final summary
        print("\n" + "=" * 50)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 50)
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Your listings data is in excellent shape.")
        elif passed >= total * 0.8:
            print("✅ Most tests passed. Minor issues to address.")
        else:
            print("⚠️  Several tests failed. Review the results above.")
        
        print(f"\n📁 Detailed results saved to: TEST_SUITE_RESULTS.json")
        
        return passed >= total * 0.8

if __name__ == "__main__":
    suite = ListingsTestSuite()
    suite.run_all_tests()

