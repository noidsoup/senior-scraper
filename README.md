## Senior Scrapr - WordPress Import and Monthly Update Toolkit

Import Senior Place listings into WordPress safely, avoid duplicates, normalize titles, assign taxonomies, and handle featured images. Includes a monthly workflow to discover new listings and prepare import-ready CSVs.

### Prerequisites
- Python 3.10+ (3.11 recommended)
- macOS/Linux (Windows WSL works)
- Optional: GitHub CLI (`gh`) for easy repo creation

### Setup
1) Clone and create virtualenv
```bash
cd /Users/nicholas/Repos
git clone <this-repo> senior-scrapr
cd senior-scrapr
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) Configure environment
```bash
# Copy example and fill in values
cp wp_config.example.env .env
source .env
```

3) (Optional) Install Playwright browser for monthly scrapers
```bash
python3 -m playwright install chromium
```

### Quick Usage
- Safe importer (creates drafts, dedupes by URLs and address, uploads images):
```bash
source .env  # or export WP_USER/WP_PASSWORD etc.
python3 import_to_wordpress_api_safe.py data/processed/monthly_candidates_YYYYMMDD.csv --batch-size 25
```

- Image backfill dry run (analyzes feasibility):
```bash
source .env
python3 backfill_images_dryrun.py
```

### Monthly Workflow
See:
- `QUICK_START_MONTHLY_UPDATES.md`
- `MONTHLY_UPDATE_README.md`

Those cover scraping, candidate generation, automation, and logs. Example:
```bash
source .env
python3 monthly_scrapers/monthly_update_orchestrator.py --full-update --states AZ --wp-password "$WP_PASSWORD"
```

### Environment Variables
- `WP_URL` (default: https://aplaceforseniorscms.kinsta.cloud)
- `WP_USER` or `WP_USERNAME`
- `WP_PASS` or `WP_PASSWORD` (WordPress Application Password)
- `FRONTEND_BASE_URL` (default: https://communities.aplaceforseniors.org)
- Optional for monthly workflow: `SP_USERNAME`, `SP_PASSWORD`, `NOTIFICATION_EMAIL`, `SMTP_PASSWORD`

### Repo Hygiene
Generated artifacts, logs, and heavy data folders are excluded via `.gitignore`:
- `data/raw/**`, `data/processed/archive/**`, `monthly_updates/**`, `*.log`, `*.import_checkpoint.json`, venv, caches, etc.

### Migrate to GitHub (no secrets committed)
1) Confirm no secrets in code (we now load from env)
2) Initialize git and commit:
```bash
git init
git add .
git commit -m \"Initial public setup: env-based creds, tooling, docs\"
```
3) Create remote and push (choose one):
```bash
# Using GitHub CLI (private repo)
gh repo create aplaceforseniors/senior-scrapr --private --source=. --remote=origin --push

# Or traditional remote
git branch -M main
git remote add origin git@github.com:<your-org-or-user>/senior-scrapr.git
git push -u origin main
```

Note: Per policy, do not commit `.env` or any credentials. Use `wp_config.example.env` as the shareable template.

### Support Docs
- `docs/README.md`
- `docs/FOLDER_STRUCTURE.md`

### Testing
```bash
pytest -q
```

# Senior Living Data Scraper System

Complete automation system for scraping and managing senior living listings from Senior Place and Seniorly.

## 🎯 What This Does

Automatically scrapes **38,000+ senior living listings** across 9 states, compares with your WordPress database, and generates import-ready CSV files for new/updated listings.

## 📁 Project Structure

```
senior-scrapr/
├── 📋 Core Scripts
│   ├── scrape_all_states.py          ← Main scraper (use this!)
│   └── scrapers_active/               ← Working scrapers
│
├── 🗂️ Current Data
│   ├── current_scraped_data/          ← Today's scrape results
│   └── monthly_updates/               ← Comparison results (new/updated)
│
├── 📚 Monthly Updates (Automated System)
│   ├── monthly_scrapers/              ← Full orchestration system
│   ├── MONTHLY_UPDATE_README.md       ← Detailed docs
│   ├── QUICK_START_MONTHLY_UPDATES.md ← 5-minute setup
│   └── SYSTEM_OVERVIEW.md             ← System explanation
│
├── 🏗️ Project History
│   ├── california_expansion/          ← CA expansion project (Oct 2024)
│   ├── wordpress_import/              ← Import-ready files
│   └── archive/                       ← Old scripts, logs, test files
│
└── 📖 Documentation
    └── docs/                          ← All documentation & guides
```

## 🚀 Quick Start

### Scrape All States (Current Approach)

```bash
# Scrape all 6 states (AZ, CA, CO, UT, ID, NM)
python3 scrape_all_states.py --states AZ CA CO ID NM UT --headless

# Output: [STATE]_seniorplace_data_YYYYMMDD.csv for each state
```

### Compare with WordPress & Find New Listings

```bash
# Compare scraped data with WordPress to find NEW listings
python3 monthly_scrapers/compare_california_quick.py

# Output: NEW_CALIFORNIA_LISTINGS.csv (ready to import)
```

## 📊 Current Coverage

| State      | Listings | Status     |
| ---------- | -------- | ---------- |
| Arizona    | 1,831    | ✅ Scraped |
| California | ~20,000+ | 🔄 Running |
| Colorado   | ~2,000   | ⏳ Queued  |
| Idaho      | ~800     | ⏳ Queued  |
| New Mexico | ~600     | ⏳ Queued  |
| Utah       | ~1,500   | ⏳ Queued  |

**Total**: ~26,000+ listings across 6 states

**Note**: These are the hand-picked states for senior living per your website.

## 🎛️ Configuration

### Senior Place Credentials

```bash
Username: allison@aplaceforseniors.org
Password: set via SP_PASSWORD environment variable (do not hardcode)
```

### WordPress API

```bash
Site: https://aplaceforseniorscms.kinsta.cloud
User: nicholas_editor
App Password: [saved in memory]
```

## 🔄 Monthly Automated Updates

System automatically:

1. ✅ Scrapes all states from Senior Place
2. ✅ Fetches current WordPress listings
3. ✅ Compares and finds NEW listings
4. ✅ Generates import-ready CSVs
5. ✅ Runs on schedule (1st of each month)

**Setup:** See `QUICK_START_MONTHLY_UPDATES.md`

## 📝 Data Fields Captured

Each listing includes:

- Title, full address (street, city, state, zip)
- Senior Place URL (source attribution)
- Featured image (CDN URL)
- Care types (normalized to CMS taxonomy)
- Pricing (base, high-end, care levels)

## 🏆 Key Features

- ✅ **No Safety Limits** - Scrapes until actual end
- ✅ **Proper Pagination** - Goes through all pages
- ✅ **State Filtering** - Extracts specific states from mixed results
- ✅ **Type Normalization** - Maps to WordPress taxonomy
- ✅ **Duplicate Detection** - Compares with existing listings
- ✅ **CSV Ready** - Direct WordPress All Import compatible

## 🛠️ Maintenance

### Check Scraper Status

```bash
# View current progress
tail -f /tmp/scrape_all_unlimited.log

# Check if running
ps aux | grep scrape_all_states | grep -v grep
```

### Re-scrape Specific State

```bash
python3 scrape_all_states.py --states AZ --headless
```

## 📈 Project History

### October 2024

- ✅ California expansion (26K+ listings)
- ✅ Monthly automation system built
- ✅ WordPress REST API integration
- ✅ Infinite pagination fix
- ✅ Multi-state scraper created

### Earlier

- Initial scrapers for Arizona
- WordPress import system
- Care type normalization
- Pricing enrichment

## 🎯 Next Steps

1. **Wait for scrape to complete** (~6-8 hours for all states)
2. **Compare each state** with WordPress
3. **Import NEW listings** via WordPress All Import
4. **Setup monthly cron** for automation

## 📞 Support

- **Scraper Issues**: Check `/tmp/scrape_all_unlimited.log`
- **WordPress Issues**: Check `monthly_updates/logs/`
- **Documentation**: See `docs/` folder

---

**Last Updated**: October 28, 2025  
**Maintained By**: AI Assistant (Claude)  
**Project Status**: ✅ Active & Running
