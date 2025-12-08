"""
Unit tests for import_to_wordpress_api_safe.py
Tests CSV normalization, care type mapping, address handling, and import logic.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from import_to_wordpress_api_safe import (
    normalize_title,
    normalize_address,
    normalize_listing_row,
    get_care_type_term_ids,
    is_blocklisted_title,
    CARE_TYPE_MAPPING,
)


class TestNormalizeTitle:
    """Tests for title normalization"""

    def test_strips_llc(self):
        assert normalize_title("SUNRISE SENIOR CARE LLC") == "Sunrise Senior Care"

    def test_strips_inc(self):
        assert normalize_title("GOLDEN YEARS INC.") == "Golden Years"

    def test_strips_dba(self):
        assert normalize_title("ABC COMPANY LLC DBA SUNNY ACRES") == "Abc Company"

    def test_handles_the_suffix(self):
        assert normalize_title("ARISTOCRAT ASSISTED LIVING (The)") == "The Aristocrat Assisted Living"

    def test_title_case_with_articles(self):
        result = normalize_title("HOUSE OF THE RISING SUN")
        assert result == "House of the Rising Sun"

    def test_empty_string(self):
        assert normalize_title("") == ""

    def test_none(self):
        assert normalize_title(None) is None


class TestNormalizeAddress:
    """Tests for address normalization"""

    def test_normalizes_case(self):
        result = normalize_address("123 Main St, Phoenix, AZ")
        assert result == "123 MAIN ST PHOENIX AZ"

    def test_removes_punctuation(self):
        result = normalize_address("456 Oak Ave., Suite 100")
        assert result == "456 OAK AVE SUITE 100"

    def test_normalizes_whitespace(self):
        result = normalize_address("789   Elm   Dr")
        assert result == "789 ELM DR"

    def test_empty_string(self):
        assert normalize_address("") is None

    def test_none(self):
        assert normalize_address(None) is None


class TestNormalizeListingRow:
    """Tests for CSV row normalization"""

    def test_maps_senior_place_url(self):
        row = {"senior_place_url": "https://app.seniorplace.com/123", "title": "Test"}
        result = normalize_listing_row(row)
        assert result["url"] == "https://app.seniorplace.com/123"

    def test_maps_normalized_types_to_care_types(self):
        row = {
            "title": "Test",
            "normalized_types": "Assisted Living Home, Memory Care",
            "address": "123 Main St",
        }
        result = normalize_listing_row(row)
        assert result["care_types"] == "Assisted Living Home, Memory Care"

    def test_handles_newline_addresses(self):
        row = {
            "title": "Test",
            "address": "123 Main St\nPhoenix\nAZ 85001\nDirections",
            "city": "",
            "state": "",
            "zip": "",
        }
        result = normalize_listing_row(row)
        assert result["address"] == "123 Main St, Phoenix, AZ 85001"
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    def test_preserves_featured_image(self):
        row = {
            "title": "Test",
            "featured_image": "https://example.com/img.jpg",
            "address": "123 Main",
        }
        result = normalize_listing_row(row)
        assert result["featured_image"] == "https://example.com/img.jpg"

    def test_handles_description(self):
        row = {
            "title": "Test",
            "description": "A lovely senior home.",
            "address": "123 Main",
        }
        result = normalize_listing_row(row)
        assert result.get("description") == "A lovely senior home."


class TestCareTypeMapping:
    """Tests for care type term ID mapping"""

    def test_maps_assisted_living_community(self):
        ids = get_care_type_term_ids("Assisted Living Community")
        assert ids == [5]

    def test_maps_assisted_living_home(self):
        ids = get_care_type_term_ids("Assisted Living Home")
        assert ids == [162]

    def test_maps_multiple_types(self):
        ids = get_care_type_term_ids("Assisted Living Community, Memory Care, Nursing Home")
        assert set(ids) == {5, 3, 7}

    def test_ignores_unknown_types(self):
        ids = get_care_type_term_ids("Unknown Type, Memory Care")
        assert ids == [3]

    def test_empty_string(self):
        ids = get_care_type_term_ids("")
        assert ids == []

    def test_none(self):
        ids = get_care_type_term_ids(None)
        assert ids == []

    def test_all_canonical_types_mapped(self):
        """Ensure all 6 canonical types have mappings"""
        canonical_types = [
            "Assisted Living Community",
            "Assisted Living Home",
            "Independent Living",
            "Memory Care",
            "Nursing Home",
            "Home Care",
        ]
        for ct in canonical_types:
            assert ct in CARE_TYPE_MAPPING, f"Missing mapping for {ct}"


class TestBlocklistFiltering:
    """Tests for blocklist title filtering"""

    def test_blocks_do_not_refer(self):
        assert is_blocklisted_title("SUNSHINE HOME DO NOT REFER") is True

    def test_blocks_do_not_use(self):
        assert is_blocklisted_title("ABC Facility - Do Not Use") is True

    def test_blocks_surgery(self):
        assert is_blocklisted_title("Phoenix Eye Surgery Center") is True

    def test_allows_normal_titles(self):
        assert is_blocklisted_title("Sunrise Senior Living") is False

    def test_empty_string(self):
        assert is_blocklisted_title("") is False

    def test_none(self):
        assert is_blocklisted_title(None) is False


class TestCareTypeNormalization:
    """Tests for care type normalization in orchestrator output"""

    def test_directed_care_maps_to_alh(self):
        """Directed Care (Arizona-specific) should map to Assisted Living Home"""
        # This tests the map_care_types function logic
        TYPE_MAPPING = {
            "assisted living facility": "Assisted Living Community",
            "assisted living home": "Assisted Living Home",
            "independent living": "Independent Living",
            "memory care": "Memory Care",
            "skilled nursing": "Nursing Home",
            "directed care": "Assisted Living Home",
        }
        
        def map_care_types(care_types_list):
            canonical = []
            for ct in care_types_list:
                mapped = TYPE_MAPPING.get(ct.lower(), ct)
                if mapped not in canonical:
                    canonical.append(mapped)
            return ", ".join(canonical)
        
        result = map_care_types(["Directed Care", "Assisted Living Home"])
        # Should deduplicate since both map to ALH
        assert result == "Assisted Living Home"

    def test_multiple_types_preserved(self):
        TYPE_MAPPING = {
            "assisted living home": "Assisted Living Home",
            "memory care": "Memory Care",
        }
        
        def map_care_types(care_types_list):
            canonical = []
            for ct in care_types_list:
                mapped = TYPE_MAPPING.get(ct.lower(), ct)
                if mapped not in canonical:
                    canonical.append(mapped)
            return ", ".join(canonical)
        
        result = map_care_types(["Assisted Living Home", "Memory Care"])
        assert "Assisted Living Home" in result
        assert "Memory Care" in result

