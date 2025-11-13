#!/usr/bin/env python3
"""
Update WordPress location taxonomy terms via REST API.

This script uses the WordPress REST API to update California city descriptions
directly in the WordPress database using application password authentication.
"""

import csv
import requests
import json
import time
from typing import Dict, List
import os

class WordPressLocationUpdater:
    def __init__(self, base_url: str, username: str, app_password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, app_password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def get_location_terms(self) -> List[Dict]:
        """Get all location terms from WordPress"""
        url = f"{self.base_url}/wp-json/wp/v2/location?per_page=100"
        all_terms = []
        page = 1

        while True:
            response = self.session.get(f"{url}&page={page}")
            if response.status_code != 200:
                print(f"❌ Failed to get location terms: {response.status_code}")
                return []

            terms = response.json()
            if not terms:
                break

            all_terms.extend(terms)
            page += 1

            # Check if there are more pages
            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if page > total_pages:
                break

        print(f"📊 Found {len(all_terms)} location terms")
        return all_terms

    def update_term_description(self, term_id: int, description: str) -> bool:
        """Update a single term's description"""
        url = f"{self.base_url}/wp-json/wp/v2/location/{term_id}"

        data = {
            'description': description
        }

        response = self.session.put(url, json=data)
        if response.status_code in [200, 201]:
            print(f"✅ Updated term {term_id}")
            return True
        else:
            print(f"❌ Failed to update term {term_id}: {response.status_code} - {response.text}")
            return False

    def load_california_descriptions(self, csv_file: str) -> Dict[str, str]:
        """Load California city descriptions from CSV"""
        descriptions = {}

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                city_name = row['City'].strip()
                descriptions[city_name] = row['Description'].strip()

        print(f"📋 Loaded {len(descriptions)} California city descriptions")
        return descriptions

    def update_california_cities(self, csv_file: str) -> int:
        """Update California city descriptions"""
        print("🔄 Starting California location updates via REST API")
        print("-" * 60)

        # Load descriptions
        descriptions = self.load_california_descriptions(csv_file)

        # Get current terms
        terms = self.get_location_terms()

        # Find California cities that need updates
        updated_count = 0
        for term in terms:
            term_name = term['name']
            term_slug = term['slug']

            # Check if this is a California city that needs updating
            if term_name in descriptions and not term['description'].strip():
                print(f"📍 Updating {term_name} ({term_slug})...")

                description = descriptions[term_name]
                if self.update_term_description(term['id'], description):
                    updated_count += 1

                # Small delay to be respectful
                time.sleep(0.5)

        print("-" * 60)
        print(f"✅ Updated {updated_count} California city descriptions")
        return updated_count

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Update WordPress location taxonomy via REST API")
    parser.add_argument('--url', default='https://aplaceforseniorscms.kinsta.cloud',
                       help='WordPress site URL')
    parser.add_argument('--username', default='nicholas_editor',
                       help='WordPress username')
    parser.add_argument('--password', required=True,
                       help='Application password')
    parser.add_argument('--csv', default='california_city_descriptions_final.csv',
                       help='California descriptions CSV file')

    args = parser.parse_args()

    # Initialize updater
    updater = WordPressLocationUpdater(args.url, args.username, args.password)

    # Test connection
    print(f"🔗 Connecting to {args.url}...")
    try:
        terms = updater.get_location_terms()
        if not terms:
            print("❌ Could not connect to WordPress site")
            return
        print("✅ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # Update California cities
    updated_count = updater.update_california_cities(args.csv)

    if updated_count > 0:
        print(f"\n🎉 Successfully updated {updated_count} California city descriptions!")
        print("📋 Check your WordPress admin to verify the changes")
    else:
        print("\n⚠️ No California cities were updated. They may already have descriptions.")

if __name__ == "__main__":
    main()
