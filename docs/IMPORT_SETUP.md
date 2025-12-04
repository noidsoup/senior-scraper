# Import Setup Checklist

Before importing all listings, configure these settings:

---

## 1. State Term ID Mapping

Your WordPress uses term IDs for states. You need to map state abbreviations to term IDs.

**Option A: Use WP-CLI** (if you have server access)

```bash
wp term list location --format=json --fields=term_id,name,slug
```

**Option B: Check via REST API**
The script can auto-detect, but you may need to manually set these in `import_to_wordpress_api_safe.py`:

```python
STATE_MAPPING = {
    'AZ': 0,  # Lookup Arizona term ID
    'CA': 0,  # Lookup California term ID
    'CO': 0,  # Lookup Colorado term ID
    'ID': 0,  # Lookup Idaho term ID
    'NM': 0,  # Lookup New Mexico term ID
    'UT': 953,  # Already known
}
```

**Option C: Import without state mapping**
The script will still work - it just won't set the state taxonomy. You can set it manually later.

---

## 2. Care Type Term ID Mapping

Same as states - map care type names to term IDs.

**Current mapping in script:**

```python
CARE_TYPE_MAPPING = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}
```

**To verify/correct:**

```bash
wp term list listing_type --format=json --fields=term_id,name
```

---

## 3. Batch Size Settings

Adjust based on your server:

- **Small batches (safer):** `--batch-size=25`
- **Medium batches:** `--batch-size=50` (default)
- **Large batches (faster):** `--batch-size=100`

**Recommendation:** Start with 25-50 for safety.

---

## 4. Import Order

Import smallest states first to test:

1. **New Mexico** (232 listings) - ~2 minutes
2. **Idaho** (303 listings) - ~3 minutes
3. **Utah** (384 listings) - ~4 minutes
4. **Colorado** (764 listings) - ~8 minutes
5. **Arizona** (2,304 listings) - ~25 minutes
6. **California** (14,752 listings) - ~2 hours

---

## 5. Review Test Listings

Before full import, review the 3 test listings created:

1. Go to WordPress admin: https://aplaceforseniorscms.kinsta.cloud/wp-admin
2. Navigate to Listings → All Listings
3. Filter by Status: Draft
4. Review the 3 test listings (IDs: 47505, 47506, 47507)
5. Check:
   - Title is correct
   - Address is populated
   - Senior Place URL is set
   - Status is Draft

**If everything looks good, proceed with import.**

---

## 6. Backup WordPress

Before importing thousands of listings:

```bash
# Export listings
wp post list --post_type=listing --format=csv > backup_$(date +%Y%m%d).csv

# Or full database backup
wp db export backup_$(date +%Y%m%d).sql
```

---

## Ready to Import?

Once you've reviewed test listings and are satisfied:

```bash
# Start with small state (New Mexico)
python3 import_to_wordpress_api_safe.py NM_seniorplace_data_20251030.csv --batch-size=25

# Then continue with other states
python3 import_to_wordpress_api_safe.py ID_seniorplace_data_20251030.csv --batch-size=25
python3 import_to_wordpress_api_safe.py UT_seniorplace_data_20251030.csv --batch-size=25
# ... etc
```

---

## If Something Goes Wrong

- **Import stops:** Use `--resume` flag to continue
- **Created duplicates:** Script automatically skips duplicates
- **Too many errors:** Check error log in checkpoint file
- **Need to rollback:** Delete draft listings in WordPress admin

---

**Current Status:**

- ✅ Test listings created (3)
- ⏳ Waiting for your review and configuration
- ⏳ Ready to import when you are
