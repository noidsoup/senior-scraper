# Monthly Senior Place Update System

## Overview

This system automatically scrapes Senior Place, compares with your WordPress site, and generates CSVs of **NEW listings only** for manual import.

Run **once per month** to keep your site up-to-date.

---

## Quick Start

### Run Update Manually

```bash
./run_monthly_update.sh
```

This will:

1. ✅ Scrape ALL listings from Senior Place (6 states)
2. ✅ Fetch ALL listings from WordPress
3. ✅ Compare and find NEW listings
4. ✅ Generate `NEW_[STATE]_LISTINGS_YYYYMMDD.csv` files

**Time:** 4-6 hours total

---

## Setup Automatic Monthly Updates

Run once to setup:

```bash
./setup_monthly_cron.sh
```

This creates a cron job that runs on the **1st of every month at 2:00 AM**.

---

## What You Get

After the update runs, you'll have CSV files like:

```
NEW_AZ_LISTINGS_20251028.csv    (291 new Arizona listings)
NEW_CA_LISTINGS_20251028.csv    (1,043 new California listings)
NEW_CO_LISTINGS_20251028.csv    (87 new Colorado listings)
...etc
```

**Only NEW listings** (not already on your WordPress site) are included.

---

## How to Import

1. **Review the CSVs** - Check they look correct
2. **WordPress All Import**:
   - Upload the CSV
   - Map fields (title, address, care types, etc.)
   - Run import
3. **Archive** - Move CSVs to `archive/` folder after import

---

## States Covered

✅ Arizona (AZ)  
✅ California (CA)  
✅ Colorado (CO)  
✅ Idaho (ID)  
✅ New Mexico (NM)  
✅ Utah (UT)

---

## Checkpoint/Resume

The scraper **automatically saves progress every 50 pages**.

If it crashes or you stop it:

```bash
./run_monthly_update.sh  # Resumes from last checkpoint
```

Checkpoint files are stored as: `current_scraped_data/[STATE]_seniorplace_data_YYYYMMDD.csv.checkpoint`

---

## Files

| File                          | Purpose                               |
| ----------------------------- | ------------------------------------- |
| `scrape_all_states.py`        | Main scraper (with checkpoint/resume) |
| `compare_and_generate_new.py` | Compare with WordPress, generate CSVs |
| `run_monthly_update.sh`       | Master script (runs both steps)       |
| `setup_monthly_cron.sh`       | Install monthly cron job              |
| `current_scraped_data/`       | Raw scraped data                      |
| `NEW_*_LISTINGS_*.csv`        | Import-ready CSVs (NEW listings only) |
| `monthly_update_*.log`        | Full logs for each run                |

---

## Troubleshooting

### Scraper finds 0 listings

- Check Senior Place credentials in `scrape_all_states.py`
- Verify login works manually at app.seniorplace.com

### Comparison fails

- Check WordPress credentials in `compare_and_generate_new.py`
- Verify REST API is accessible

### Cron job doesn't run

- Check crontab: `crontab -l`
- Check logs: `ls -lh monthly_cron_*.log`
- Test manually first: `./run_monthly_update.sh`

---

## Support

Check these docs:

- `PROJECT_STATUS.md` - Current data coverage
- `README.md` - General project info
- `FOLDER_ORGANIZATION.md` - File structure

---

**Run monthly. Stay updated. Simple as that.**
