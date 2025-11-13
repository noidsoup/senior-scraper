# Folder Organization

Clean, organized structure for the senior-scrapr project.

## 📁 Root Directory Structure

```
senior-scrapr/
├── README.md                          ← Start here
├── FOLDER_ORGANIZATION.md             ← This file
├── memory.md                          ← AI session history
├── scrape_all_states.py               ← Main scraper (ACTIVE)
│
├── 📂 current_scraped_data/           ← Today's results
│   ├── AZ_seniorplace_data_*.csv      ← 1,831 Arizona listings ✅
│   ├── CA_seniorplace_data_*.csv      ← ~20K California listings 🔄
│   ├── NEW_CALIFORNIA_LISTINGS.csv    ← 291 new CA listings 📥
│   └── README.md
│
├── 📂 monthly_updates/                ← Automated comparison results
│   └── YYYYMMDD_HHMMSS/
│       ├── new_listings_*.csv         ← NEW listings to import
│       ├── updated_listings_*.csv     ← Existing listings to update
│       └── update_summary_*.json      ← Statistics
│
├── 📂 monthly_scrapers/               ← Automation system
│   ├── monthly_update_orchestrator.py
│   ├── compare_california_quick.py
│   ├── send_monthly_report.py
│   ├── test_monthly_update.py
│   └── setup_monthly_scheduler.sh
│
├── 📂 scrapers_active/                ← Current working scrapers
│   ├── enhanced_seniorly_scraper.py
│   ├── scrape_live_senior_place_data.py
│   ├── scrape_seniorly_community_types.py
│   └── update_prices_from_seniorplace_export.py
│
├── 📂 scrapers_archive/               ← Old/experimental scrapers
│   └── [15 archived scrapers]
│
├── 📂 docs/                           ← Documentation
│   ├── MONTHLY_UPDATE_README.md
│   ├── QUICK_START_MONTHLY_UPDATES.md
│   ├── SYSTEM_OVERVIEW.md
│   ├── FOLDER_STRUCTURE.md
│   └── [other docs]
│
├── 📂 california_expansion/           ← CA expansion project
│   ├── [CA-specific scrapers]
│   ├── [CA data files]
│   └── archive_csvs/
│
├── 📂 wordpress_import/               ← Final import files
│   └── [9 CSV files ready for import]
│
├── 📂 organized_csvs/                 ← Organized data exports
│   └── [103 CSV files]
│
├── 📂 data_analysis/                  ← Analysis scripts
│   └── [41 Python scripts]
│
├── 📂 data_outputs/                   ← Intermediate outputs
│   └── [various JSON and CSV files]
│
├── 📂 test_scripts/                   ← Test scripts
│   └── [23 test Python scripts]
│
├── 📂 tools/                          ← Utility tools
│   └── [11 helper scripts]
│
├── 📂 data/                           ← Checkpoints and logs
│   ├── checkpoints/
│   └── logs/
│
└── 📂 archive/                        ← Old/inactive files
    ├── old_state_fixes/               ← Deprecated state fix scripts
    ├── old_scripts/                   ← One-off utility scripts
    ├── test_csvs/                     ← Test data files
    └── logs/                          ← Old log files
```

## 🎯 Quick Navigation

### I want to...

**Scrape a state:**
→ `python3 scrape_all_states.py --states AZ`

**Find new listings:**
→ `current_scraped_data/NEW_CALIFORNIA_LISTINGS.csv`

**Setup automation:**
→ `docs/QUICK_START_MONTHLY_UPDATES.md`

**Import to WordPress:**
→ `wordpress_import/` or `current_scraped_data/`

**Check scraper progress:**
→ `tail -f /tmp/scrape_all_unlimited.log`

**Understand the system:**
→ `docs/SYSTEM_OVERVIEW.md`

## 📋 File Types by Location

### CSVs

- `current_scraped_data/` - TODAY's scrape results
- `organized_csvs/` - Historical organized data
- `wordpress_import/` - Ready for import
- `california_expansion/` - CA project data
- `archive/test_csvs/` - Test/sample files

### Python Scripts

- Root: `scrape_all_states.py` (main scraper)
- `scrapers_active/` - Current working scrapers
- `monthly_scrapers/` - Automation system
- `data_analysis/` - Analysis tools
- `test_scripts/` - Test utilities
- `archive/old_scripts/` - Deprecated scripts

### Documentation

- Root: `README.md`, `memory.md`
- `docs/` - All guides and documentation
- Each subfolder has its own `README.md`

### Logs

- `/tmp/scrape_all_unlimited.log` - Current scraper
- `data/logs/` - System logs
- `archive/logs/` - Old logs

## 🧹 Cleanup Rules

### Keep in Root

- `README.md` - Project overview
- `memory.md` - AI session history
- `scrape_all_states.py` - Main active scraper
- `FOLDER_ORGANIZATION.md` - This file

### Archive These

- One-off scripts → `archive/old_scripts/`
- Test/sample CSVs → `archive/test_csvs/`
- Old logs → `archive/logs/`
- Deprecated state fixes → `archive/old_state_fixes/`

### Active Directories

- `current_scraped_data/` - Clear old after import
- `monthly_updates/` - Keep last 3 months
- `scrapers_active/` - Only working scrapers
- `docs/` - Keep all documentation

## 🔄 Maintenance Schedule

**Daily:**

- Check scraper progress: `tail /tmp/scrape_all_unlimited.log`

**Weekly:**

- Clear old `current_scraped_data/` after import
- Review `monthly_updates/` for processing

**Monthly:**

- Archive old `monthly_updates/` (keep 3 months)
- Update `memory.md` with session notes
- Review and archive unused scripts

**Quarterly:**

- Clean `data_outputs/` of old intermediate files
- Review `organized_csvs/` for consolidation
- Update documentation

---

**Last Organized**: October 28, 2025  
**Organization Pattern**: Active files up front, archives in subfolders  
**Principle**: Everything has a place, nothing in root unless active
