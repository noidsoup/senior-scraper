#!/usr/bin/env python3
from core import should_block_title

test_titles = [
    'Garden Plaza of the Valley View - NOT ADDING REFERRAL agents at this time',
    'Normal Assisted Living Facility',
    'Another Home - Not Accepting Referrals Currently',
    'Good Senior Care - No Referral Agents Please'
]

print('Testing updated title blocking:')
for title in test_titles:
    blocked = should_block_title(title)
    status = 'BLOCKED' if blocked else 'ALLOWED'
    print(f'{status}: "{title}"')
