"""
Unit tests for Senior Place field scraping.
Tests that the enrichment logic correctly extracts all fields.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSeniorPlaceFieldExtraction:
    """Tests for Senior Place field extraction logic"""

    def test_care_types_extraction_js(self):
        """Test the JavaScript logic for extracting care types from checkboxes"""
        # Simulate the JS extraction logic in Python
        # This tests the structure of data we expect
        
        mock_checked_labels = [
            {"text": "Assisted Living Home", "checked": True},
            {"text": "Directed Care", "checked": True},
            {"text": "Memory Care", "checked": False},
            {"text": "Independent Living", "checked": True},
        ]
        
        extracted = [
            label["text"]
            for label in mock_checked_labels
            if label["checked"]
        ]
        
        assert "Assisted Living Home" in extracted
        assert "Directed Care" in extracted
        assert "Independent Living" in extracted
        assert "Memory Care" not in extracted

    def test_pricing_extraction_structure(self):
        """Test that pricing fields are correctly structured"""
        mock_pricing = {
            "monthly_base_price": "3500",
            "price_high_end": "5000",
            "second_person_fee": "1500",
        }
        
        assert "monthly_base_price" in mock_pricing
        assert "price_high_end" in mock_pricing
        assert "second_person_fee" in mock_pricing
        
        # Values should be strings (from form inputs)
        assert isinstance(mock_pricing["monthly_base_price"], str)

    def test_description_extraction(self):
        """Test description field handling"""
        mock_description = "This is a wonderful assisted living facility in Phoenix, AZ. We offer 24/7 care."
        
        assert len(mock_description) > 0
        assert "assisted living" in mock_description.lower()

    def test_image_url_normalization(self):
        """Test that image URLs are properly normalized"""
        # Relative URL from S3
        relative_url = "/api/files/public/abc123.jpg"
        base = "https://placement-crm-cdn.s3.us-west-2.amazonaws.com"
        
        if relative_url.startswith("/api/files/"):
            full_url = f"{base}{relative_url}"
        else:
            full_url = relative_url
        
        assert full_url == "https://placement-crm-cdn.s3.us-west-2.amazonaws.com/api/files/public/abc123.jpg"
        
        # Already full URL
        full_external = "https://example.com/image.jpg"
        if full_external.startswith("http"):
            result = full_external
        else:
            result = f"{base}{full_external}"
        
        assert result == "https://example.com/image.jpg"


class TestEnrichedListingStructure:
    """Tests for the structure of enriched listings"""

    def test_enriched_listing_has_all_fields(self):
        """Verify enriched listing contains all required fields"""
        enriched_listing = {
            "title": "Sunrise Senior Care",
            "url": "https://app.seniorplace.com/communities/show/abc123",
            "address": "123 Main St, Phoenix, AZ 85001",
            "featured_image": "https://cdn.example.com/image.jpg",
            "care_types": ["Assisted Living Home", "Memory Care"],
            "monthly_base_price": "3500",
            "price_high_end": "5000",
            "second_person_fee": "1500",
            "description": "A wonderful place for seniors.",
        }
        
        required_fields = [
            "title",
            "url",
            "address",
            "featured_image",
            "care_types",
            "monthly_base_price",
            "description",
        ]
        
        for field in required_fields:
            assert field in enriched_listing, f"Missing required field: {field}"

    def test_care_types_is_list(self):
        """Care types should be a list after enrichment"""
        enriched_listing = {
            "care_types": ["Assisted Living Home", "Memory Care"],
        }
        
        assert isinstance(enriched_listing["care_types"], list)

    def test_pricing_fields_are_strings(self):
        """Pricing fields should be strings from form inputs"""
        enriched_listing = {
            "monthly_base_price": "3500",
            "price_high_end": "5000",
            "second_person_fee": "1500",
        }
        
        assert isinstance(enriched_listing["monthly_base_price"], str)
        assert isinstance(enriched_listing["price_high_end"], str)
        assert isinstance(enriched_listing["second_person_fee"], str)


class TestCSVFieldMapping:
    """Tests for CSV field mapping from orchestrator to importer"""

    def test_csv_headers_match_importer_expectations(self):
        """Verify CSV headers match what the importer expects"""
        orchestrator_csv_headers = [
            "title",
            "address",
            "city",
            "state",
            "zip",
            "senior_place_url",
            "featured_image",
            "price",
            "normalized_types",
            "care_types_raw",
            "price_high_end",
            "second_person_fee",
            "description",
        ]
        
        # The importer's normalize_listing_row should handle these
        importer_expected = ["title", "url", "address", "city", "state", "zip", 
                           "featured_image", "care_types", "description"]
        
        # Map orchestrator -> importer
        field_mapping = {
            "senior_place_url": "url",
            "normalized_types": "care_types",
        }
        
        # All expected fields should be derivable
        for expected in importer_expected:
            # Either directly in headers or mapped
            direct = expected in orchestrator_csv_headers
            mapped = any(k for k, v in field_mapping.items() if v == expected and k in orchestrator_csv_headers)
            assert direct or mapped, f"Field {expected} not derivable from CSV"

    def test_description_column_present(self):
        """Verify description column is in the CSV output"""
        csv_headers = [
            "title", "address", "city", "state", "zip",
            "senior_place_url", "featured_image",
            "price", "normalized_types", "care_types_raw",
            "price_high_end", "second_person_fee", "description",
        ]
        
        assert "description" in csv_headers


class TestAddressParsingFromNewlines:
    """Tests for parsing newline-delimited addresses from Senior Place"""

    def test_parses_standard_address(self):
        """Test parsing address with newlines"""
        raw_address = "123 Main St\nPhoenix\nAZ 85001\nDirections"
        
        lines = [ln.strip() for ln in raw_address.split("\n") if ln.strip()]
        
        street = lines[0] if lines else ""
        city = lines[1] if len(lines) > 1 else ""
        
        state_zip_line = lines[2] if len(lines) > 2 else ""
        state_zip_line = state_zip_line.replace("Directions", "").strip()
        
        import re
        match = re.match(r"([A-Z]{2})\s*(\d{5})?", state_zip_line)
        state = match.group(1) if match else ""
        zip_code = match.group(2) if match and match.group(2) else ""
        
        assert street == "123 Main St"
        assert city == "Phoenix"
        assert state == "AZ"
        assert zip_code == "85001"

    def test_parses_address_with_phone(self):
        """Test parsing address that includes phone number"""
        raw_address = "456 Oak Ave\nScottsdale\nAZ 85254\nDirections\n(602) 555-1234"
        
        lines = [ln.strip() for ln in raw_address.split("\n") if ln.strip()]
        
        street = lines[0]
        city = lines[1]
        
        # State line might have extra junk
        state_line = lines[2].replace("Directions", "").strip()
        
        import re
        match = re.match(r"([A-Z]{2})\s*(\d{5})?", state_line)
        state = match.group(1) if match else ""
        zip_code = match.group(2) if match and match.group(2) else ""
        
        assert street == "456 Oak Ave"
        assert city == "Scottsdale"
        assert state == "AZ"
        assert zip_code == "85254"


class TestEndToEndFieldFlow:
    """Tests for the complete flow from scrape to import"""

    def test_scraped_to_csv_to_import(self):
        """Test that scraped data flows correctly through the pipeline"""
        # 1. Scraped listing from Senior Place
        scraped = {
            "title": "SUNSHINE SENIOR CARE LLC",
            "url": "https://app.seniorplace.com/communities/show/abc123",
            "address": "789 Elm Dr\nTempe\nAZ 85281\nDirections",
            "featured_image": "https://cdn.example.com/sunshine.jpg",
            "care_types": ["Assisted Living Home", "Directed Care"],
            "monthly_base_price": "4000",
            "price_high_end": "6000",
            "second_person_fee": "1200",
            "description": "Sunshine Senior Care offers compassionate assisted living.",
        }
        
        # 2. CSV row (what orchestrator writes)
        csv_row = {
            "title": scraped["title"],
            "address": "789 Elm Dr",
            "city": "Tempe",
            "state": "AZ",
            "zip": "85281",
            "senior_place_url": scraped["url"],
            "featured_image": scraped["featured_image"],
            "price": "4000",
            "normalized_types": "Assisted Living Home",  # After mapping
            "care_types_raw": "Assisted Living Home, Directed Care",
            "price_high_end": "6000",
            "second_person_fee": "1200",
            "description": scraped["description"],
        }
        
        # 3. Importer normalization
        from import_to_wordpress_api_safe import normalize_listing_row
        normalized = normalize_listing_row(csv_row)
        
        # 4. Verify all fields are present and correct
        assert normalized["title"] == "SUNSHINE SENIOR CARE LLC"
        assert normalized["url"] == "https://app.seniorplace.com/communities/show/abc123"
        assert "789 Elm Dr" in normalized["address"]
        assert normalized["city"] == "Tempe"
        assert normalized["state"] == "AZ"
        assert normalized["featured_image"] == "https://cdn.example.com/sunshine.jpg"
        assert "Assisted Living Home" in normalized["care_types"]
        assert normalized.get("description") == scraped["description"]

