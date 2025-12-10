# Session Memory (Dec 8-9, 2025)

## Current State
- **Full scrape running** for all states (AZ, CA, CO, ID, NM, UT) without page cap.
- Log: `web_interface/logs/scraper_20251208_182704.log`
- Dashboard: http://localhost:5000

## Recent Changes (Dec 8-9)
1. **Canonical care type mapping** implemented in both:
   - `monthly_scrapers/monthly_update_orchestrator.py` (`map_care_types` function)
   - `web_interface/app.py` (`CARE_TYPE_MAPPING` + `map_care_types_to_canonical`)
   - Filters out room types (Studio, One Bedroom) and bathroom types (Shared, Private)

2. **MAX_PAGES_PER_STATE** env var added to `wp_config.env` for quick testing:
   - Set to limit pagination per state (e.g., `MAX_PAGES_PER_STATE="5"`)
   - Comment out for full production runs

3. **Compare Listing tab** added to dashboard:
   - API: `/api/compare-single-listing`
   - Fetches Senior Place listing, compares to WordPress by URL then by title
   - Shows match status (new, exists, exists_by_title)

4. **Version badge** added to dashboard header:
   - Displays git short hash or `APP_VERSION` env
   - API: `/api/status` returns `app_version`

5. **Care types display** updated in dashboard:
   - Shows both "Care Types (Canonical)" and "Care Types (Raw)"
   - Single Listing and Compare Listing tabs both updated

## Key Files
- `monthly_scrapers/monthly_update_orchestrator.py` - main scraper/enricher
- `web_interface/app.py` - Flask dashboard backend
- `web_interface/templates/index.html` - dashboard frontend
- `wp_config.env` - environment configuration
- `runbook.md` - AI operational guide
- `import_to_wordpress_api_safe.py` - safe WordPress importer

## WordPress Canonical Care Types
| ID | Type |
|----|------|
| 5 | Assisted Living Community |
| 162 | Assisted Living Home |
| 6 | Independent Living |
| 3 | Memory Care |
| 7 | Nursing Home |
| 488 | Home Care |

## Outstanding Actions
- Monitor full scrape completion
- Validate generated CSVs after full run completes
- Import to WordPress and verify listings

## Notes
- Senior Place credentials: stored in `wp_config.env` (not in repo)
- Pagination uses `button:has-text("Next")` (not `<a>` links)
- Address extraction: Details tab has form inputs for address/city/state/zip
- Image extraction: Use community images, convert `/api/files/` to CDN URLs

## Recent Fixes
- **Address parsing**: Fixed card-level scraping to properly extract city/state/zip from "City, ST ZIP" format
- **Care type extraction**: Now targets only "Community Type(s)" section checkboxes, avoids bathroom/other sections
- **Data quality**: Scraper now produces clean data from source instead of requiring post-processing
- **Code quality**: Added 3 new comprehensive tests, fixed regex warnings, enhanced error handling
- **Test coverage**: All 75 tests pass, covering address parsing, care type mapping, and full workflows
- **Documentation**: Updated runbook with current procedures and data quality metrics