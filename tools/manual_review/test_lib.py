#!/usr/bin/env python3
"""
Sanity tests for manual review library functions.

This does NOT spin up Streamlit; it verifies the underlying logic used by the app:
- load_base_data: columns and renames
- upsert_decision: idempotent write/update
- export_wp_import: correct columns and mappings

Run:
  python3 tools/manual_review/test_lib.py
"""

import os
import tempfile
import pandas as pd
from pathlib import Path

from tools.manual_review.lib import (
    load_base_data,
    load_progress,
    save_progress,
    upsert_decision,
    export_wp_import,
)


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg} | {a} != {b}")


def main():
    with tempfile.TemporaryDirectory() as tmpd:
        base_csv = Path(tmpd) / "base.csv"
        prog_csv = Path(tmpd) / "progress.csv"

        # Create a tiny base dataset (mimics seniorly_listings_for_scraping.csv)
        base_df = pd.DataFrame(
            [
                {"ID": 1001, "Title": "Alpha Home", "seniorly_url_final": "https://example/alpha",
                 "type": "", "States": "Arizona", "Locations": "Phoenix"},
                {"ID": 1002, "Title": "Beta Community", "seniorly_url_final": "https://example/beta",
                 "type": "", "States": "Arizona", "Locations": "Mesa"},
                {"ID": 1003, "Title": "Gamma", "seniorly_url_final": "https://example/gamma",
                 "type": "", "States": "Arizona", "Locations": "Tucson"},
            ]
        )
        base_df.to_csv(base_csv, index=False)

        # Load base data via lib and check columns
        loaded = load_base_data(str(base_csv))
        for col in ["ID", "Title", "URL", "type", "States", "Locations"]:
            assert col in loaded.columns, f"missing column {col}"
        assert_equal(len(loaded), 3, "base rows")

        # Progress should load empty
        prog = load_progress(str(prog_csv))
        assert_equal(len(prog), 0, "empty progress")

        # Upsert decisions for two rows
        prog = upsert_decision(prog, 1001, "Home", "")
        prog = upsert_decision(prog, 1002, "Community", "")
        save_progress(str(prog_csv), prog)

        # Reload and confirm persistence
        prog2 = load_progress(str(prog_csv))
        assert_equal(len(prog2), 2, "persisted decisions count")
        assert set(prog2["Decision"]) == {"Home", "Community"}, "decision set"

        # Export and verify mapping
        out = export_wp_import(prog2, loaded)
        # Only decided rows included
        assert_equal(len(out), 2, "export rows")
        # Columns
        assert list(out.columns) == ["ID", "type", "normalized_types", "_type"], "export columns"
        # Mapping
        row_home = out[out.ID == 1001].iloc[0]
        row_comm = out[out.ID == 1002].iloc[0]
        assert_equal(row_home["type"], "162", "home type id")
        assert_equal(row_home["normalized_types"], "Assisted Living Home", "home label")
        assert_equal(row_home["_type"], "162", "home _type")
        assert_equal(row_comm["type"], "5", "community type id")
        assert_equal(row_comm["normalized_types"], "Assisted Living Community", "community label")
        assert_equal(row_comm["_type"], "5", "community _type")

        print("OK: lib tests passed.")


if __name__ == "__main__":
    main()


