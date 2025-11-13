#!/bin/bash
################################################################################
# Setup monthly cron job for Senior Place updates
# Runs on the 1st of every month at 2 AM
################################################################################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CRON_CMD="0 2 1 * * cd $SCRIPT_DIR && ./run_monthly_update.sh >> monthly_cron_\$(date +\%Y\%m).log 2>&1"

echo "🔧 Setting up monthly cron job..."
echo ""
echo "Schedule: 1st of every month at 2:00 AM"
echo "Script: $SCRIPT_DIR/run_monthly_update.sh"
echo ""

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "run_monthly_update.sh"; then
    echo "⚠️  Cron job already exists!"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep "run_monthly_update.sh"
    echo ""
    read -p "Replace existing entry? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 1
    fi
    # Remove old entry
    crontab -l | grep -v "run_monthly_update.sh" | crontab -
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo ""
echo "✅ Cron job installed!"
echo ""
echo "📋 Current crontab:"
crontab -l
echo ""
echo "To remove: crontab -e (then delete the line)"
echo "To test now: ./run_monthly_update.sh"

