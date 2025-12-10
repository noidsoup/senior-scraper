#!/usr/bin/env python3
from core import should_block_title

# Test the titles the user mentioned
test_titles = [
    'jendrew assisted living',
    'homebridge',
    'Garden Plaza of Valley View – Not Adding Referral Agents at This Time',
    'Normal Assisted Living Facility'
]

print('Testing user-mentioned titles:')
for title in test_titles:
    blocked = should_block_title(title)
    status = 'BLOCKED' if blocked else 'ALLOWED'
    print(f'{status}: "{title}"')
