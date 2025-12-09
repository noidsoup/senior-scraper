# Senior Scraper Runbook (for assistant)

## Fast start
- Dashboard: `start_dashboard.bat` (Windows) or `./start_dashboard.sh`, then open `http://localhost:5000`.
- CLI full run: `python monthly_scrapers/monthly_update_orchestrator.py --full-update --states AZ CA CO ID NM UT --wp-password "$WP_PASSWORD" --sp-password "$SP_PASSWORD"`.
- Playwright must be installed once: `python -m playwright install chromium`.

## Normal flow
1) Fetch & compare: orchestrator scrapes Senior Place, enriches detail pages (care types, pricing, description, featured image), compares to WordPress, writes CSVs under `monthly_updates/<timestamp>/`.
2) Import: use dashboard "Add Communities" tab to upload `new_listings_*.csv` / `updated_listings_*.csv`, which calls `import_to_wordpress_api_safe.py` (safe importer, drafts).
3) Review drafts in WordPress and publish.

## Canonical Care Type Mapping
Senior Place types are mapped to WordPress canonical types. Only valid care types are included; room types (Studio, One Bedroom) and bathroom types (Shared, Private) are filtered out.

| Senior Place Type | WordPress Canonical |
|-------------------|---------------------|
| Assisted Living Facility | Assisted Living Community |
| Assisted Living Home | Assisted Living Home |
| Independent Living | Independent Living |
| Memory Care | Memory Care |
| Skilled Nursing | Nursing Home |
| CCRC | Assisted Living Community |
| In-Home Care | Home Care |
| Home Health | Home Care |
| Hospice | Home Care |
| Respite Care | Assisted Living Community |
| Directed Care | Assisted Living Home |
| Personal Care | Assisted Living Home |
| Supervisory Care | Assisted Living Home |

## Quick testing (page cap)
Set `MAX_PAGES_PER_STATE` in `wp_config.env` to limit pagination per state for faster test runs:
```
MAX_PAGES_PER_STATE="5"  # Only scrape 5 pages per state
```
Comment out or remove for full production runs.

## Resume a stopped run
- Locate `monthly_updates/<timestamp>/resume_checkpoint.json`.
- Re-run orchestrator with `--full-update --resume --checkpoint <path>` (or use dashboard resume if available).
- Raw state per state in `monthly_updates/<timestamp>/raw/*.json` enables skip of completed states.

## Logs and status
- Dashboard status API: `http://localhost:5000/api/status`.
- Process persistence: `web_interface/logs/process_state.json` (PID, log path).
- Live logs: `web_interface/logs/scraper_*.log`, `web_interface/logs/import_*.log`.
- Version badge: displayed in dashboard header (git short hash or APP_VERSION env).

## Dashboard features
- **Find Communities**: Scrape Senior Place for selected states.
- **Single Listing**: Paste Senior Place URL to preview all extracted fields.
- **Compare Listing**: Paste Senior Place URL to compare with cached WordPress listings (checks by URL, then by title).
- **Add Communities**: Upload CSVs to import to WordPress.
- **Search History**: View past scrape runs.
- **Check System**: Verify WordPress and Senior Place connectivity.

## Single listing spot-check
- Dashboard "Single Listing" or "Compare Listing" tab: paste Senior Place URL (`/show/<id>`).
- Expected fields returned: title, address, city, state, zip, care types (canonical + raw), pricing (base/high/second person), description, featured image URL.

## Testing
- Full suite: `python -m pytest tests -v`.
- System smoke: `python monthly_scrapers/test_monthly_update.py`.
- WordPress ping (example): `curl -u "user:pass" "https://your-site/wp-json/wp/v2/listing?per_page=1"`.

## Performance / caching notes
- WordPress listings are cached locally (`.cache/wp_listings_cache.json`) to speed duplicate checks.
- Senior Place enrichment runs per listing; pagination uses `button:has-text("Next")`.

## Guiding principle (safety)
- **Do not jeopardize access to Senior Place.** Keep automation polite: respect login, avoid aggressive concurrency, and stop immediately if the UI or responses indicate throttling or blocks. Favor slower, reliable operation over risk of ban.

## Outputs
- `monthly_updates/<timestamp>/` contains:
  - `new_listings_*.csv` - new listings ready for WordPress import
  - `updated_listings_*.csv` - existing listings needing updates
  - `update_summary_*.json` - statistics and file paths
  - `raw/*.json` - raw scraped data per state
  - `resume_checkpoint.json` - checkpoint for resuming interrupted runs
