#!/bin/bash
#
# Monthly Update Scheduler Setup
# Configures cron job to run monthly updates automatically
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)

echo "🔧 Setting up monthly update scheduler..."
echo "Script directory: $SCRIPT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Create log directory
mkdir -p "$SCRIPT_DIR/monthly_updates/logs"

# Create wrapper script that activates environment and runs update
cat > "$SCRIPT_DIR/run_monthly_update.sh" << 'EOF'
#!/bin/bash
# Auto-generated monthly update runner

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/monthly_updates/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/update_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Log start
echo "========================================" >> "$LOG_FILE"
echo "Monthly Update Started: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Load credentials from environment or config
# You can set these in ~/.bashrc or ~/.zshrc:
# export WP_PASSWORD="your_wordpress_app_password"
# export SP_PASSWORD="Hugomax2025!"

cd "$SCRIPT_DIR"

# Run the update
python3 -u monthly_update_orchestrator.py \
    --full-update \
    --wp-url "https://aplaceforseniorscms.kinsta.cloud" \
    --wp-username "nicholas_editor" \
    --wp-password "${WP_PASSWORD}" \
    --sp-username "allison@aplaceforseniors.org" \
    --sp-password "${SP_PASSWORD}" \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

# Log completion
echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "Monthly Update Completed: $(date)" >> "$LOG_FILE"
echo "Exit Code: $EXIT_CODE" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Send notification email (if configured)
if [ -n "$NOTIFICATION_EMAIL" ]; then
    if [ $EXIT_CODE -eq 0 ]; then
        SUBJECT="✅ Monthly Update Success - $(date +%Y-%m-%d)"
    else
        SUBJECT="❌ Monthly Update Failed - $(date +%Y-%m-%d)"
    fi
    
    mail -s "$SUBJECT" "$NOTIFICATION_EMAIL" < "$LOG_FILE"
fi

exit $EXIT_CODE
EOF

chmod +x "$SCRIPT_DIR/run_monthly_update.sh"

echo "✅ Created runner script: run_monthly_update.sh"
echo ""

# Generate crontab entry
CRON_ENTRY="0 2 1 * * $SCRIPT_DIR/run_monthly_update.sh"

echo "📅 Suggested crontab entry (runs 1st of each month at 2am):"
echo ""
echo "    $CRON_ENTRY"
echo ""
echo "To install this cron job, run:"
echo ""
echo "    (crontab -l 2>/dev/null; echo \"$CRON_ENTRY\") | crontab -"
echo ""
echo "Alternative schedules:"
echo "  - Every 30 days at 2am:  0 2 */30 * * $SCRIPT_DIR/run_monthly_update.sh"
echo "  - Every Sunday at 3am:   0 3 * * 0 $SCRIPT_DIR/run_monthly_update.sh"
echo "  - 15th of month at 2am:  0 2 15 * * $SCRIPT_DIR/run_monthly_update.sh"
echo ""

# Check for required environment variables
echo "⚙️  Required environment variables:"
echo ""
echo "  WP_PASSWORD  - WordPress application password"
echo "  SP_PASSWORD  - Senior Place password (default: Hugomax2025!)"
echo "  NOTIFICATION_EMAIL - (optional) Email for notifications"
echo ""
echo "Add these to your ~/.bashrc or ~/.zshrc:"
echo ""
echo '  export WP_PASSWORD="your_app_password_here"'
echo '  export SP_PASSWORD="Hugomax2025!"'
echo '  export NOTIFICATION_EMAIL="your-email@example.com"'
echo ""

echo "✅ Setup complete!"
echo ""
echo "Manual test run:"
echo "  $SCRIPT_DIR/run_monthly_update.sh"
echo ""

