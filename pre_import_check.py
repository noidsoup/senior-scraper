#!/usr/bin/env python3
"""
Pre-import verification script for web interface
Ensures WordPress connection and permissions are working before importing listings
"""
import requests
import os
import sys

# Configuration
WP_URL = 'https://aplaceforseniorscms.kinsta.cloud'
WP_USER = os.getenv('WP_USER')
WP_PASS = os.getenv('WP_PASS')

def check_environment():
    """Check that required environment variables are set"""
    print("Checking environment variables...")

    missing = []
    if not WP_USER:
        missing.append('WP_USER')
    if not WP_PASS:
        missing.append('WP_PASS')

    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        print("   Run: .\\load_env.ps1")
        return False

    print(f"WP_USER: {WP_USER}")
    print(f"WP_PASS: {len(WP_PASS)} characters")
    return True

def test_wordpress_connection():
    """Test basic WordPress API connection"""
    print("\nTesting WordPress connection...")

    try:
        response = requests.get(f'{WP_URL}/wp-json/wp/v2/listing?per_page=1', auth=(WP_USER, WP_PASS), timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                print("WordPress API accessible")
                print(f"   Found {len(data)} test listing(s)")
                return True
            else:
                print("WordPress API accessible but no listings found")
                return True
        else:
            print(f"WordPress API error: {response.status_code} - {response.text[:100]}")
            return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def test_listing_creation():
    """Test creating a listing to verify permissions"""
    print("\nTesting listing creation permissions...")

    test_listing = {
        'title': 'Pre-Import Test Listing',
        'content': 'This is a test listing to verify import permissions work correctly.',
        'status': 'draft',
        'acf': {
            'address': '123 Test Street, Test City, AZ 12345',
            'senior_place_url': 'https://test.example.com'
        }
    }

    try:
        response = requests.post(
            f'{WP_URL}/wp-json/wp/v2/listing',
            json=test_listing,
            auth=(WP_USER, WP_PASS),
            timeout=15
        )

        if response.status_code in [200, 201]:
            data = response.json()
            listing_id = data['id']
            print("Can create listings!")
            print(f"   Created test listing ID: {listing_id}")

            # Clean up the test listing
            delete_response = requests.delete(
                f'{WP_URL}/wp-json/wp/v2/listing/{listing_id}?force=true',
                auth=(WP_USER, WP_PASS),
                timeout=10
            )

            if delete_response.status_code == 200:
                print("Test listing cleaned up")
            else:
                print(f"Test listing not cleaned up (ID: {listing_id})")

            return True
        else:
            print(f"Cannot create listings: {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            print("   This usually means insufficient WordPress permissions.")
            print("   Check that the user has 'Administrator' role in WordPress admin.")
            return False

    except Exception as e:
        print(f"Error testing listing creation: {e}")
        return False

def main():
    """Run all pre-import checks"""
    print("Senior Scraper - Pre-Import Verification")
    print("=" * 50)

    checks_passed = 0
    total_checks = 3

    # Check 1: Environment variables
    if check_environment():
        checks_passed += 1
    else:
        sys.exit(1)

    # Check 2: WordPress connection
    if test_wordpress_connection():
        checks_passed += 1

    # Check 3: Listing creation permissions
    if test_listing_creation():
        checks_passed += 1

    print("\n" + "=" * 50)
    print(f"Results: {checks_passed}/{total_checks} checks passed")

    if checks_passed == total_checks:
        print("All systems go! Ready to import listings.")
        return True
    else:
        print("Some checks failed. Please fix issues before importing.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
