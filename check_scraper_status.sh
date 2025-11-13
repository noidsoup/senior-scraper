#!/bin/bash
# Quick status check for the production scraper

cd /Users/nicholas/Repos/senior-scrapr

echo "========================================================================"
echo "SCRAPER STATUS CHECK"
echo "========================================================================"
date
echo

# Check if running
if ps aux | grep -v grep | grep "scrape_all_states.py.*--states AZ CA CO ID NM UT" > /dev/null; then
    echo "✅ Scraper is RUNNING"
else
    echo "❌ Scraper is NOT running"
    exit 1
fi

# Show latest log
echo
echo "📄 Latest progress:"
echo "------------------------------------------------------------------------"
tail -20 production_run_FINAL.log
echo "------------------------------------------------------------------------"

# Show file sizes
echo
echo "📁 Output files:"
ls -lh *_seniorplace_data_*.csv 2>/dev/null | grep $(date +%Y%m%d) | tail -6

echo
echo "========================================================================"
echo "TO RUN DATA QUALITY TEST:"
echo "  python3 TEST_VERIFY_SCRAPED_DATA.py"
echo
echo "TO SEE FULL DOCUMENTATION:"
echo "  cat HOW_TO_VERIFY_DATA.md"
echo "========================================================================"

