# Developer Guide

Technical documentation for contributing to the Senior Scraper project.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Dashboard (Flask)                     │
│                   localhost:5000                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   Orchestrator  │     │   WordPress     │
│   (Python)      │     │   REST API      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Senior Place   │     │   Kinsta WP     │
│  (Playwright)   │     │   Database      │
└─────────────────┘     └─────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Dashboard Backend | Flask 3.x |
| Dashboard Frontend | Vanilla HTML/CSS/JS |
| Scraping | Playwright (Chromium) |
| HTTP Requests | aiohttp, requests |
| Data Processing | Python csv, json |
| WordPress API | REST API v2 |

## Local Development Setup

### Prerequisites

- Python 3.10+
- Node.js (for Playwright browsers)
- Git

### Setup Steps

```bash
# 1. Clone
git clone https://github.com/CooperBold/senior-scraper.git
cd senior-scraper

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser
python -m playwright install chromium

# 5. Configure credentials
cp wp_config.example.env wp_config.env
# Edit wp_config.env with your test credentials

# 6. Run tests
python monthly_scrapers/test_monthly_update.py

# 7. Start dashboard
python web_interface/app.py
```

## Project Structure

```
senior-scraper/
├── web_interface/              # Flask web dashboard
│   ├── app.py                 # Main Flask app, API routes
│   ├── templates/
│   │   └── index.html         # Single-page dashboard
│   ├── logs/                  # Process logs (gitignored)
│   └── uploads/               # Uploaded CSVs (gitignored)
│
├── monthly_scrapers/           # Core business logic
│   ├── monthly_update_orchestrator.py  # Main entry point
│   ├── test_monthly_update.py          # System tests
│   ├── send_monthly_report.py          # Email notifications
│   └── compare_california_quick.py     # CA comparison utility
│
├── scrapers_active/            # Scraping modules
│   ├── scrape_live_senior_place_data.py  # Senior Place scraper
│   └── update_prices_from_seniorplace_export.py
│
├── docs/                       # Documentation
├── monthly_updates/            # Generated output (gitignored)
└── archive/                    # Legacy code (gitignored)
```

## Key Files

### `web_interface/app.py`

Flask application with these routes:

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Dashboard HTML |
| `/api/status` | GET | WordPress connection status |
| `/api/run-scraper` | POST | Start scraper subprocess |
| `/api/run-import` | POST | Start import subprocess |
| `/api/process-status/<name>` | GET | Check running process |
| `/api/stop-process/<name>` | POST | Kill running process |
| `/api/logs/<path>` | GET | Read log file contents |
| `/api/upload-csv` | POST | Upload CSV for import |
| `/api/fetch-single-listing` | POST | Scrape one listing by URL |
| `/api/test-connection` | GET | Run system tests |

### `monthly_scrapers/monthly_update_orchestrator.py`

Main orchestration logic:

1. Fetches all WordPress listings via REST API
2. Logs into Senior Place via Playwright
3. Scrapes each state's listings
4. Compares scraped data with WordPress
5. Generates CSV files for new/updated listings
6. Outputs summary JSON

### `scrapers_active/scrape_live_senior_place_data.py`

Senior Place scraper:

- Uses Playwright for browser automation
- Handles login, pagination, state filtering
- Extracts: title, address, care types, pricing, images
- Outputs CSV files per state

## Data Flow

```
Senior Place Website
        │
        ▼ (Playwright scrape)
Raw Listing Data
        │
        ▼ (Normalize care types)
Normalized Data
        │
        ▼ (Compare with WordPress)
┌───────┴───────┐
│               │
▼               ▼
NEW           UPDATED
Listings      Listings
│               │
▼               ▼
new_listings.csv  updated_listings.csv
        │
        ▼ (Import API)
WordPress Drafts
```

## Care Type Normalization

Senior Place uses various type names. We map them to canonical WordPress taxonomy terms:

```python
TYPE_MAPPING = {
    'assisted living home': 'Assisted Living Home',
    'assisted living facility': 'Assisted Living Facility',
    'independent living': 'Independent Living',
    'memory care': 'Memory Care',
    'skilled nursing': 'Skilled Nursing Facility',
    'adult day care': 'Adult Day Care',
    'directed care': 'Assisted Living Home',  # Special case
    # ... more mappings
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WP_URL` | Yes | WordPress site URL |
| `WP_USER` | Yes | WordPress username |
| `WP_PASSWORD` | Yes | WordPress app password |
| `SP_USERNAME` | Yes | Senior Place email |
| `SP_PASSWORD` | Yes | Senior Place password |
| `NOTIFICATION_EMAIL` | No | Email for reports |
| `SMTP_PASSWORD` | No | Gmail app password |

## Testing

### System Tests

```bash
python monthly_scrapers/test_monthly_update.py
```

Tests:
- Python dependencies installed
- Environment variables set
- WordPress API accessible
- Senior Place login works
- File structure correct

### Manual Testing

```bash
# Test WordPress API
curl -u "user:pass" "https://site/wp-json/wp/v2/listing?per_page=1"

# Test scraper (limited)
python scrapers_active/scrape_live_senior_place_data.py --limit 5 --state AZ

# Test Flask app
python -c "from web_interface.app import app; print('OK')"
```

## Adding a New State

1. The scraper already supports any state Senior Place has
2. Just add the state code to the orchestrator call:

```bash
python monthly_update_orchestrator.py --states AZ CA CO TX
```

3. Update documentation if it's a permanent addition

## Debugging

### Log Locations

| Log | Location |
|-----|----------|
| Dashboard processes | `web_interface/logs/` |
| Monthly updates | `monthly_updates/YYYYMMDD_HHMMSS/` |
| Flask server | Terminal stdout |

### Common Issues

**Scraper stuck on login:**
- Check SP_PASSWORD is correct
- Senior Place may have changed their login page
- Try running with `--headless=false` to watch

**WordPress API 401:**
- Verify WP_PASSWORD is an Application Password
- Check user has edit_posts capability
- Test with curl first

**Empty log files:**
- Fixed in recent update (unbuffered output)
- Ensure using latest code

## Contributing

1. Create a branch: `git checkout -b feature/my-feature`
2. Make changes
3. Run tests: `python monthly_scrapers/test_monthly_update.py`
4. Test dashboard manually
5. Commit: `git commit -m "Add feature X"`
6. Push: `git push origin feature/my-feature`
7. Open PR

## Code Style

- Python: Follow PEP 8
- Use f-strings for formatting
- Add docstrings to functions
- Keep functions under 50 lines
- Use type hints where helpful

## Security Checklist

Before committing:
- [ ] No hardcoded credentials
- [ ] No API keys in code
- [ ] `wp_config.env` in `.gitignore`
- [ ] No sensitive data in logs
- [ ] Test with `git diff` before push

