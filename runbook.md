# Senior Scraper Runbook (for assistant)

## Fast start
- Dashboard: `start_dashboard.bat` (Windows) or `./start_dashboard.sh`, then open `http://localhost:5000`.
- CLI full run: `python monthly_scrapers/monthly_update_orchestrator.py --full-update --states AZ CA CO ID NM UT --wp-password "$WP_PASSWORD" --sp-password "$SP_PASSWORD"`.
- Playwright must be installed once: `python -m playwright install chromium`.

## Normal flow
1) Fetch & compare: orchestrator scrapes Senior Place, enriches detail pages (care types, pricing, description, featured image), compares to WordPress, writes CSVs under `monthly_updates/<timestamp>/`.
2) Import: use dashboard “Add Communities” tab to upload `new_listings_*.csv` / `updated_listings_*.csv`, which calls `import_to_wordpress_api_safe.py` (safe importer, drafts).
3) Review drafts in WordPress and publish.

## Resume a stopped run
- Locate `monthly_updates/<timestamp>/resume_checkpoint.json`.
- Re-run orchestrator with `--full-update --resume --checkpoint <path>` (or use dashboard resume if available).
- Raw state per state in `monthly_updates/<timestamp>/raw/*.json` enables skip of completed states.

## Logs and status
- Dashboard status API: `http://localhost:5000/api/status`.
- Process persistence: `web_interface/logs/process_state.json` (PID, log path).
- Live logs: `web_interface/logs/scraper_*.log`, `web_interface/logs/import_*.log`.

## Single listing spot-check
- Dashboard “Single Listing” tab: paste Senior Place URL (`/show/<id>`).
- Expected fields returned: title, address, city, state, zip, care types, pricing (base/high/second person), description, featured image URL.

## Testing
- Full suite: `python -m pytest tests -v`.
- System smoke: `python monthly_scrapers/test_monthly_update.py`.
- WordPress ping (example): `curl -u "user:pass" "https://your-site/wp-json/wp/v2/listing?per_page=1"`.

## Performance / caching notes
- WordPress listings are cached locally to speed duplicate checks.
- Senior Place enrichment runs per listing; pagination uses `button:has-text("Next")`.

## Guiding principle (safety)
- Do not jeopardize access to Senior Place. Keep automation polite: respect login, avoid aggressive concurrency, and stop immediately if the UI or responses indicate throttling or blocks. Favor slower, reliable operation over risk of ban.

## Outputs
- `monthly_updates/<timestamp>/` contains `new_listings_*.csv`, `updated_listings_*.csv`, `update_summary_*.json`, `raw/*.json`, and `resume_checkpoint.json`.

