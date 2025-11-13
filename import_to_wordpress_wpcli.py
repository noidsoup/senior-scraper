#!/usr/bin/env python3
"""
WordPress WP-CLI Import Script
Imports Senior Place listings from CSV to WordPress using WP-CLI

Usage:
    python3 import_to_wordpress_wpcli.py <csv_file> [--dry-run] [--wp-path=/path/to/wp]

Example:
    python3 import_to_wordpress_wpcli.py AZ_seniorplace_data_20251030.csv --dry-run
    python3 import_to_wordpress_wpcli.py AZ_seniorplace_data_20251030.csv --wp-path=/var/www/html
"""

import csv
import subprocess
import sys
import argparse
import json
from pathlib import Path

# Care type mapping to WordPress taxonomy term IDs
# You'll need to get these from your WordPress site first
CARE_TYPE_MAPPING = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}

# State mapping to WordPress taxonomy term IDs
# You'll need to get these from your WordPress site first
STATE_MAPPING = {
    'AZ': 0,  # To be filled
    'CA': 0,  # To be filled
    'CO': 0,  # To be filled
    'ID': 0,  # To be filled
    'NM': 0,  # To be filled
    'UT': 953,  # We know this one from the test
}


def run_wp_cli(args, wp_path=None):
    """Run a WP-CLI command and return the output"""
    cmd = ['wp'] + args
    if wp_path:
        cmd.extend(['--path=' + wp_path])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"  ❌ WP-CLI Error: {e.stderr}")
        return None
    except FileNotFoundError:
        print("  ❌ Error: WP-CLI not found. Install it first:")
        print("     curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar")
        print("     chmod +x wp-cli.phar")
        print("     sudo mv wp-cli.phar /usr/local/bin/wp")
        sys.exit(1)


def check_existing_listing(url, wp_path=None):
    """Check if a listing with this Senior Place URL already exists"""
    result = run_wp_cli([
        'post', 'list',
        '--post_type=listing',
        '--meta_key=senior_place_url',
        f'--meta_value={url}',
        '--field=ID',
        '--format=json'
    ], wp_path)
    
    if result:
        try:
            posts = json.loads(result)
            return posts[0] if posts else None
        except:
            return None
    return None


def create_listing(listing, wp_path=None, dry_run=False):
    """Create a WordPress listing post with ACF fields"""
    
    title = listing['title']
    url = listing['url']
    address = listing['address']
    city = listing['city']
    state = listing['state']
    zip_code = listing['zip']
    featured_image = listing['featured_image']
    care_types = listing['care_types']
    
    if dry_run:
        print(f"  ✅ Would create: {title}")
        print(f"     URL: {url}")
        print(f"     Address: {address}")
        print(f"     State: {state}")
        print(f"     Care Types: {care_types}")
        return 'DRY_RUN'
    
    # Create the post
    post_id = run_wp_cli([
        'post', 'create',
        '--post_type=listing',
        f'--post_title={title}',
        '--post_status=draft',
        '--porcelain'
    ], wp_path)
    
    if not post_id:
        return None
    
    print(f"  ✅ Created post ID: {post_id}")
    
    # Set ACF fields
    run_wp_cli(['post', 'meta', 'update', post_id, 'senior_place_url', url], wp_path)
    run_wp_cli(['post', 'meta', 'update', post_id, 'address', address], wp_path)
    
    if city:
        run_wp_cli(['post', 'meta', 'update', post_id, '_city', city], wp_path)
    
    if zip_code:
        run_wp_cli(['post', 'meta', 'update', post_id, '_zip', zip_code], wp_path)
    
    # Set state taxonomy (if we have the term ID)
    if state in STATE_MAPPING and STATE_MAPPING[state] > 0:
        run_wp_cli(['post', 'term', 'add', post_id, 'location', str(STATE_MAPPING[state])], wp_path)
    
    # Set care type taxonomy (if we have the term IDs)
    if care_types:
        for care_type in care_types.split(','):
            care_type = care_type.strip()
            if care_type in CARE_TYPE_MAPPING:
                term_id = CARE_TYPE_MAPPING[care_type]
                run_wp_cli(['post', 'term', 'add', post_id, 'listing_type', str(term_id)], wp_path)
    
    # Set featured image URL (for later download)
    if featured_image:
        run_wp_cli(['post', 'meta', 'update', post_id, '_thumbnail_url', featured_image], wp_path)
    
    return post_id


def import_csv(csv_file, wp_path=None, dry_run=False):
    """Import all listings from CSV file"""
    
    if not Path(csv_file).exists():
        print(f"❌ Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    print("=" * 80)
    print("WordPress WP-CLI Import")
    print("=" * 80)
    print(f"CSV File: {csv_file}")
    print(f"WP Path: {wp_path or 'auto-detect'}")
    print(f"Dry Run: {dry_run}")
    print("=" * 80)
    print()
    
    # Test WP-CLI connection
    print("🔍 Testing WP-CLI connection...")
    site_url = run_wp_cli(['option', 'get', 'siteurl'], wp_path)
    if site_url:
        print(f"✅ Connected to WordPress: {site_url}\n")
    else:
        print("❌ Failed to connect to WordPress")
        sys.exit(1)
    
    # Read and import
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        listings = list(reader)
    
    total = len(listings)
    created = 0
    skipped = 0
    errors = 0
    
    print(f"📊 Total listings to process: {total}\n")
    
    for i, listing in enumerate(listings, 1):
        title = listing['title']
        url = listing['url']
        
        print(f"[{i}/{total}] Processing: {title[:60]}")
        
        # Check if exists
        existing_id = check_existing_listing(url, wp_path)
        if existing_id:
            print(f"  ⏭️  Skipped (already exists, ID: {existing_id})")
            skipped += 1
            continue
        
        # Create listing
        post_id = create_listing(listing, wp_path, dry_run)
        
        if post_id:
            created += 1
        else:
            errors += 1
        
        # Progress update every 25 listings
        if i % 25 == 0:
            print()
            print(f"📈 Progress: {i}/{total} (Created: {created}, Skipped: {skipped}, Errors: {errors})")
            print()
    
    # Final summary
    print()
    print("=" * 80)
    print("✅ Import Complete!")
    print("=" * 80)
    print(f"Total processed: {total}")
    print(f"Created: {created}")
    print(f"Skipped (duplicates): {skipped}")
    print(f"Errors: {errors}")
    print("=" * 80)
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN. No changes were made.")
        print("   Remove --dry-run flag to perform actual import.")


def main():
    parser = argparse.ArgumentParser(description='Import Senior Place listings to WordPress via WP-CLI')
    parser.add_argument('csv_file', help='CSV file to import')
    parser.add_argument('--dry-run', action='store_true', help='Preview import without making changes')
    parser.add_argument('--wp-path', help='Path to WordPress installation')
    
    args = parser.parse_args()
    
    import_csv(args.csv_file, wp_path=args.wp_path, dry_run=args.dry_run)


if __name__ == '__main__':
    main()

