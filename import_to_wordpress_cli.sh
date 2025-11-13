#!/bin/bash

# WordPress WP-CLI Import Script
# Imports Senior Place listings from CSV to WordPress using WP-CLI

set -e  # Exit on error

# Configuration
WP_PATH="/path/to/wordpress"  # UPDATE THIS
CSV_FILE="$1"
DRY_RUN="${2:-false}"  # Pass "true" as second argument for dry run

if [ -z "$CSV_FILE" ]; then
    echo "Usage: ./import_to_wordpress_cli.sh <csv_file> [dry_run]"
    echo "Example: ./import_to_wordpress_cli.sh AZ_seniorplace_data_20251030.csv"
    echo "Example (dry run): ./import_to_wordpress_cli.sh AZ_seniorplace_data_20251030.csv true"
    exit 1
fi

if [ ! -f "$CSV_FILE" ]; then
    echo "Error: CSV file not found: $CSV_FILE"
    exit 1
fi

echo "========================================================================"
echo "WordPress WP-CLI Import"
echo "========================================================================"
echo "CSV File: $CSV_FILE"
echo "Dry Run: $DRY_RUN"
echo "========================================================================"
echo ""

# Count total lines (subtract header)
TOTAL_LINES=$(($(wc -l < "$CSV_FILE") - 1))
echo "Total listings to process: $TOTAL_LINES"
echo ""

# Read CSV and import
COUNTER=0
CREATED=0
SKIPPED=0
ERRORS=0

# Skip header line
tail -n +2 "$CSV_FILE" | while IFS=',' read -r title address city state zip url featured_image care_types care_types_raw; do
    COUNTER=$((COUNTER + 1))
    
    # Remove quotes from fields
    title=$(echo "$title" | sed 's/^"//;s/"$//')
    address=$(echo "$address" | sed 's/^"//;s/"$//')
    city=$(echo "$city" | sed 's/^"//;s/"$//')
    state=$(echo "$state" | sed 's/^"//;s/"$//')
    zip=$(echo "$zip" | sed 's/^"//;s/"$//')
    url=$(echo "$url" | sed 's/^"//;s/"$//')
    featured_image=$(echo "$featured_image" | sed 's/^"//;s/"$//')
    care_types=$(echo "$care_types" | sed 's/^"//;s/"$//')
    
    echo "[$COUNTER/$TOTAL_LINES] Processing: $title"
    
    # Check if listing already exists (by senior_place_url)
    EXISTING_ID=$(wp post list --post_type=listing --meta_key=senior_place_url --meta_value="$url" --field=ID --path="$WP_PATH" 2>/dev/null | head -n 1)
    
    if [ -n "$EXISTING_ID" ]; then
        echo "  ⏭️  Skipped (already exists, ID: $EXISTING_ID)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "  ✅ Would create: $title"
        echo "     Address: $address"
        echo "     State: $state"
        echo "     Care Types: $care_types"
        CREATED=$((CREATED + 1))
        continue
    fi
    
    # Create the post
    POST_ID=$(wp post create \
        --post_type=listing \
        --post_title="$title" \
        --post_status=draft \
        --porcelain \
        --path="$WP_PATH" 2>&1)
    
    if [ $? -ne 0 ] || [ -z "$POST_ID" ]; then
        echo "  ❌ Error creating post: $POST_ID"
        ERRORS=$((ERRORS + 1))
        continue
    fi
    
    echo "  ✅ Created post ID: $POST_ID"
    
    # Set ACF fields
    wp post meta update "$POST_ID" senior_place_url "$url" --path="$WP_PATH" 2>/dev/null
    wp post meta update "$POST_ID" address "$address" --path="$WP_PATH" 2>/dev/null
    
    # Set featured image if available
    if [ -n "$featured_image" ]; then
        echo "  📷 Setting featured image..."
        # Note: Would need to download and attach image - simplified here
        wp post meta update "$POST_ID" _thumbnail_url "$featured_image" --path="$WP_PATH" 2>/dev/null
    fi
    
    CREATED=$((CREATED + 1))
    
    # Progress indicator
    if [ $((COUNTER % 10)) -eq 0 ]; then
        echo ""
        echo "Progress: $COUNTER/$TOTAL_LINES (Created: $CREATED, Skipped: $SKIPPED, Errors: $ERRORS)"
        echo ""
    fi
done

echo ""
echo "========================================================================"
echo "Import Complete!"
echo "========================================================================"
echo "Total processed: $COUNTER"
echo "Created: $CREATED"
echo "Skipped (duplicates): $SKIPPED"
echo "Errors: $ERRORS"
echo "========================================================================"

