import asyncio
import json
from pathlib import Path

import pytest

from monthly_scrapers.monthly_update_orchestrator import MonthlyUpdateOrchestrator


def test_resume_skips_completed_state(tmp_path, monkeypatch):
    """Resume uses cached raw data and only scrapes remaining states."""
    orch = MonthlyUpdateOrchestrator(
        wp_url="https://example.com",
        wp_username="user",
        wp_password="pass",
        sp_username="sp_user",
        sp_password="sp_pass",
    )
    orch.timestamp = "TS"

    # Prepare checkpoint and cached raw data for AZ
    cp_dir = tmp_path / "monthly_updates" / "TS"
    raw_dir = cp_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cached_listing = [{"title": "Cached AZ", "url": "https://app.seniorplace.com/az1", "address": "AZ"}]
    raw_file = raw_dir / "AZ.json"
    raw_file.write_text(json.dumps(cached_listing), encoding="utf-8")

    checkpoint_payload = {
        "timestamp": "TS",
        "states_completed": ["AZ"],
        "states_remaining": ["UT"],
        "scraped_files": {"AZ": str(raw_file)},
    }
    cp_file = cp_dir / "resume_checkpoint.json"
    cp_file.write_text(json.dumps(checkpoint_payload), encoding="utf-8")

    # Mocks
    monkeypatch.setattr(orch, "fetch_current_wordpress_listings", lambda: {})

    scraped_states = []

    async def fake_scrape(code, name):
        scraped_states.append(code)
        return [{"title": f"New {code}", "url": f"https://app.seniorplace.com/{code.lower()}2", "address": code}]

    async def fake_enrich(listings):
        return listings

    def fake_identify(listings):
        return listings, []

    def fake_generate(new, updated):
        out_dir = tmp_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    monkeypatch.setattr(orch, "scrape_seniorplace_state", fake_scrape)
    monkeypatch.setattr(orch, "enrich_listing_details", fake_enrich)
    monkeypatch.setattr(orch, "identify_new_and_updated", fake_identify)
    monkeypatch.setattr(orch, "generate_wordpress_import_files", fake_generate)

    states = [("AZ", "Arizona"), ("UT", "Utah")]
    
    # Run the async function using asyncio.run()
    asyncio.run(orch.run_full_update(states, resume_data=checkpoint_payload, checkpoint_file=cp_file))

    # Only UT should be scraped anew
    assert scraped_states == ["UT"]
    # Total processed counts cached AZ + new UT
    assert orch.stats["total_processed"] == 2

    # Checkpoint should be marked complete
    final_cp = json.loads(cp_file.read_text(encoding="utf-8"))
    assert final_cp["states_remaining"] == []
    assert final_cp.get("status") == "complete"

