#!/bin/bash
# Run monthly update NOW - generates CSVs only (safe, reviewable)

cd /Users/nicholas/Repos/senior-scrapr

# Check for WordPress password
if [ -z "$WP_PASSWORD" ]; then
    echo "❌ Need WordPress password"
    echo ""
    echo "Run this first:"
    echo '  export WP_PASSWORD="your_wordpress_app_password"'
    echo ""
    exit 1
fi

echo "🚀 Starting update (CSV generation only - safe mode)"
echo ""

# Run with all states (or specify fewer to test faster)
python3 -u monthly_update_orchestrator.py \
    --full-update \
    --wp-password "$WP_PASSWORD"

echo ""
echo "✅ DONE! CSVs generated in monthly_updates/"
echo ""
echo "Files created:"
ls -lh monthly_updates/*/new_listings_*.csv 2>/dev/null | tail -1
ls -lh monthly_updates/*/updated_listings_*.csv 2>/dev/null | tail -1
echo ""
echo "Review CSVs, then import to WordPress when ready."

