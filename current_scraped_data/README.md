# Current Scraped Data

This folder contains the most recent scraping results.

## Files

### State-Specific Scrapes

- `AZ_seniorplace_data_20251027.csv` - **1,831 Arizona listings** (Complete)
- `CA_seniorplace_data_20251027.csv` - **~20,000+ California listings** (In Progress)
- More states will be added as scraping completes...

### Comparison Results

- `NEW_CALIFORNIA_LISTINGS.csv` - **291 NEW California listings** not in WordPress
  - Ready to import via WordPress All Import
  - Already compared with existing WordPress data

## Usage

### Import New Listings

1. Open WordPress Admin → All Import
2. Upload `NEW_CALIFORNIA_LISTINGS.csv`
3. Map fields:
   - `title` → Post Title
   - `url` → ACF: senior_place_url
   - `featured_image` → Featured Image (download from URL)
   - `care_types` → Taxonomy: Type
   - `address`, `city`, `state`, `zip` → ACF fields
4. Run import

### Compare Other States

Once other states finish scraping, run comparison:

```bash
python3 ../monthly_scrapers/compare_[state]_quick.py
```

## Data Quality

- All listings include: title, full address, URL, featured image
- Care types normalized to WordPress taxonomy
- Duplicates removed via URL comparison
- Ready for direct WordPress import

## Next Steps

1. ✅ Arizona complete (1,831 listings)
2. 🔄 California scraping (~page 40 of 600+)
3. ⏳ Other 7 states queued
4. 📥 Import NEW_CALIFORNIA_LISTINGS.csv whenever ready

---

**Generated**: October 28, 2025  
**Source**: Senior Place (app.seniorplace.com)
