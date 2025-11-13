# Update California Location Descriptions

This guide shows how to update the existing WordPress locations taxonomy with the California city descriptions.

## Current State

From the WordPress admin, I can see:
- ✅ **947 location terms** already exist in the taxonomy
- ✅ **California cities are present** (Acton, Adelanto, Alamo, etc.)
- ❌ **California cities showing "—No description"** - need to be updated

## Import Instructions

### Option 1: WP All Import (Recommended)

1. **Go to WP All Import** → New Import
2. **Upload** `CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT_FLAT.csv`
3. **Set Post Type** to **"Taxonomies"**
4. **Map the columns:**
   ```
   taxonomy    → Taxonomy (locations)
   parent      → Parent (leave blank)
   name        → Term Name (Acton, Adelanto, etc.)
   slug        → Term Slug (acton, adelanto, etc.)
   description → Term Description
   ```
5. **Import Settings:**
   - ✅ **Update existing terms** (if term exists, update description)
   - ✅ **Create new terms** (for any missing cities)
6. **Run the import**

### Option 2: Manual Updates
If you prefer to update manually:
1. Go to **Locations** in WordPress admin
2. Click **Edit** on each California city
3. Copy/paste the description from the CSV
4. Save

## Files Generated

✅ **CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT_FLAT.csv** (313 terms)
- Format: Flat taxonomy structure matching your existing setup
- Cities: All 313 California cities from your descriptions
- Descriptions: Tailored for seniors with healthcare, lifestyle, and community info

✅ **CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT.csv** (313 terms)
- Format: Hierarchical (State > City) - alternative option

## Expected Results

After import, your California cities will have rich descriptions like:
- **Acton**: "Acton offers seniors affordable living in California's diverse landscape with access to excellent healthcare and community services..."
- **Los Angeles**: "Los Angeles offers seniors the perfect blend of coastal beauty and urban convenience. The city's temperate climate, excellent healthcare facilities, and vibrant senior community create an ideal retirement destination..."

## Verification

Use the verification script to confirm:
```bash
python3 verify_taxonomy_import.py
```

## Integration

These descriptions will enhance:
- City landing pages with SEO-rich content
- Location filtering and search results
- User experience when browsing by city
- Content marketing for city-specific pages
