#!/bin/bash
# Quick progress check for production scrape

cd /Users/nicholas/Repos/senior-scrapr

echo "========================================================================"
echo "PRODUCTION SCRAPE PROGRESS CHECK"
echo "========================================================================"
date
echo

# Check if scraper is running
if ps aux | grep -v grep | grep "scrape_all_states.py" > /dev/null; then
    echo "✅ Scraper is RUNNING"
    echo
else
    echo "❌ Scraper is NOT running"
    echo
fi

# Show latest log file
LATEST_LOG=$(ls -t production_run_*.log 2>/dev/null | head -1)

if [ -n "$LATEST_LOG" ]; then
    echo "📄 Latest log: $LATEST_LOG"
    echo "📊 Log size: $(du -h "$LATEST_LOG" | cut -f1)"
    echo
    echo "Last 30 lines:"
    echo "------------------------------------------------------------------------"
    tail -30 "$LATEST_LOG"
    echo "------------------------------------------------------------------------"
else
    echo "⚠️  No log files found"
fi

echo
echo "Output files created:"
ls -lh *_seniorplace_data_*.csv 2>/dev/null | tail -10

echo
echo "========================================================================"

