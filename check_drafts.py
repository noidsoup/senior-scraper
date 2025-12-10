#!/usr/bin/env python3
"""
Check what draft listings exist in WordPress
"""

import requests
import os
from datetime import datetime
from requests.auth import HTTPBasicAuth

# Load WordPress credentials
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud")
WP_USER = os.getenv("WP_USER", "nicholas_editor")
WP_PASS = os.getenv("WP_PASS", "3oiO dmah Ao7w Y8M7 5RKF rVrk")

def get_draft_listings():
    """Fetch all draft listings from WordPress"""
    listings = []
    page = 1
    per_page = 100

    print(f"Fetching draft listings from {WP_URL}...")

    while True:
        url = f"{WP_URL}/wp-json/wp/v2/listing"
        params = {
            'status': 'draft',
            'per_page': per_page,
            'page': page,
            '_fields': 'id,title,slug,status,date_modified'
        }

        try:
            response = requests.get(url, params=params, auth=HTTPBasicAuth(WP_USER, WP_PASS), timeout=30)
            response.raise_for_status()

            batch = response.json()
            if not batch:
                break

            listings.extend(batch)
            print(f"Fetched page {page}: {len(batch)} drafts (total drafts: {len(listings)})")

            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if page >= total_pages:
                break

            page += 1

        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    return listings

def main():
    print("CHECKING DRAFT LISTINGS")
    print("=" * 50)

    drafts = get_draft_listings()
    print(f"\nTotal draft listings: {len(drafts)}")

    if drafts:
        print("\nAll draft listings:")
        print("-" * 80)

        # Sort by modification date (most recent first)
        drafts.sort(key=lambda x: x.get('date_modified', ''), reverse=True)

        for i, listing in enumerate(drafts, 1):
            title = listing['title']['rendered'] if isinstance(listing['title'], dict) else listing['title']
            modified = listing.get('date_modified', 'Unknown')
            if modified != 'Unknown':
                # Parse and format date
                try:
                    dt = datetime.fromisoformat(modified.replace('T', ' ').replace('Z', ''))
                    modified = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass

            print(f"{i:2d}. {title} (ID: {listing['id']}, Modified: {modified})")

    else:
        print("No draft listings found.")

if __name__ == "__main__":
    main()
