# Pagination Loop Bug - FIXED

## Date: October 30, 2025

## Problem

The scraper was stuck in an infinite loop, collecting the same listings repeatedly. Arizona scrape collected **4,256 total entries** but only **2,304 were unique** - **1,952 duplicates** (41% duplication).

### Root Cause

Senior Place's pagination shows the same listings on multiple pages after reaching the real end of results. The scraper had no duplicate detection, so it kept adding the same listings over and over.

## Solution

Added comprehensive duplicate detection and loop prevention:

### 1. **Duplicate URL Tracking**

```python
seen_urls = set()  # Track all URLs we've already processed

# Skip duplicates during scraping
if url in seen_urls:
    continue

# Mark URL as seen when adding listing
seen_urls.add(url)
```

### 2. **Loop Detection**

```python
consecutive_duplicate_pages = 0
MAX_DUPLICATE_PAGES = 50

# Track pages where ALL listings were duplicates
if new_listings_this_page == 0 and state_count > 0:
    consecutive_duplicate_pages += 1
    if consecutive_duplicate_pages >= MAX_DUPLICATE_PAGES:
        print("🛑 Pagination is looping - all listings collected")
        break
```

### 3. **Checkpoint Resume Protection**

When resuming from checkpoint, populate `seen_urls` with all previously collected URLs to prevent re-adding duplicates:

```python
seen_urls_from_checkpoint = {listing['url'] for listing in all_listings}
seen_urls = seen_urls_from_checkpoint
```

## Results

### Arizona Data (Completed)

- **File:** `AZ_seniorplace_data_20251030.csv`
- **Total unique listings:** 2,304
- **With care types:** 2,222/2,304 (96.4%)
- **With images:** 2,079/2,304 (90.2%)
- **Status:** ✅ COMPLETE

### Remaining States (In Progress)

Currently scraping:

- California
- Colorado
- Idaho
- New Mexico
- Utah

**Log file:** `production_run_5states.log`

## How It Works Now

1. **Scraper processes each page**
2. **Checks each listing URL against `seen_urls`**
3. **Skips if already seen** (duplicate)
4. **Adds to `seen_urls` if new**
5. **Tracks consecutive pages with only duplicates**
6. **Stops after 50 consecutive duplicate-only pages** (pagination loop detected)

## Expected Completion

- **California:** Largest dataset, ~4-6 hours
- **Other states:** 1-2 hours each
- **Total:** Tonight by ~11 PM

All states will automatically stop when pagination loops are detected, ensuring clean, deduplicated data.
