#!/usr/bin/env python3
"""
EMERGENCY: Clean up inappropriate listing titles in WordPress
Changes posts with problematic titles from 'publish' to 'draft' status
"""

import requests
import json
import time
import os
from datetime import datetime
from requests.auth import HTTPBasicAuth

# Load WordPress credentials
WP_URL = os.getenv("WP_URL", "https://aplaceforseniorscms.kinsta.cloud")
WP_USER = os.getenv("WP_USER", "nicholas_editor")
WP_PASS = os.getenv("WP_PASS", "3oiO dmah Ao7w Y8M7 5RKF rVrk")

# Import title blocking logic
import sys
sys.path.insert(0, '.')
from core import should_block_title

def get_all_listings():
    """Fetch all published listings from WordPress"""
    listings = []
    page = 1
    per_page = 100  # Max allowed by WP API

    print(f"Fetching all published listings from {WP_URL}...")

    while True:
        url = f"{WP_URL}/wp-json/wp/v2/listing"
        params = {
            'status': 'publish',
            'per_page': per_page,
            'page': page,
            '_fields': 'id,title,slug,status'  # Only fetch needed fields
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            batch = response.json()
            if not batch:
                break

            listings.extend(batch)
            print(f"Fetched page {page}: {len(batch)} listings (total: {len(listings)})")

            # Check if there are more pages
            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if page >= total_pages:
                break

            page += 1
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    return listings

def identify_problematic_titles(listings):
    """Identify listings with titles that should be blocked"""
    problematic = []
    blocked_count = 0
    clean_count = 0

    print("Analyzing titles for problematic content...")
    print(f"Processing {len(listings)} total listings...")

    # Sample first 10 for detailed logging
    sample_size = min(10, len(listings))

    for i, listing in enumerate(listings, 1):
        if i % 500 == 0:
            print(f"Analyzed {i}/{len(listings)} listings... ({blocked_count} blocked, {clean_count} clean)")

        title = listing['title']['rendered'] if isinstance(listing['title'], dict) else listing['title']

        # Show detailed analysis for first few
        if i <= sample_size:
            is_blocked = should_block_title(title)
            status = "BLOCKED" if is_blocked else "CLEAN"
            print(f"[{i:2d}] {status}: '{title}' (ID: {listing['id']})")

        if should_block_title(title):
            blocked_count += 1
            problematic.append({
                'id': listing['id'],
                'title': title,
                'slug': listing.get('slug', ''),
                'url': f"{WP_URL}/wp-admin/post.php?post={listing['id']}&action=edit"
            })
        else:
            clean_count += 1

    print("\nANALYSIS COMPLETE:")
    print(f"Total listings analyzed: {len(listings)}")
    print(f"Clean titles: {clean_count}")
    print(f"Problematic titles: {len(problematic)}")
    if len(listings) > 0:
        percentage = (len(problematic) / len(listings)) * 100
        print(".1f")

    if problematic:
        print(f"\nFirst 10 problematic titles:")
        for i, item in enumerate(problematic[:10], 1):
            print(f"{i}. '{item['title']}' (ID: {item['id']})")

    return problematic

def change_to_draft(listing_id, title):
    """Change a listing from publish to draft status"""
    url = f"{WP_URL}/wp-json/wp/v2/listing/{listing_id}"

    data = {
        'status': 'draft'
    }

    try:
        response = requests.post(
            url,
            json=data,
            auth=HTTPBasicAuth(WP_USER, WP_PASS),
            timeout=30
        )
        response.raise_for_status()

        print(f"Changed to draft: {title} (ID: {listing_id})")
        return True

    except Exception as e:
        print(f"Failed to change {title} (ID: {listing_id}): {e}")
        return False

def main():
    """Main cleanup process"""
    print("EMERGENCY TITLE CLEANUP STARTED")
    print("=" * 60)

    # Step 1: Get all published listings
    listings = get_all_listings()
    print(f"Total published listings found: {len(listings)}")

    if not listings:
        print("No listings found. Check WordPress credentials.")
        return

    # Step 2: Identify problematic titles
    problematic = identify_problematic_titles(listings)

    if not problematic:
        print("No problematic titles found!")
        return

    # Step 3: Show summary
    print("\nPROBLEMATIC TITLES FOUND:")
    print("-" * 40)
    for i, item in enumerate(problematic[:10], 1):  # Show first 10
        print(f"{i:2d}. {item['title']}")
    if len(problematic) > 10:
        print(f"... and {len(problematic) - 10} more")

    # Step 4: Show what would be changed
    print(f"\nWould change {len(problematic)} listings from PUBLISHED to DRAFT")

    # Show detailed list of problematic titles
    print("\nDETAILED LIST:")
    print("-" * 80)
    for i, item in enumerate(problematic, 1):
        print("2d")
        if i >= 20:  # Limit output
            print(f"... and {len(problematic) - 20} more")
            break

    # Step 5: Ask user what to do
    print(f"\nOPTIONS:")
    print("1. Proceed with changing all to draft")
    print("2. Show only count (no details)")
    print("3. Cancel")

    choice = input("\nChoose option (1/2/3): ").strip()

    if choice == "1":
        # Process the changes
        print("\nStarting title cleanup...")
        successful = 0
        failed = 0

        for item in problematic:
            if change_to_draft(item['id'], item['title']):
                successful += 1
            else:
                failed += 1

            # Rate limiting
            time.sleep(0.2)

        # Final report
        print("\n" + "=" * 60)
        print("CLEANUP COMPLETE")
        print("=" * 60)
        print(f"Successfully changed: {successful} listings")
        print(f"Failed to change: {failed} listings")
        print(f"Total processed: {len(problematic)} listings")
        print("\nThese listings are now DRAFTS and won't appear on the live site.")

    elif choice == "2":
        print(f"\nTotal problematic titles found: {len(problematic)}")
        print("No changes made.")

    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()
