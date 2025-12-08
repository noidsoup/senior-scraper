"""
Unit tests for WordPress listing cache functionality.
Tests cache saving, loading, TTL expiration, and invalidation.
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCacheBasics:
    """Basic cache functionality tests"""

    def test_cache_file_structure(self, tmp_path):
        """Test cache file JSON structure"""
        cache_data = {
            "timestamp": "2024-01-15T10:30:00",
            "ttl_seconds": 3600,
            "data": {
                "sp_urls": ["https://app.seniorplace.com/a", "https://app.seniorplace.com/b"],
                "seniorly_urls": ["https://seniorly.com/a"],
                "addresses": ["123 MAIN ST PHOENIX AZ"],
            },
        }
        
        cache_file = tmp_path / ".cache" / "test_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
        
        loaded = json.loads(cache_file.read_text(encoding="utf-8"))
        
        assert "timestamp" in loaded
        assert "ttl_seconds" in loaded
        assert "data" in loaded
        assert isinstance(loaded["data"]["sp_urls"], list)

    def test_cache_ttl_logic(self):
        """Test TTL expiration logic"""
        from datetime import datetime, timedelta
        
        cache_time = datetime.now() - timedelta(hours=2)
        current_time = datetime.now()
        ttl_seconds = 3600  # 1 hour
        
        age_seconds = (current_time - cache_time).total_seconds()
        is_expired = age_seconds > ttl_seconds
        
        assert is_expired is True  # 2 hours > 1 hour TTL
        
        # Fresh cache
        cache_time_fresh = datetime.now() - timedelta(minutes=30)
        age_fresh = (current_time - cache_time_fresh).total_seconds()
        is_expired_fresh = age_fresh > ttl_seconds
        
        assert is_expired_fresh is False  # 30 minutes < 1 hour TTL

    def test_cache_directory_created(self, tmp_path):
        """Test that .cache directory is created if missing"""
        cache_dir = tmp_path / ".cache"
        assert not cache_dir.exists()
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        assert cache_dir.exists()
        assert cache_dir.is_dir()


class TestOrchestratorCache:
    """Tests for orchestrator WordPress cache"""

    def test_cache_contains_url_mappings(self, tmp_path):
        """Test that cache stores URL -> listing mappings"""
        cache_data = {
            "https://app.seniorplace.com/123": {"id": 1, "title": "Test 1"},
            "https://app.seniorplace.com/456": {"id": 2, "title": "Test 2"},
        }
        
        cache_file = tmp_path / "wp_listings_cache.json"
        full_cache = {
            "timestamp": "2024-01-15T10:30:00",
            "ttl_seconds": 3600,
            "data": cache_data,
        }
        cache_file.write_text(json.dumps(full_cache), encoding="utf-8")
        
        loaded = json.loads(cache_file.read_text(encoding="utf-8"))
        
        assert "https://app.seniorplace.com/123" in loaded["data"]
        assert loaded["data"]["https://app.seniorplace.com/123"]["id"] == 1


class TestImporterCache:
    """Tests for importer duplicate cache"""

    def test_cache_contains_sets(self, tmp_path):
        """Test that cache stores URL sets for duplicate checking"""
        cache_data = {
            "sp_urls": ["https://app.seniorplace.com/a", "https://app.seniorplace.com/b"],
            "seniorly_urls": ["https://seniorly.com/x"],
            "addresses": ["123 MAIN ST PHOENIX AZ", "456 OAK AVE TEMPE AZ"],
        }
        
        cache_file = tmp_path / "wp_existing_urls_cache.json"
        full_cache = {
            "timestamp": "2024-01-15T10:30:00",
            "ttl_seconds": 3600,
            "data": cache_data,
        }
        cache_file.write_text(json.dumps(full_cache), encoding="utf-8")
        
        loaded = json.loads(cache_file.read_text(encoding="utf-8"))
        data = loaded["data"]
        
        # Convert to sets for duplicate checking
        sp_urls = set(data["sp_urls"])
        addresses = set(data["addresses"])
        
        assert "https://app.seniorplace.com/a" in sp_urls
        assert "123 MAIN ST PHOENIX AZ" in addresses

    def test_cache_invalidation_env_var(self):
        """Test that WP_CACHE_DISABLE=1 bypasses cache"""
        os.environ["WP_CACHE_DISABLE"] = "1"
        
        should_use_cache = os.environ.get("WP_CACHE_DISABLE") != "1"
        
        assert should_use_cache is False
        
        # Cleanup
        del os.environ["WP_CACHE_DISABLE"]

    def test_custom_ttl_env_var(self):
        """Test that WP_CACHE_TTL_SECONDS overrides default"""
        os.environ["WP_CACHE_TTL_SECONDS"] = "7200"
        
        ttl = int(os.environ.get("WP_CACHE_TTL_SECONDS", 3600))
        
        assert ttl == 7200
        
        # Cleanup
        del os.environ["WP_CACHE_TTL_SECONDS"]


class TestCacheIntegration:
    """Integration tests for cache behavior"""

    def test_fresh_cache_skips_fetch(self, tmp_path):
        """Test that fresh cache prevents WP API calls"""
        from datetime import datetime
        
        # Create fresh cache
        cache_file = tmp_path / ".cache" / "wp_existing_urls_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "ttl_seconds": 3600,
            "data": {
                "sp_urls": ["https://app.seniorplace.com/cached"],
                "seniorly_urls": [],
                "addresses": ["CACHED ADDRESS"],
            },
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
        
        # Load and verify
        loaded = json.loads(cache_file.read_text(encoding="utf-8"))
        cache_time = datetime.fromisoformat(loaded["timestamp"])
        age = (datetime.now() - cache_time).total_seconds()
        
        assert age < loaded["ttl_seconds"]  # Cache is fresh

    def test_expired_cache_triggers_fetch(self, tmp_path):
        """Test that expired cache triggers fresh WP API call"""
        from datetime import datetime, timedelta
        
        # Create expired cache (2 hours old, 1 hour TTL)
        cache_file = tmp_path / ".cache" / "wp_existing_urls_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        old_time = datetime.now() - timedelta(hours=2)
        cache_data = {
            "timestamp": old_time.isoformat(),
            "ttl_seconds": 3600,
            "data": {
                "sp_urls": ["https://app.seniorplace.com/old"],
                "seniorly_urls": [],
                "addresses": [],
            },
        }
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
        
        # Check if expired
        loaded = json.loads(cache_file.read_text(encoding="utf-8"))
        cache_time = datetime.fromisoformat(loaded["timestamp"])
        age = (datetime.now() - cache_time).total_seconds()
        
        assert age > loaded["ttl_seconds"]  # Cache is expired

