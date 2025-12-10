# Senior Scraper 👴👵

A complete system for managing senior living community data - scrape listings from Senior Place, compare with WordPress, and import new communities.

## 🚀 Quick Start

### Option A: Web Dashboard (Recommended)

```bash
# Windows
start_dashboard.bat

# Mac/Linux
./start_dashboard.sh
```

Then open **http://localhost:5000**

### Option B: Command Line

```bash
# 1. Setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium

# 2. Configure credentials
cp wp_config.example.env wp_config.env
# Edit wp_config.env with your credentials

# 3. Run monthly update
python monthly_scrapers/monthly_update_orchestrator.py \
    --full-update \
    --states AZ CA CO ID NM UT \
    --wp-password "$WP_PASSWORD"
```

### Option C: Web Dashboard (BEST - One Click!)

The **recommended way** - complete visual interface with real-time progress:

```bash
start_dashboard.bat  # Windows
# or
./start_dashboard.sh  # Mac/Linux
```

**Features:**
- ✅ **One-click import** with pre-verification
- ✅ **Real-time progress** bars and logs
- ✅ **Upload or select** existing CSV files
- ✅ **Safe batch processing** with error recovery
- ✅ **Visual status** - no command line needed!

Open `http://localhost:5000` → **"Add Communities"** tab → Done!

### Option D: Command Line (Advanced)

For automated scripts or headless operation:

## 📊 What It Does

| Step | Action | Output |
|------|--------|--------|
| 1. **Scrape** | Fetches listings from Senior Place | Raw listing data |
| 2. **Compare** | Checks against WordPress database | New & updated lists |
| 3. **Generate** | Creates import-ready CSV files | `monthly_updates/` folder |
| 4. **Import** | Adds new listings as WordPress drafts | Draft posts for review |

## 🖥️ Web Dashboard Features

- 🔍 **Find Communities** - Scrape any combination of states
- 📌 **Single Listing** - Fetch one listing by URL
- 📥 **Add Communities** - Import CSV files or upload your own
- 📜 **History** - View past runs and statistics
- 🧪 **System Check** - Test all connections

## 📁 Project Structure

```
senior-scraper/
├── web_interface/           # Flask dashboard
│   ├── app.py              # Backend API
│   └── templates/          # Frontend HTML
├── monthly_scrapers/        # Core scraping logic
│   ├── monthly_update_orchestrator.py  # Main orchestrator
│   ├── test_monthly_update.py          # System tests
│   └── send_monthly_report.py          # Email reports
├── scrapers_active/         # Individual scrapers
├── docs/                    # Documentation
│   ├── USER_GUIDE.md       # End-user guide
│   ├── QUICK_REFERENCE.md  # Cheat sheet
│   └── DEVELOPER.md        # Developer setup
├── wp_config.example.env    # Credential template
└── requirements.txt         # Python dependencies
```

## ⚙️ Configuration

Create `wp_config.env` from the example:

```env
# WordPress API
WP_URL=https://your-site.kinsta.cloud
WP_USER=your_username
WP_PASSWORD="your application password"

# Senior Place Login
SP_USERNAME="email@example.com"
SP_PASSWORD="password"

# Optional: Email notifications
NOTIFICATION_EMAIL=you@example.com
```

## 🗓️ Operational Runbook

### Normal run (dashboard)
1. Start dashboard → `start_dashboard.bat` (Win) or `./start_dashboard.sh` (Mac/Linux).
2. Open `http://localhost:5000`, pick states, click **Search for Communities**.
3. Keep the tab open; live logs stream from `web_interface/logs/…`.
4. When finished, download `new_listings_*.csv` and `updated_listings_*.csv` from `monthly_updates/<timestamp>/`.
5. Import via dashboard **Add Communities** tab (uploads CSV and runs safe importer).
6. Review drafts in WordPress and publish as needed.

### Resume a stopped run
1. Find latest `monthly_updates/<timestamp>/resume_checkpoint.json`.
2. Re-run the orchestrator with `--full-update --resume --checkpoint <path>` (or from dashboard if supported).
3. It reloads cached raw state data and continues remaining states; enrichment re-runs as needed.

### Inspect logs / status
- Dashboard status/API: `http://localhost:5000/api/status`.
- Process tracking is persisted in `web_interface/logs/process_state.json` (PID, log path, start time).
- Live logs: `web_interface/logs/scraper_*.log` and importer logs `web_interface/logs/import_*.log`.

### Single listing spot-check
- Dashboard **Single Listing** tab → paste Senior Place URL (`/show/<id>`).
- Returns: title, address, city/state/zip, care types, pricing (base/high/second person), description, featured image URL.

### CLI run (headless)
```bash
python monthly_scrapers/monthly_update_orchestrator.py \
  --full-update \
  --states AZ CA CO ID NM UT \
  --wp-password "$WP_PASSWORD" \
  --sp-password "$SP_PASSWORD"
```

Outputs land in `monthly_updates/<timestamp>/` with `raw/*.json`, `new_listings_*.csv`, `updated_listings_*.csv`, and `update_summary_*.json`.

## 🧪 Testing

```bash
# Full suite (unit + integration)
python -m pytest tests -v

# System smoke
python monthly_scrapers/test_monthly_update.py

# WordPress connection
curl -u "user:pass" "https://your-site/wp-json/wp/v2/listing?per_page=1"
```

## 📊 Coverage (expected)

| State | Listings | Status |
|-------|----------|--------|
| Arizona | ~1,800 | ✅ Active |
| California | ~20,000 | ✅ Active |
| Colorado | ~2,000 | ✅ Active |
| Idaho | ~800 | ✅ Active |
| New Mexico | ~600 | ✅ Active |
| Utah | ~1,500 | ✅ Active |

**Total target**: ~26,000+ listings across 6 states (verify after each run)

## 📖 Documentation

| Doc | Purpose |
|-----|---------|
| [User Guide](docs/USER_GUIDE.md) | Complete usage instructions |
| [Quick Reference](docs/QUICK_REFERENCE.md) | One-page cheat sheet |
| [Developer Guide](docs/DEVELOPER.md) | Contributing & architecture |
| [Reliable Import](IMPORT_RELIABLE.md) | Guaranteed import process |

## 🔒 Security

- ✅ No credentials in code
- ✅ `.gitignore` excludes sensitive files
- ✅ Uses WordPress Application Passwords
- ✅ Environment-based configuration

## 📞 Support

1. **Check logs**: `web_interface/logs/`
2. **Run diagnostics**: Dashboard → "Check System" tab
3. **Review docs**: `docs/` folder

---

**Maintained by**: A Place for Seniors  
**Last Updated**: December 2025
