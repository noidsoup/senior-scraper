#!/bin/bash
# Senior Scraper Dashboard Launcher for Mac/Linux

echo "========================================"
echo "Senior Scraper Web Dashboard"
echo "========================================"
echo ""

# Load environment variables from wp_config.env
if [ -f wp_config.env ]; then
    echo "Loading environment variables..."
    export $(cat wp_config.env | grep -v '^#' | xargs)
    echo "Environment loaded!"
else
    echo "WARNING: wp_config.env not found!"
    echo "Please create wp_config.env with your credentials."
    exit 1
fi

echo ""
echo "Installing/checking Flask..."
python3 -m pip install flask>=3.0.0 --quiet

echo ""
echo "Starting dashboard at http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

cd web_interface
python3 app.py

