#!/usr/bin/env python3
from core import should_block_title
from core.constants import TITLE_BLOCKLIST_PATTERNS
import re

# Test the specific referral titles that are published
referral_titles = [
    "Touchmark at Meadow Lake Village – Do Not Work With Referral Companies",
    "Niitsuma Living Center – Does Not Pay Referral Agents",
    "Frasier Meadows – Do Not Work With Referral Agents",
    "Barber Station Assisted Living And Memory Care Long Wait List No Referral Fee",
    "Rancho Montanes Low Income 55 Housing Good Referral But No Referral Fee",
    "Rancho Ciello Low Income 55 Apartments No Referral Fee But Good To Refer"
]

print("Testing referral titles against current patterns:")
print("=" * 80)

for title in referral_titles:
    blocked = should_block_title(title)
    print(f"\nTitle: {title}")
    print(f"Blocked: {blocked}")

    if not blocked:
        print("NOT BLOCKED - Matching patterns that should catch this:")
        title_lower = title.lower().strip()
        for pattern in TITLE_BLOCKLIST_PATTERNS:
            if re.search(pattern, title_lower, re.IGNORECASE):
                print(f"  ✓ {pattern}")
        print("  No patterns matched!")

print("\n" + "=" * 80)
print("Current TITLE_BLOCKLIST_PATTERNS:")
for i, pattern in enumerate(TITLE_BLOCKLIST_PATTERNS, 1):
    print(f"{i:2d}. {pattern}")
