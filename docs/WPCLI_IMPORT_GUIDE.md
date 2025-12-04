# WordPress WP-CLI Import Guide

Import Senior Place listings using WordPress command-line tools.

---

## Prerequisites

### 1. Install WP-CLI

**On your WordPress server:**

```bash
# Download WP-CLI
curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar

# Make it executable
chmod +x wp-cli.phar

# Move to system path
sudo mv wp-cli.phar /usr/local/bin/wp

# Test it
wp --info
```

### 2. SSH Access to WordPress Server

You need SSH access to the server where WordPress is installed.

```bash
ssh user@your-wordpress-server.com
```

### 3. Upload CSV Files

Transfer the CSV files to your server:

```bash
# From your local machine
scp *_seniorplace_data_20251030.csv user@server:/path/to/uploads/
```

---

## Step 1: Get WordPress Term IDs

Before importing, you need to get the term IDs for states and care types from your WordPress database.

### Run the Term ID Lookup Script

```bash
# Navigate to WordPress directory
cd /var/www/html/wordpress

# Copy the script to server (if not already there)
# Then run it:
python3 get_wordpress_term_ids.py

# OR specify WordPress path
python3 get_wordpress_term_ids.py --wp-path=/var/www/html/wordpress
```

### Expected Output

```
📍 Fetching Location/State Terms:
  Arizona         → ID: 1234  ('AZ')
  California      → ID: 5678  ('CA')
  Colorado        → ID: 910   ('CO')
  Idaho           → ID: 1112  ('ID')
  New Mexico      → ID: 1314  ('NM')
  Utah            → ID: 953   ('UT')

Python mapping:
STATE_MAPPING = {
    'AZ': 1234,
    'CA': 5678,
    'CO': 910,
    'ID': 1112,
    'NM': 1314,
    'UT': 953,
}

🏥 Fetching Care Type Terms:
  Assisted Living Community → ID: 5     ('Assisted Living Community')
  Assisted Living Home      → ID: 162   ('Assisted Living Home')
  Independent Living        → ID: 6     ('Independent Living')
  Memory Care               → ID: 3     ('Memory Care')
  Nursing Home              → ID: 7     ('Nursing Home')
  Home Care                 → ID: 488   ('Home Care')

Python mapping:
CARE_TYPE_MAPPING = {
    'Assisted Living Community': 5,
    'Assisted Living Home': 162,
    'Independent Living': 6,
    'Memory Care': 3,
    'Nursing Home': 7,
    'Home Care': 488,
}
```

### Update the Import Script

Copy the mappings and paste them into `import_to_wordpress_wpcli.py`:

```python
# Replace these sections in the script
STATE_MAPPING = {
    'AZ': 1234,  # Your actual IDs from the lookup
    'CA': 5678,
    # ...
}

CARE_TYPE_MAPPING = {
    'Assisted Living Community': 5,  # Your actual IDs
    'Assisted Living Home': 162,
    # ...
}
```

---

## Step 2: Test Import (Dry Run)

Always test first with a dry run!

```bash
# Test with one small state (Utah)
python3 import_to_wordpress_wpcli.py UT_seniorplace_data_20251030.csv --dry-run

# OR specify WordPress path
python3 import_to_wordpress_wpcli.py UT_seniorplace_data_20251030.csv \
    --dry-run \
    --wp-path=/var/www/html/wordpress
```

### Expected Output

```
========================================================================
WordPress WP-CLI Import
========================================================================
CSV File: UT_seniorplace_data_20251030.csv
WP Path: auto-detect
Dry Run: True
========================================================================

🔍 Testing WP-CLI connection...
✅ Connected to WordPress: https://aplaceforseniorscms.kinsta.cloud

📊 Total listings to process: 384

[1/384] Processing: A-Plus Healthcare at Home - Home Health
  ✅ Would create: A-Plus Healthcare at Home - Home Health
     URL: https://app.seniorplace.com/communities/show/...
     Address: 1443 North 1200 West, Orem, UT 84057
     State: UT
     Care Types: Home Care

[2/384] Processing: ...
...

========================================================================
✅ Import Complete!
========================================================================
Total processed: 384
Created: 18
Skipped (duplicates): 366
Errors: 0
========================================================================

⚠️  This was a DRY RUN. No changes were made.
   Remove --dry-run flag to perform actual import.
```

---

## Step 3: Backup WordPress (IMPORTANT!)

Before importing, back up your WordPress database:

```bash
# Export all listings
wp post list --post_type=listing --format=csv > backup_listings_$(date +%Y%m%d).csv

# Or full database backup
wp db export backup_$(date +%Y%m%d).sql
```

---

## Step 4: Run Actual Import

Once you're satisfied with the dry run, do the real import:

### Import One State at a Time

