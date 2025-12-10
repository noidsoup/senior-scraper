#!/usr/bin/env python3
"""
Find published listings with 'referral' in the title
"""

import requests
import os
from requests.auth import HTTPBasicAuth

# Load WordPress credentials
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud")
WP_USER = os.getenv("WP_USER", "nicholas_editor")
WP_PASS = os.getenv("WP_PASS", "3oiO dmah Ao7w Y8M7 5RKF rVrk")

def find_referral_listings():
    """Find all published listings with 'referral' in title"""
    listings = []
    page = 1
    per_page = 100

    print("Searching for published listings with 'referral' in title...")

    while True:
        url = f"{WP_URL}/wp-json/wp/v2/listing"
        params = {
            'status': 'publish',
            'per_page': per_page,
            'page': page,
            '_fields': 'id,title,slug,status'
        }

        try:
            response = requests.get(url, params=params, auth=HTTPBasicAuth(WP_USER, WP_PASS), timeout=30)
            response.raise_for_status()

            batch = response.json()
            if not batch:
                break

            # Filter for titles containing 'referral' (case insensitive)
            referral_listings = []
            for item in batch:
                title = item['title']['rendered'] if isinstance(item['title'], dict) else item['title']
                if 'referral' in title.lower():
                    referral_listings.append({
                        'id': item['id'],
                        'title': title,
                        'status': item['status']
                    })

            listings.extend(referral_listings)
            print(f"Fetched page {page}: {len(batch)} total, {len(referral_listings)} with 'referral'")

            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if page >= total_pages:
                break

            page += 1

        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    return listings

def main():
    referral_listings = find_referral_listings()

    print(f"\nFound {len(referral_listings)} published listings with 'referral' in title:")
    print("-" * 80)

    for i, listing in enumerate(referral_listings, 1):
        print(f"{i:2d}. {listing['title']} (ID: {listing['id']})")

    if not referral_listings:
        print("No listings found with 'referral' in the title.")

if __name__ == "__main__":
    main()
