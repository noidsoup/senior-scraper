#!/usr/bin/env python3
import requests
import os
from requests.auth import HTTPBasicAuth

WP_URL = os.getenv('WP_URL', 'https://aplaceforseniorscms.kinsta.cloud')
WP_USER = os.getenv('WP_USER', 'nicholas_editor')
WP_PASS = os.getenv('WP_PASS', '3oiO dmah Ao7w Y8M7 5RKF rVrk')

# Get the specific listing
listing_id = 49499  # A Plus Paradise Valley Assisted Living
url = f'{WP_URL}/wp-json/wp/v2/listing/{listing_id}'
response = requests.get(url, auth=HTTPBasicAuth(WP_USER, WP_PASS))

if response.status_code == 200:
    data = response.json()
    print('Listing details:')
    print(f'ID: {data["id"]}')
    print(f'Title: {data["title"]["rendered"]}')
    print(f'Status: {data["status"]}')
    print(f'Date created: {data["date"]}')
    print(f'Date modified: {data["modified"]}')

    # Check if it has ACF fields (care types, etc.)
    acf = data.get('acf', {})
    if acf:
        print(f'ACF fields present: {list(acf.keys())}')
        if 'care_types' in acf:
            print(f'Care types: {acf["care_types"]}')
        if 'type' in acf:
            print(f'Type field: {acf["type"]}')
        if 'address' in acf:
            print(f'Address: {acf["address"]}')
    else:
        print('No ACF fields found')
else:
    print(f'Error: {response.status_code} - {response.text[:200]}')
