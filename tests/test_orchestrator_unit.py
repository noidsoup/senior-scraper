import json
from pathlib import Path

import pytest

from monthly_scrapers.monthly_update_orchestrator import MonthlyUpdateOrchestrator


@pytest.fixture
def orch():
    return MonthlyUpdateOrchestrator(
        wp_url="https://example.com",
        wp_username="user",
        wp_password="pass",
        sp_username="sp_user",
        sp_password="sp_pass",
    )


def test_fetch_current_wordpress_listings_paginates_and_maps(monkeypatch, orch, tmp_path):
    """Ensure pagination stops at 400 and URLs map correctly."""
    # Disable cache for this test (must set directly since orch is already created)
    orch.disable_wp_cache = True
    
    calls = []

    class FakeResponse:
        def __init__(self, status, payload):
            self.status_code = status
            self._payload = payload

        def raise_for_status(self):
            if self.status_code >= 400 and self.status_code != 400:
                raise Exception("http error")

        def json(self):
            return self._payload

    def fake_get(url, params, auth, timeout):
        page = params["page"]
        calls.append(page)
        # Two pages of data, then a 400 to stop
        if page == 1:
            return FakeResponse(
                200,
                [
                    {
                        "id": 1,
                        "acf": {"senior_place_url": "https://app.seniorplace.com/a"},
                        "meta": {"_seniorly_url": ["https://www.seniorly.com/a"]},
                    }
                ],
            )
        if page == 2:
            return FakeResponse(
                200,
                [
                    {
                        "id": 2,
                        "acf": {"senior_place_url": "https://app.seniorplace.com/b"},
                        "meta": {"_seniorly_url": ["https://www.seniorly.com/b"]},
                    }
                ],
            )
        return FakeResponse(400, [])

    monkeypatch.setattr("monthly_scrapers.monthly_update_orchestrator.requests.get", fake_get)

    listings = orch.fetch_current_wordpress_listings()

    assert calls == [1, 2, 3]  # page 3 triggers 400 and stops
    assert "https://app.seniorplace.com/a" in listings
    assert "https://www.seniorly.com/a" in listings
    assert listings["https://app.seniorplace.com/b"]["id"] == 2


def test_identify_new_and_updated_sets_stats(orch):
    orch.current_wp_listings = {
        "https://app.seniorplace.com/existing": {"id": 10, "acf": {"price": "1500"}}
    }

    scraped = [
        {
            "title": "Existing",
            "url": "https://app.seniorplace.com/existing",
            "monthly_base_price": "$2,000",
            "care_types": ["assisted living facility"],
        },
        {
            "title": "New",
            "url": "https://app.seniorplace.com/new",
            "monthly_base_price": "$3,000",
            "care_types": ["directed care"],
        },
    ]

    new_listings, updated_listings = orch.identify_new_and_updated(scraped)

    assert len(new_listings) == 1
    assert len(updated_listings) == 1
    assert orch.stats["new_listings_found"] == 1
    assert orch.stats["listings_updated"] == 1
    assert orch.stats["pricing_updates"] == 1
    assert orch.stats["care_type_updates"] == 1
    assert updated_listings[0]["updates"]["price"] == "2000"


def test_generate_wordpress_import_files_creates_outputs(tmp_path, orch):
    # Run inside temp dir to avoid polluting real monthly_updates
    Path(tmp_path).mkdir(parents=True, exist_ok=True)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)
    orch.timestamp = "TEST_TS"

    new_listings = [
        {
            "title": "New Place",
            "address": "1 Main St, Phoenix, AZ 85001",
            "url": "https://app.seniorplace.com/new",
            "featured_image": "http://img",
            "monthly_base_price": "$1,500",
            "care_types": ["directed care", "Memory Care"],
            "price_high_end": "$2,500",
            "second_person_fee": "$500",
        }
    ]

    updated_listings = [
        {
            "wp_id": 77,
            "title": "Existing Place",
            "url": "https://app.seniorplace.com/existing",
            "monthly_base_price": "$2,000",
            "care_types": ["assisted living facility"],
            "updates": {"price": "2000", "care_types": ["assisted living facility"]},
        }
    ]

    output_dir = orch.generate_wordpress_import_files(new_listings, updated_listings)

    # New listings CSV
    new_csv = output_dir / "new_listings_TEST_TS.csv"
    assert new_csv.exists()
    rows = new_csv.read_text(encoding="utf-8").strip().splitlines()
    assert "New Place" in rows[1]
    assert "Assisted Living Home" in rows[1]  # directed care -> ALH
    assert "Memory Care" in rows[1]

    # Updated listings CSV
    upd_csv = output_dir / "updated_listings_TEST_TS.csv"
    assert upd_csv.exists()
    rows_upd = upd_csv.read_text(encoding="utf-8").strip().splitlines()
    assert "Existing Place" in rows_upd[1]
    assert "Assisted Living Community" in rows_upd[1]

    # Summary JSON
    summary = output_dir / "update_summary_TEST_TS.json"
    assert summary.exists()
    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_payload["files_generated"]["new_listings"].endswith("new_listings_TEST_TS.csv")
    assert summary_payload["files_generated"]["updated_listings"].endswith("updated_listings_TEST_TS.csv")

    monkeypatch.undo()

