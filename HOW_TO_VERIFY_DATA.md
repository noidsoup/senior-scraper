# How to Verify Scraped Data is Usable

## Quick Test (Run This Now)

After the scraper has been running for ~1 hour:

```bash
cd /Users/nicholas/Repos/senior-scrapr
python3 TEST_VERIFY_SCRAPED_DATA.py
```

## What the Test Checks

### ✅ PASS Criteria:
1. **Care Types are CLEAN** - Only these values allowed:
   - Assisted Living Home
   - Assisted Living Community
   - Independent Living
   - Memory Care
   - Nursing Home
   - Home Care

2. **NO FORBIDDEN values** like:
   - ❌ Directed Care
   - ❌ Personal Care
   - ❌ Supervisory Care
   - ❌ United Healthcare
   - ❌ MercyCare
   - ❌ All-Inclusive Pricing

3. **Titles are normalized**:
   - No LLC, INC, CORP suffixes
   - Title Case format
   - Example: "A Happy Place Adult Care Home" (not "A HAPPY PLACE ADULT CARE HOME LLC")

4. **All fields populated**:
   - title, address, city, state, zip
   - Senior Place URL
   - Featured image (when available)
   - Care types (when available)

### ❌ FAIL = Scraper is Broken

If test fails, the scraper needs to be fixed. DO NOT proceed with import.

## Test Output Example

The test will show:

```
======================================================================
DEFINITIVE DATA QUALITY TEST
======================================================================
Test run: 2025-10-30 12:15:00

📂 Testing file: AZ_seniorplace_data_20251030.csv
   File size: 245.3 KB
   Modified: 2025-10-30 12:10:23
   Total rows: 847

📊 DATA STATISTICS:
   Listings with care types: 812/847 (95.9%)
   Listings with images:     762/847 (90.0%)

✅ All care types are CLEAN (no forbidden types found)

======================================================================
SAMPLE DATA (10 random rows)
======================================================================

======================================================================
SAMPLE ROW #1
======================================================================
Title:           A Happy Place Adult Care Home
Address:         4918 East Karen Drive, Scottsdale, AZ 85254
City:            Scottsdale, AZ 85254
Senior Place:    https://app.seniorplace.com/communities/show/11f3157d-e0...
Featured Image:  ✅ YES
Care Types:      Assisted Living Home
                 ✅ CLEAN

... (9 more samples) ...

======================================================================
TEST RESULTS
======================================================================
✅ DATA IS USABLE AND CORRECT
   - Care types are clean
   - Titles are normalized
   - All fields properly populated
   - Ready for WordPress import
```

## When to Run This Test

1. **After 1 hour** - Check if scraper is working correctly
2. **After each state completes** - Verify that state's data
3. **Before WordPress import** - Final check before importing

## If Test Fails

**DO NOT PROCEED.** The scraper is broken and needs to be fixed.

Contact the developer (me) and show the test output.

## Manual Verification (If You Want Extra Confidence)

After test passes, you can manually spot-check:

```bash
# Show first 20 rows of Arizona data
head -21 AZ_seniorplace_data_20251030.csv | column -t -s','

# Count listings by care type
awk -F',' 'NR>1 {print $8}' AZ_seniorplace_data_20251030.csv | \
  sort | uniq -c | sort -rn
```

## Files Produced by Scraper

- `AZ_seniorplace_data_YYYYMMDD.csv` - Arizona listings
- `CA_seniorplace_data_YYYYMMDD.csv` - California listings
- `CO_seniorplace_data_YYYYMMDD.csv` - Colorado listings
- `ID_seniorplace_data_YYYYMMDD.csv` - Idaho listings
- `NM_seniorplace_data_YYYYMMDD.csv` - New Mexico listings
- `UT_seniorplace_data_YYYYMMDD.csv` - Utah listings

Each CSV is WordPress All Import ready with these columns:
- title
- address
- city
- state
- zip
- url (Senior Place URL)
- featured_image
- care_types (normalized)
- care_types_raw (original from site)

