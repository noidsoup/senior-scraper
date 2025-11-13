# Care Type Mapping Fix - Complete Solution

## Problem Identified ✅

Based on your conversation screenshots and analysis, the issue is:

**Your current mapping incorrectly converts "Assisted Living Facility" → "Assisted Living Community"**

This destroys the important distinction that Senior Place maintains:

- **Assisted Living Home** = Small homes (≤10 beds)
- **Assisted Living Facility** = Larger facilities
- **Independent Living** = Separate category entirely

## Root Cause ✅

The `TYPE_LABEL_MAP` in multiple scripts has this incorrect mapping:

```python
"assisted living facility": "Assisted Living Community",  # ❌ WRONG
```

This should be:

```python
"assisted living facility": "Assisted Living Facility",   # ✅ CORRECT
```

## Complete Solution

### Step 1: Create Missing WordPress Category 🏗️

**WordPress is missing the "Assisted Living Facility" category.**

**Manual creation (recommended):**

1. Log into https://aplaceforseniorscms.kinsta.cloud/wp-admin
2. Go to Listings → Categories
3. Add new category:
   - **Name:** Assisted Living Facility
   - **Slug:** assisted-living-facility
   - **Description:** Assisted living facilities - larger care facilities that provide assistance with daily activities
4. **Note the new category ID** (you'll need this)

**OR via WP-CLI:**

```bash
wp term create category 'Assisted Living Facility' --slug='assisted-living-facility' --description='Assisted living facilities - larger care facilities that provide assistance with daily activities'
```

### Step 2: Fix All Mapping Scripts 🔧

Update the `TYPE_LABEL_MAP` in these files:

- `fix_seniorplace_care_types.py`
- `update_prices_from_seniorplace_export.py`
- `sync_seniorly_from_sp_export.py`
- `search_seniorly_on_seniorplace.py`
- `sync_seniorly_care_types.py`

**Change from:**

```python
TYPE_LABEL_MAP = {
    "assisted living facility": "Assisted Living Community",  # ❌ WRONG
    "assisted living home": "Assisted Living Home",
    # ... rest unchanged
}
```

**Change to:**

```python
TYPE_LABEL_MAP = {
    "assisted living facility": "Assisted Living Facility",   # ✅ CORRECT
    "assisted living home": "Assisted Living Home",
    # ... rest unchanged
}
```

### Step 3: Re-scrape with Corrected Logic 🔄

Run the comprehensive fix script:

```bash
# After creating the WordPress category and getting its ID
python3 fix_care_type_mapping_comprehensive.py \
  --input "/Users/nicholas/Repos/senior-scrapr/organized_csvs/Listings-Export-2025-August-28-1956.csv" \
  --output "/Users/nicholas/Repos/senior-scrapr/organized_csvs/CORRECTED_CARE_TYPES_$(date +%Y%m%d_%H%M%S).csv" \
  --facility-category-id [NEW_CATEGORY_ID]
```

This will:

1. Re-scrape Senior Place to get **actual** care types (not our incorrect mappings)
2. Apply the **corrected** mapping logic
3. Generate a clean CSV for WordPress import

### Step 4: Import Corrected Data 📥

Import the corrected CSV using WordPress All Import with:

- Map `type` field to the Type taxonomy
- Use "Only assign existing terms" option
- Map `corrected_mapping_applied` to a custom field for verification

## Key Files Created

- `fix_facility_vs_community_mapping.py` - Analysis of current issues
- `create_assisted_living_facility_category.py` - WordPress category creation guide
- `fix_care_type_mapping_comprehensive.py` - Complete re-scraping solution
- `SOLUTION_SUMMARY.md` - This summary

## Expected Outcome ✅

After this fix:

- **Assisted Living Homes** → Correctly labeled as "Assisted Living Home" (small, ≤10 beds)
- **Assisted Living Facilities** → Correctly labeled as "Assisted Living Facility" (larger facilities)
- **CCRCs** → Still labeled as "Assisted Living Community" (appropriate)
- **Memory Care, Independent Living, etc.** → Unchanged (already correct)

## Memory Updated ✅

Updated memory ID 5208898 with the critical mapping error discovery and solution approach.

---

**Next Action:** Create the "Assisted Living Facility" category in WordPress and get its ID, then run the comprehensive fix script.
