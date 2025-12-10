#!/usr/bin/env python3
from core import should_block_title
from core.constants import TITLE_BLOCKLIST_PATTERNS
import re

title = 'A Plus Paradise Valley Assisted Living'
blocked = should_block_title(title)
print(f'Title: "{title}"')
print(f'Blocked: {blocked}')

if blocked:
    title_lower = title.lower().strip()
    print('Matching patterns:')
    for pattern in TITLE_BLOCKLIST_PATTERNS:
        if re.search(pattern, title_lower, re.IGNORECASE):
            print(f'  - {pattern}')
