# Senior Scrapr - Folder Structure

## Root Directory Organization

### 📁 `/california_expansion/` (7 files)

**Current California expansion project files**

- `california_seniorplace_data.csv` - 26,248 CA listings (raw data)
- `california_seniorplace_data.jsonl` - Incremental scrape data
- `california_seniorplace_data_with_seniorly.csv` - CA listings with Seniorly matches attempted
- `CALIFORNIA_WP_IMPORT_BASE.csv` - **WordPress import ready file**
- `scrape_california_senior_place.py` - CA-specific Senior Place scraper
- `match_california_with_seniorly.py` - Search Seniorly for CA listings
- `prepare_california_for_wordpress.py` - Convert CA data to WP format

### 📁 `/scrapers_active/` (4 files)

**Currently used/maintained scraping scripts**

- `enhanced_seniorly_scraper.py` - Get better images/descriptions from Seniorly
- `update_prices_from_seniorplace_export.py` - Main pricing scraper
- `scrape_live_senior_place_data.py` - Live Senior Place data extraction
- `scrape_seniorly_community_types.py` - Seniorly care type scraper

### 📁 `/scrapers_archive/` (15 files)

**Old/experimental scrapers - kept for reference**

- Various sync scripts (`sync_*.py`)
- Comprehensive update scripts
- Old classifier versions
- Search/match experiments

### 📁 `/wordpress_import/` (9 files)

**Final WordPress import files and manual review data**

- `WP_IMPORT_*.csv` - Import-ready files
- `FINAL_*.csv` - Finalized correction files
- `RECOMMENDED_*.csv` - Recommendation outputs
- `manual_review_*.csv` - Manual review tracking

### 📁 `/data_outputs/` (15 files)

**Data outputs, exports, and intermediate files**

- `Listings-Export-*.csv` - WordPress exports
- `seniorly_*.csv` - Seniorly classification outputs
- `SENIORLY_*.csv` - Seniorly processing results
- `*.json` - JSON test/analysis results
- `TRIAGE_*.csv` - Conflict triage files

### 📁 `/data_analysis/` (38 files)

**Analysis, fixing, and data manipulation scripts**

- `analyze_*.py` - Data analysis scripts
- `check_*.py` - Data validation scripts
- `create_*.py` - Data creation/transformation scripts
- `export_*.py` - Export utilities
- `extract_*.py` - Data extraction utilities
- `fix_*.py` - Data fixing/correction scripts
- `merge_*.py` - Data merging utilities
- `find_*.py` - Search/find utilities
- `map_*.py` - Mapping utilities

### 📁 `/test_scripts/` (20 files)

**Testing and debugging scripts**

- `test_*.py` - Test scripts
- `debug_*.py` - Debugging utilities
- `simple_*.py` - Simple test cases
- Frontend/filter tests

### 📁 `/docs/` (7 files)

**Documentation and notes**

- `memory.md` - **Session memory (always read first!)**
- `README.md` - Project README
- `*.md` - Solution summaries and documentation
- `*.txt` - Failed URLs and notes

### 📁 `/archive/` (existing)

**Historical files - already organized**

### 📁 `/organized_csvs/` (existing)

**Previously organized CSV files**

### 📁 `/tools/` (existing)

**Tool utilities (e.g., manual review app)**

## Root Directory Files

**Active/In-Progress:**

- `enrich_california_pricing.py` - ⚠️ **CURRENTLY RUNNING** - Do not delete!
- `california_seniorplace_data_with_pricing.csv.checkpoint` - Checkpoint file (auto-saves)
- `pricing_enrichment.log` - Pricing enrichment log

**Config:**

- `package.json` - Node dependencies
- `requirements.txt` - Python dependencies

## Key Patterns

1. **Active project files** → `/california_expansion/`
2. **Scripts you use regularly** → `/scrapers_active/`
3. **Old/experimental scripts** → `/scrapers_archive/`
4. **Final outputs for WordPress** → `/wordpress_import/`
5. **Raw data & intermediate files** → `/data_outputs/`
6. **Analysis & one-off scripts** → `/data_analysis/`
7. **Testing & debugging** → `/test_scripts/`
8. **Documentation** → `/docs/`

## Notes

- **DO NOT MOVE** `enrich_california_pricing.py` while it's running
- Checkpoint files (`.checkpoint`) are auto-generated, keep in root
- Log files (`.log`) are transient, safe to delete when process completes
- Always check `docs/memory.md` at start of each session
