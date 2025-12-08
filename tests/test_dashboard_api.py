"""
Unit tests for the Flask dashboard API endpoints.
Tests status, process management, and single listing fetch.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Flask app
from web_interface.app import app, get_project_root


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestStatusEndpoint:
    """Tests for /api/status endpoint"""

    def test_status_returns_json(self, client):
        """Test that status endpoint returns JSON"""
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_status_contains_required_keys(self, client):
        """Test that status response has required keys"""
        response = client.get("/api/status")
        data = json.loads(response.data)
        
        required_keys = ["recent_runs", "wordpress", "csv_files", "environment", "running_processes"]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_status_environment_check(self, client):
        """Test that environment status is reported"""
        response = client.get("/api/status")
        data = json.loads(response.data)
        
        assert "environment" in data
        assert "wp_credentials" in data["environment"]
        assert "sp_credentials" in data["environment"]


class TestProjectRoot:
    """Tests for project root detection"""

    def test_project_root_is_directory(self):
        """Test that project root is a valid directory"""
        root = get_project_root()
        assert root.exists()
        assert root.is_dir()

    def test_project_root_contains_expected_files(self):
        """Test that project root contains expected files"""
        root = get_project_root()
        # Should have requirements.txt or similar
        assert (root / "requirements.txt").exists() or (root / "monthly_scrapers").exists()


class TestSingleListingFetch:
    """Tests for /api/fetch-single-listing endpoint"""

    def test_requires_url_parameter(self, client):
        """Test that URL is required"""
        response = client.post(
            "/api/fetch-single-listing",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_rejects_empty_url(self, client):
        """Test that empty URL is rejected"""
        response = client.post(
            "/api/fetch-single-listing",
            json={"url": ""},
            content_type="application/json",
        )
        assert response.status_code == 400


class TestProcessManagement:
    """Tests for process status and control endpoints"""

    def test_process_status_not_found(self, client):
        """Test status for non-existent process"""
        response = client.get("/api/process-status/nonexistent")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] in ["not_running", "not_found"]

    def test_stop_nonexistent_process(self, client):
        """Test stopping a process that doesn't exist"""
        response = client.post("/api/stop-process/nonexistent")
        # Should return error or already stopped
        data = json.loads(response.data)
        assert "error" in data or "status" in data


class TestCSVUpload:
    """Tests for CSV upload endpoint"""

    def test_upload_requires_file(self, client):
        """Test that file is required"""
        response = client.post("/api/upload-csv")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_upload_rejects_non_csv(self, client):
        """Test that non-CSV files are rejected"""
        from io import BytesIO
        
        response = client.post(
            "/api/upload-csv",
            data={"file": (BytesIO(b"test content"), "test.txt")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "CSV" in data["error"] or "csv" in data["error"].lower()


class TestLogsEndpoint:
    """Tests for log file retrieval"""

    def test_logs_not_found(self, client):
        """Test response for non-existent log file"""
        response = client.get("/api/logs/nonexistent_file.log")
        assert response.status_code == 404


class TestDashboardRoutes:
    """Tests for main dashboard routes"""

    def test_index_returns_html(self, client):
        """Test that index returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Senior Scraper Dashboard" in response.data


class TestRunScraperEndpoint:
    """Tests for /api/run-scraper endpoint"""

    def test_run_scraper_accepts_states(self, client):
        """Test that states parameter is accepted"""
        # This would normally start a process, but we're just testing the endpoint
        # In a real test, we'd mock subprocess.Popen
        with patch("web_interface.app.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            response = client.post(
                "/api/run-scraper",
                json={"states": ["AZ"]},
                content_type="application/json",
            )
            
            # Should start or indicate already running
            assert response.status_code in [200, 400]


class TestRunImportEndpoint:
    """Tests for /api/run-import endpoint"""

    def test_import_requires_csv(self, client):
        """Test that CSV file is required"""
        response = client.post(
            "/api/run-import",
            json={},
            content_type="application/json",
        )
        # Should fail due to missing CSV
        assert response.status_code in [400, 500]

