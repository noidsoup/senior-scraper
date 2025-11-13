#!/usr/bin/env python3
"""
Check WordPress category term counts and sample listing assignments for community types.
Uses public REST API; validates whether listings are actually assigned to these terms.
"""

import requests

WP_BASE = 'https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2'
TYPE_SLUGS = [
    'assisted-living-community',
    'assisted-living-home',
    'independent-living',
    'home-care',
    'memory-care',
    'nursing-home',
]


def fetch_json(url: str):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.json()
        return {'__http_status__': r.status_code}
    except Exception as e:
        return {'__error__': str(e)}


def main():
    print('🔎 Checking category terms and listing assignments')
    for slug in TYPE_SLUGS:
        cats = fetch_json(f"{WP_BASE}/categories?slug={slug}")
        if isinstance(cats, dict):
            print(f"{slug}: error {cats}")
            continue
        if not cats:
            print(f"{slug}: not found")
            continue
        term = cats[0]
        term_id = term.get('id')
        count = term.get('count')
        name = term.get('name')
        print(f"- {name} ({slug}) → term_id={term_id}, count={count}")
        # sample up to 3 listings assigned to this category
        listings = fetch_json(f"{WP_BASE}/listing?categories={term_id}&per_page=3")
        if isinstance(listings, dict):
            print(f"  listings query error: {listings}")
            continue
        print(f"  assigned listings: {len(listings)} sample")
        for item in listings:
            title = item.get('title', {}).get('rendered', '')
            print(f"    · {title[:70]}")

    print('\nℹ️ If counts are unexpectedly low (e.g., Memory Care=1), the ACF taxonomy field may not be set to "Save Terms" or the import only updated ACF postmeta without syncing taxonomy relationships. Enable Save Terms on the ACF field and re-save posts, or assign categories during import, or run a sync that calls wp_set_post_terms().')


if __name__ == '__main__':
    main()
