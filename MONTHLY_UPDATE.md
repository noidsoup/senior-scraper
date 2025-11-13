## Monthly update: find and add NEW listings

This flow produces a CSV of only-new listings (not yet on WordPress), then imports them as drafts for review.

### 1) Scrape latest data (6 states)
Run the scraper to refresh CSVs. Example:

```bash
python3 -u scrape_all_states.py --states AZ CA CO ID NM UT --headless > production_run_$(date +%Y%m%d_%H%M%S).log 2>&1
```

This creates files like `AZ_seniorplace_data_YYYYMMDD.csv` in the repo root.

### 2) Generate the monthly candidate list
This compares the newest CSV per state against WordPress and emits a consolidated candidate file.

```bash
python3 monthly_generate_candidates.py \
  --states AZ CA CO ID NM UT \
  --output data/processed/monthly_candidates_$(date +%Y%m%d).csv
```

Output example:

```
Candidate generation complete:
  Total rows scanned:   12,345
  Skipped invalid:      123
  Skipped existing:     11,987
  New candidates:       235
  Output CSV:           data/processed/monthly_candidates_YYYYMMDD.csv
```

Notes
- Dedupe is by Senior Place URL (authoritative).
- Titles are normalized (DBA/LLC stripped; “(The)” moved to front).
- Blocklist applied: titles containing “Do Not Refer”, “Do Not Use”, “Not Signing”, or surgery-related terms are excluded.

### 3) Import candidates to WordPress (safe)
Import in small batches as drafts. You can review and publish afterward.

```bash
python3 import_to_wordpress_api_safe.py data/processed/monthly_candidates_YYYYMMDD.csv --batch-size=25
```

Tips
- To publish automatically after creation, use your existing helper or open each draft and publish.
- If you re-run the import, duplicates are skipped via the cached WordPress URL set.

### 4) Verify on frontend
Spot check a few entries:
- Title formatting (DBA/LLC removed; “The …” fix)
- Address present
- Care types assigned
- Correct state + location taxonomy

### Troubleshooting
- If candidates = 0 but you expect new entries, re-run step 1 (fresh scrape) and step 2 with `--wp-pages` omitted to fetch the full WordPress URL cache.
- If a title appears as `Name (The)`, the normalizer is already configured to move it to `The Name` on import.


