#!/usr/bin/env python3
"""
Get WordPress Term IDs for States and Care Types

This script fetches the term IDs from WordPress that you need for import mapping.
Run this FIRST before running the import script.

Usage:
    python3 get_wordpress_term_ids.py [--wp-path=/path/to/wp]
"""

import subprocess
import json
import argparse


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
        print(f"❌ WP-CLI Error: {e.stderr}")
        return None


def get_term_ids(taxonomy, wp_path=None):
    """Get all terms from a taxonomy"""
    result = run_wp_cli([
        'term', 'list', taxonomy,
        '--format=json',
        '--fields=term_id,name,slug'
    ], wp_path)
    
    if result:
        try:
            return json.loads(result)
        except:
            return []
    return []


def main():
    parser = argparse.ArgumentParser(description='Get WordPress term IDs for import mapping')
    parser.add_argument('--wp-path', help='Path to WordPress installation')
    args = parser.parse_args()
    
    print("=" * 80)
    print("WordPress Term ID Lookup")
    print("=" * 80)
    print()
    
    # Test connection
    print("🔍 Testing WP-CLI connection...")
    site_url = run_wp_cli(['option', 'get', 'siteurl'], args.wp_path)
    if site_url:
        print(f"✅ Connected to: {site_url}\n")
    else:
        print("❌ Failed to connect to WordPress")
        return
    
    # Get location/state terms
    print("📍 Fetching Location/State Terms:")
    print("-" * 80)
    locations = get_term_ids('location', args.wp_path)
    
    if locations:
        # Filter for our 6 states
        target_states = ['Arizona', 'California', 'Colorado', 'Idaho', 'New Mexico', 'Utah']
        state_map = {}
        
        for term in locations:
            if term['name'] in target_states:
                # Get state abbreviation
                abbrev = {
                    'Arizona': 'AZ',
                    'California': 'CA',
                    'Colorado': 'CO',
                    'Idaho': 'ID',
                    'New Mexico': 'NM',
                    'Utah': 'UT'
                }.get(term['name'])
                
                if abbrev:
                    state_map[abbrev] = term['term_id']
                    print(f"  {term['name']:15} → ID: {term['term_id']:5} ('{abbrev}')")
        
        print()
        print("Python mapping:")
        print("STATE_MAPPING = {")
        for abbrev in ['AZ', 'CA', 'CO', 'ID', 'NM', 'UT']:
            term_id = state_map.get(abbrev, 0)
            print(f"    '{abbrev}': {term_id},")
        print("}")
    else:
        print("  No location terms found")
    
    print()
    
    # Get care type terms
    print("🏥 Fetching Care Type Terms:")
    print("-" * 80)
    care_types = get_term_ids('listing_type', args.wp_path)
    
    if care_types:
        care_type_map = {}
        
        # Map to our canonical types
        canonical = {
            'Assisted Living Community': ['Assisted Living Community', 'Assisted Living Facility'],
            'Assisted Living Home': ['Assisted Living Home'],
            'Independent Living': ['Independent Living'],
            'Memory Care': ['Memory Care'],
            'Nursing Home': ['Nursing Home', 'Skilled Nursing'],
            'Home Care': ['Home Care', 'In-Home Care'],
        }
        
        for term in care_types:
            for canonical_name, variations in canonical.items():
                if term['name'] in variations:
                    care_type_map[canonical_name] = term['term_id']
                    print(f"  {term['name']:30} → ID: {term['term_id']:5} ('{canonical_name}')")
        
        print()
        print("Python mapping:")
        print("CARE_TYPE_MAPPING = {")
        for name in ['Assisted Living Community', 'Assisted Living Home', 'Independent Living', 
                     'Memory Care', 'Nursing Home', 'Home Care']:
            term_id = care_type_map.get(name, 0)
            print(f"    '{name}': {term_id},")
        print("}")
    else:
        print("  No care type terms found")
    
    print()
    print("=" * 80)
    print("✅ Copy the mappings above into import_to_wordpress_wpcli.py")
    print("=" * 80)


if __name__ == '__main__':
    main()

