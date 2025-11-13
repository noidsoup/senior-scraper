# CA Duplicate State Term - Cleanup Needed

## Issue

There are TWO state terms for California:

- ✅ **California** (ID: 490) - CORRECT, use this one
- ❌ **CA** (ID: 953) - DUPLICATE, should be deleted

## Impact

- Confusing in WordPress admin (two checkboxes for same state)
- Could cause data inconsistency if some locations use CA and others use California

## Solution Implemented in Script

The `update_wp_locations_api.py` script now maps both "CA" and "California" to ID 490:

```python
state_map = {
    'CA': 490,  # Map to California, not the duplicate
    'California': 490,
    # ...
}
```

This ensures the "CA" (953) checkbox will NEVER be checked by our automated updates.

## Recommended Cleanup (Optional)

To remove the duplicate "CA" term from WordPress:

### Option 1: WordPress Admin (Manual)

1. Go to WordPress Admin → Listings → States
2. Find the "CA" term (ID: 953)
3. If it has 0 listings associated, delete it
4. If it has listings, bulk edit those listings to use "California" instead, then delete

### Option 2: WP CLI (if you have server access)

```bash
# Check if CA term has any listings
wp term list state --field=name,count | grep "^CA"

# If count is 0, delete it
wp term delete state 953

# If count > 0, migrate listings first
wp post list --post_type=listing --state=953 --format=ids | \
  xargs -I {} wp post term set {} state 490

# Then delete the duplicate
wp term delete state 953
```

### Option 3: Leave It

The duplicate won't cause issues since our script never uses it. You can leave it if:

- Manual editors know to use "California" not "CA"
- It's not causing confusion

## Current Status

✅ Script configured to always use California (490)  
⚠️ Duplicate "CA" (953) term still exists in WordPress but won't be used
