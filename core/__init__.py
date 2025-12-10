"""
Senior Scraper Core Module
Shared constants, models, utilities, and configuration
"""

from .constants import (
    CARE_TYPE_MAPPING,
    NOISE_PATTERNS,
    SUPPORTED_STATES,
    BLOCKLIST_PATTERNS,
    TITLE_BLOCKLIST_PATTERNS,
    CANONICAL_CARE_TYPES,
)
from .models import Listing, ScrapeResult, ImportResult, ScrapeStats
from .config import Settings, get_settings
from .exceptions import (
    SeniorScraperError,
    AuthenticationError,
    RateLimitError,
    DataValidationError,
    WordPressAPIError,
)
from .utils import map_care_types_to_canonical, should_block_title, clean_listing_title

__all__ = [
    # Constants
    'CARE_TYPE_MAPPING',
    'NOISE_PATTERNS',
    'SUPPORTED_STATES',
    'BLOCKLIST_PATTERNS',
    'TITLE_BLOCKLIST_PATTERNS',
    'CANONICAL_CARE_TYPES',
    # Models
    'Listing',
    'ScrapeResult',
    'ImportResult',
    'ScrapeStats',
    # Config
    'Settings',
    'get_settings',
    # Exceptions
    'SeniorScraperError',
    'AuthenticationError',
    'RateLimitError',
    'DataValidationError',
    'WordPressAPIError',
    # Utils
    'map_care_types_to_canonical',
    'should_block_title',
    'clean_listing_title',
]

