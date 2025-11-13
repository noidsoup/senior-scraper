# How to Run Monthly Updates

## Quick Summary

**Every month, run these 3 commands:**

1. **Scrape** → Get latest data from Senior Place
2. **Generate** → Find NEW listings (not in WordPress yet)
3. **Import** → Add new listings as drafts

---

## Step-by-Step (Monthly)

### Step 1: Scrape Latest Data

Scrapes all 6 states from Senior Place:

```bash
cd /Users/nicholas/Repos/senior-scrapr
python3 -u scrape_all_states.py --states AZ CA CO ID NM UT --headless > production_run_$(date +%Y%m%d_%H%M%S).log 2>&1
```

**Time:** ~6-8 hours (runs in background)

**Output:** Creates files like:
- `AZ_seniorplace_data_20251111.csv`
- `CA_seniorplace_data_20251111.csv`
- etc.

**Check progress:**
```bash
tail -f production_run_*.log
```

---

### Step 2: Generate Candidate List (NEW listings only)

Compares scraped data with WordPress to find what's NEW:

```bash
cd /Users/nicholas/Repos/senior-scrapr
python3 monthly_generate_candidates.py \
  --states AZ CA CO ID NM UT \
  --output data/processed/monthly_candidates_$(date +%Y%m%d).csv
```

**Time:** ~2-3 minutes

**Output:** `data/processed/monthly_candidates_YYYYMMDD.csv`

**What it does:**
- Finds listings NOT already in WordPress
- Skips duplicates (by URL and address)
- Filters out blocklisted titles
- Normalizes titles (removes LLC, DBA, etc.)

---

### Step 3: Import to WordPress (as drafts)

Imports new listings as drafts for you to review:

```bash
cd /Users/nicholas/Repos/senior-scrapr
python3 import_to_wordpress_api_safe.py \
  data/processed/monthly_candidates_YYYYMMDD.csv \
  --batch-size 25 \
  --resume
```

**Time:** ~10-30 minutes (depending on how many new listings)

**What it does:**
- Creates drafts in WordPress
- Uploads featured images
- Sets care types, state, location taxonomies
- Skips duplicates automatically
- Saves checkpoint (can resume if interrupted)

**Monitor progress:**
```bash
tail -f wordpress_import_progress.log
```

---

## After Import

1. **Review drafts** in WordPress admin:
   - https://aplaceforseniorscms.kinsta.cloud/wp-admin/edit.php?post_type=listing&post_status=draft

2. **Publish** the ones you want to go live

3. **Delete** any you don't want

---

## Tips

- **Resume interrupted imports:** Just re-run Step 3 with `--resume` flag
- **Test first:** Add `--limit 5` to Step 3 to test with just 5 listings
- **Check for errors:** Look for "❌ Error" in the log file
- **Rate limiting:** Script automatically slows down to avoid server overload

---

## Example Monthly Workflow

```bash
# Day 1: Start scraping (runs overnight)
python3 -u scrape_all_states.py --states AZ CA CO ID NM UT --headless > production_run_$(date +%Y%m%d).log 2>&1 &

# Day 2: After scraping completes, generate candidates
python3 monthly_generate_candidates.py --states AZ CA CO ID NM UT --output data/processed/monthly_candidates_$(date +%Y%m%d).csv

# Day 2: Import new listings
python3 import_to_wordpress_api_safe.py data/processed/monthly_candidates_$(date +%Y%m%d).csv --batch-size 25

# Day 2: Review and publish drafts in WordPress admin
```

---

## Troubleshooting

**"No new candidates found"**
- Normal if no new listings were added to Senior Place
- Double-check by looking at the scraped CSV dates

**"Duplicate detected"**
- Good! The system is working correctly
- It means that listing already exists in WordPress

**Import fails partway through**
- Just re-run Step 3 with `--resume` flag
- It will continue from where it stopped

**Server errors (500)**
- Script automatically retries
- If persistent, increase delays in `import_to_wordpress_api_safe.py`:
  - `RATE_LIMIT_DELAY = 2.0` → `3.0`
  - `BATCH_PAUSE = 10` → `15`

