# State Checkbox Association - Solution

## Problem

Location taxonomy terms need to be associated with their State via ACF field `field_685dbc92bad4d`, but the ACF REST API is not enabled on the WordPress site.

## Current Status

✅ **Descriptions update successfully** via REST API  
❌ **State checkboxes do NOT update** via REST API (ACF not exposed)

## Solutions

### Option 1: Enable ACF REST API (Recommended)

**Requires:** WordPress admin access

1. Go to WordPress Admin → Custom Fields → Field Groups
2. Find the field group containing the "State" field (field_685dbc92bad4d)
3. Edit the field group settings
4. Enable "Show in REST API" option
5. Save changes

Once enabled, the existing script will work automatically!

### Option 2: Manual Bulk Edit (Quick Fix)

**For immediate use:**

1. Go to WordPress Admin → Locations
2. Select all locations that need state association
3. Use "Bulk Actions" → "Edit"
4. Check the appropriate state checkbox
5. Apply changes

### Option 3: WP CLI Script (Advanced)

**Requires:** Server SSH access

Create a WP CLI script to update term meta directly:

```php
<?php
// update_location_states.php
if (!defined('WP_CLI')) {
    die('WP CLI only');
}

function update_location_states_from_csv($csv_file) {
    $state_map = [
        'California' => 490,
        'Colorado' => 211,
        'Arizona' => 207,
        // ... etc
    ];

    $file = fopen($csv_file, 'r');
    fgetcsv($file); // skip header

    while (($row = fgetcsv($file)) !== FALSE) {
        $city = $row[0];
        $state = $row[1];
        $state_id = $state_map[$state] ?? null;

        if (!$state_id) continue;

        $term = get_term_by('name', $city, 'location');
        if ($term) {
            update_field('field_685dbc92bad4d', [$state_id], 'location_' . $term->term_id);
            WP_CLI::success("Updated $city → $state");
        }
    }
}

WP_CLI::add_command('update-location-states', 'update_location_states_from_csv');
```

Run with:

```bash
wp eval-file update_location_states.php missing_city_descriptions_generated.csv
```

### Option 4: Database Direct Update (Most Advanced)

**Requires:** Database access

```sql
-- Find the ACF meta key for state field
SELECT * FROM wp_termmeta WHERE meta_key LIKE '%685dbc92bad4d%' LIMIT 5;

-- Update term meta for a specific location
INSERT INTO wp_termmeta (term_id, meta_key, meta_value)
VALUES (512, 'field_685dbc92bad4d', 'a:1:{i:0;i:490;}')
ON DUPLICATE KEY UPDATE meta_value = 'a:1:{i:0;i:490;}';
```

## Recommendation

**Enable ACF REST API** (Option 1) - This is the cleanest solution and will make future updates automatic.

Until then, the script will successfully update **descriptions only**. State associations can be done manually or via WP CLI.

## Current Script Behavior

The `update_wp_locations_api.py` script will:

- ✅ Update location descriptions successfully
- ⚠️ Attempt to update state ACF field (will fail silently)
- ✅ Log all actions for review

No errors will occur - state checkboxes just won't be updated automatically.
