# Enable ACF Field REST API Access

## The Issue

The taxonomies (location, state) have REST API enabled ✅  
BUT the **ACF Field Group** that contains the State field does NOT have REST API enabled ❌

## Solution: Enable ACF Field Group REST API

### Step 1: Find the Field Group

1. In WordPress Admin, go to **Custom Fields** → **Field Groups** (not Taxonomies)
2. Look for a field group that is assigned to the "Location" taxonomy
3. It will contain the "State" field (field key: `field_685dbc92bad4d`)

### Step 2: Edit Field Group Settings

1. Click to edit that field group
2. Look for **"Show in REST API"** setting (usually in the field group settings panel on the right side)
3. **Enable/Check** the "Show in REST API" option
4. Click **Update** to save

### Step 3: Verify

After enabling, test with:

```bash
curl -s "https://aplaceforseniorscms.kinsta.cloud/wp-json/wp/v2/location/512" \
  -u "${WP_USER}:${WP_PASS}" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print('ACF fields:', data.get('acf', {}))"
```

If it returns ACF field data (not just `[]`), it's working!

## Alternative: Check ACF Settings

If you can't find the field group, try:

1. Go to **Custom Fields** → **Field Groups**
2. Look for any field group with "Location Fields" or similar name
3. Check its "Location" rules - it should show "Taxonomy is equal to location"

## What This Enables

Once REST API is enabled for the ACF Field Group:

- ✅ Location descriptions will update (already working)
- ✅ State checkboxes will update automatically
- ✅ Full automation of all 286 cities!

## Current Workaround

Until ACF REST API is enabled, the script will:

- ✅ Update all descriptions successfully
- ❌ State associations will need manual bulk edit

Let me know once you've enabled it and we can test!
