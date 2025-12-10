"""
Shared utility functions
"""

import re
from typing import List, Optional
from .constants import CARE_TYPE_MAPPING, NOISE_PATTERNS, TITLE_BLOCKLIST_PATTERNS


def map_care_types_to_canonical(care_types_list: Optional[List[str]]) -> List[str]:
    """
    Map raw Senior Place care types to WordPress canonical types.
    Filters out non-care-types (room types, bathroom types, etc.)
    
    Args:
        care_types_list: List of care type strings from Senior Place
    
    Returns:
        List of canonical care type strings
    """
    if not care_types_list:
        return []
    
    canonical = []
    for ct in care_types_list:
        ct_lower = ct.lower().strip()
        if not ct_lower:
            continue
        
        # Filter out noise patterns
        if any(noise in ct_lower for noise in NOISE_PATTERNS):
            continue
        
        # Direct mapping
        mapped = CARE_TYPE_MAPPING.get(ct_lower)
        
        # Fallback substring matching for partial labels
        if not mapped:
            if 'assisted living' in ct_lower:
                mapped = 'Assisted Living Community'
            elif 'independent' in ct_lower:
                mapped = 'Independent Living'
            elif 'memory care' in ct_lower:
                mapped = 'Memory Care'
            elif 'nursing' in ct_lower:
                mapped = 'Nursing Home'
            elif 'home care' in ct_lower or 'home health' in ct_lower or 'in-home care' in ct_lower:
                mapped = 'Home Care'
        
        if mapped and mapped not in canonical:
            canonical.append(mapped)
    
    return sorted(canonical)


def should_block_title(title: str) -> bool:
    """
    Check if a listing title should be blocked from scraping/import.

    Titles containing operational notes, restrictions, or non-standard content
    should be filtered out to maintain data quality.

    Args:
        title: The listing title to check

    Returns:
        True if the title should be blocked, False otherwise
    """
    if not title:
        return True

    title_lower = title.lower().strip()

    # Check against all blocklist patterns
    for pattern in TITLE_BLOCKLIST_PATTERNS:
        if re.search(pattern, title_lower, re.IGNORECASE):
            return True

    return False


def clean_listing_title(title: str) -> str:
    """
    Clean and normalize a listing title by removing unwanted suffixes/comments.

    Args:
        title: Raw title from Senior Place

    Returns:
        Cleaned title suitable for import
    """
    if not title:
        return ""

    # Remove common unwanted suffixes
    title = re.sub(r'\s*/.*', '', title)  # Remove everything after first slash
    title = re.sub(r'\s*\.\.\..*', '', title)  # Remove trailing dots and comments
    title = re.sub(r'\s*\([^)]*do not[^)]*\)', '', title, flags=re.IGNORECASE)  # Remove (do not...) comments

    # Clean up extra whitespace
    title = re.sub(r'\s+', ' ', title).strip()

    return title

