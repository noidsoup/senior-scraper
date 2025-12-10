"""
Shared constants for Senior Scraper
"""

# Canonical care types (WordPress taxonomy)
CANONICAL_CARE_TYPES = [
    'Assisted Living Community',
    'Assisted Living Home',
    'Independent Living',
    'Memory Care',
    'Nursing Home',
    'Home Care',
]

# Mapping from Senior Place care types (lowercase) to WordPress canonical types
CARE_TYPE_MAPPING = {
    'assisted living facility': 'Assisted Living Community',
    'assisted living home': 'Assisted Living Home',
    'independent living': 'Independent Living',
    'memory care': 'Memory Care',
    'skilled nursing': 'Nursing Home',
    'continuing care retirement community': 'Assisted Living Community',
    'ccrc': 'Assisted Living Community',
    'in-home care': 'Home Care',
    'home health': 'Home Care',
    'hospice': 'Home Care',
    'respite care': 'Assisted Living Community',
    'directed care': 'Assisted Living Home',  # Arizona-specific
    'personal care': 'Assisted Living Home',
    'supervisory care': 'Assisted Living Home',
}

# Patterns to filter out (not care types)
NOISE_PATTERNS = [
    'private pay',
    'medicaid',
    'contract',
    'cane',
    'walker',
    'wheelchair',
    'some memory loss',
    'private',
    'shared',
    'studio',
    'one bedroom',
    'two bedroom',
    'bathroom',
]

# Supported states for scraping
SUPPORTED_STATES = ['AZ', 'CA', 'CO', 'ID', 'NM', 'UT']

# State abbreviation to full name mapping
STATE_NAMES = {
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'ID': 'Idaho',
    'NM': 'New Mexico',
    'UT': 'Utah',
}

# Blocklist patterns for titles that should never be imported
BLOCKLIST_PATTERNS = [
    r"\bdo\s+not\s+refer\b",
    r"\bdo\s+not\s+use\b",
    r"\bnot\s+signing\b",
    r"\bsurgery\b",
    r"\bsurgical\b",
]

# Title filtering patterns - exclude listings with these in titles during scraping
TITLE_BLOCKLIST_PATTERNS = [
    # Original patterns
    r"\bdo\s+not\s+refer\b",
    r"\bdo\s+not\s+use\b",
    r"\bnot\s+signing\b",
    r"\bsurgery\b",
    r"\bsurgical\b",
    r"\btbi\b",  # Traumatic Brain Injury specific
    r"\bonly\b.*\bagencies?\b",  # "only" + "agency/agencies"
    r"\bnot\s+working\s+with\b",  # "not working with"
    r"\betc\.+",  # "etc..."
    r"\.\.\.+",  # Multiple dots (indicating trailing comments)
    r"/.*only",  # Slash followed by "only"
    r"\bprivate\s+only\b",  # "private only"
    r"\breferral\s+only\b",  # "referral only"
    r"\bspecific\s+clients?\b",  # "specific client(s)"

    # Additional patterns for operational notes
    r"\bnot\s+adding\b",
    r"\bnot\s+accepting\b",
    r"\bno\s+longer\s+accepting\b",
    r"\bat\s+this\s+time\b",
    r"\bcurrently\s+not\b",
    r"\btemporarily\s+closed\b",
    r"\bunder\s+construction\b",
    r"\bcoming\s+soon\b",
    r"\bcall\s+for\s+availability\b",
    r"\breferral.*only\b",
    r"\bonly.*referral\b",
    r"\bagency.*only\b",
    r"\bonly.*agency\b",
    r"\bprivate.*pay.*only\b",
    r"\bmedicaid.*only\b",
    r"\binsurance.*only\b",

    # Case variations and common phrases
    r"not adding referral",
    r"not accepting referral",
    r"no referral agents",
    r"referral agents not",
    r"agents not accepted",
    r"not working with agencies",
    r"agencies not welcome",

    # Additional referral-related patterns
    r"do not work with referral",
    r"does not pay referral",
    r"no referral fee",
    r"not pay referral",
    r"referral fee",
    r"referral companies",
    r"referral agents",
    r"work with referral",
    r"pay referral",
]

