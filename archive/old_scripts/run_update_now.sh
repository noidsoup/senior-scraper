#!/bin/bash
# Quick run script - execute monthly update RIGHT NOW

set -e

cd /Users/nicholas/Repos/senior-scrapr

# Check for required environment variable
if [ -z "$WP_PASSWORD" ]; then
    echo "❌ WP_PASSWORD not set"
    echo ""
    echo "Set it with:"
    echo "  export WP_PASSWORD='your_wordpress_app_password'"
    echo ""
    exit 1
fi

# Default Senior Place password if not set
SP_PASSWORD="${SP_PASSWORD:-Hugomax2025!}"

echo "🚀 Running monthly update NOW..."
echo ""
echo "States: ${STATES:-AZ CA CO UT ID NM WY CT AR}"
echo ""

# Run the update
python3 -u monthly_update_orchestrator.py \
    --full-update \
    --states ${STATES:-AZ CA CO UT ID NM WY CT AR} \
    --wp-url "${WP_URL:-https://aplaceforseniorscms.kinsta.cloud}" \
    --wp-username "${WP_USERNAME:-nicholas_editor}" \
    --wp-password "$WP_PASSWORD" \
    --sp-username "${SP_USERNAME:-allison@aplaceforseniors.org}" \
    --sp-password "$SP_PASSWORD"

echo ""
echo "✅ Update complete!"
echo ""
echo "Check output in: monthly_updates/"
ls -lt monthly_updates/ | head -5