```bash
# Start with smallest state (Utah)
python3 import_to_wordpress_wpcli.py UT_seniorplace_data_20251030.csv

# Then New Mexico
python3 import_to_wordpress_wpcli.py NM_seniorplace_data_20251030.csv

# Then Idaho
python3 import_to_wordpress_wpcli.py ID_seniorplace_data_20251030.csv

# Then Colorado
python3 import_to_wordpress_wpcli.py CO_seniorplace_data_20251030.csv

# Then Arizona (larger)
python3 import_to_wordpress_wpcli.py AZ_seniorplace_data_20251030.csv

# Finally California (largest)
python3 import_to_wordpress_wpcli.py CA_seniorplace_data_20251030.csv
```

### Or Import All States with a Loop

```bash
# Import all states
for state in UT NM ID CO AZ CA; do
    echo "Importing ${state}..."
    python3 import_to_wordpress_wpcli.py ${state}_seniorplace_data_20251030.csv
    echo "✅ ${state} complete"
    echo ""
done
```

---

## Step 5: Verify Import

After import, verify the data:

### Check Total Listings

```bash
wp post list --post_type=listing --format=count
```

### Check Sample Listings

```bash
# Get 5 random draft listings
wp post list --post_type=listing --post_status=draft --posts_per_page=5 --format=table
```

### Check ACF Fields

```bash
# Pick a listing ID from above and check its fields
wp post meta list <POST_ID>
```

### Search for Specific Listing

```bash
# Search by Senior Place URL
wp post list --post_type=listing \
    --meta_key=senior_place_url \
    --meta_value="https://app.seniorplace.com/communities/show/..." \
    --format=table
```

---

## Step 6: Publish Listings

Once verified, publish the listings:

### Publish All Draft Listings

```bash
# Get all draft listing IDs
wp post list --post_type=listing --post_status=draft --format=ids | xargs -n1 wp post update --post_status=publish
```

### Or Publish Selectively

```bash
# Publish only new Utah listings
wp post list --post_type=listing --post_status=draft --meta_key=_state --meta_value=UT --format=ids | xargs -n1 wp post update --post_status=publish
```

---

## Troubleshooting

### WP-CLI Not Found

```bash
# Make sure it's in your PATH
which wp

# Or use full path
/usr/local/bin/wp --info
```

### Permission Denied

```bash
# Run as WordPress user
sudo -u www-data wp post list --post_type=listing

# Or fix file permissions
sudo chown -R www-data:www-data /var/www/html/wordpress
```

### Duplicate Detection Not Working

The script checks for duplicates using `senior_place_url`. If duplicates are being created:

1. Verify the ACF field name is correct: `senior_place_url`
2. Check existing listings have this field populated

```bash
# Check if field exists on existing listings
wp post meta get <POST_ID> senior_place_url
```

### Import Stops Unexpectedly

Check WordPress error logs:

```bash
tail -f /var/log/nginx/error.log
# or
tail -f /var/log/apache2/error.log
```

---

## Performance Tips

### Speed Up Large Imports

For California's 14,752 listings:

```bash
# Disable object cache temporarily
wp cache flush

# Increase PHP memory limit
wp config set WP_MEMORY_LIMIT 512M

# Run import
python3 import_to_wordpress_wpcli.py CA_seniorplace_data_20251030.csv
```

### Run in Background

For very large imports:

```bash
# Run in background with logging
nohup python3 import_to_wordpress_wpcli.py CA_seniorplace_data_20251030.csv > import_ca.log 2>&1 &

# Check progress
tail -f import_ca.log
```

---

## Expected Import Times

| State     | Listings   | Estimated Time  |
| --------- | ---------- | --------------- |
| UT        | 384        | ~2 minutes      |
| NM        | 232        | ~1 minute       |
| ID        | 303        | ~2 minutes      |
| CO        | 764        | ~4 minutes      |
| AZ        | 2,304      | ~12 minutes     |
| CA        | 14,752     | ~75 minutes     |
| **TOTAL** | **18,739** | **~96 minutes** |

_Times assume ~130 listings/minute throughput_

---

## Summary of Files

| File                           | Purpose                         |
| ------------------------------ | ------------------------------- |
| `get_wordpress_term_ids.py`    | Lookup state/care type term IDs |
| `import_to_wordpress_wpcli.py` | Main import script (Python)     |
| `import_to_wordpress_cli.sh`   | Alternative bash script         |
| `WPCLI_IMPORT_GUIDE.md`        | This guide                      |

---

## Final Checklist

- ✅ WP-CLI installed and working
- ✅ CSV files uploaded to server
- ✅ Term IDs retrieved and added to script
- ✅ Dry run completed successfully
- ✅ WordPress backed up
- ✅ Import completed
- ✅ Listings verified
- ✅ Listings published

**You're done!** 🎉

Your WordPress site now has 18,739+ senior living listings with clean data, care types, and images ready to display.
