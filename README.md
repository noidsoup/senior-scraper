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

## 🗓️ Monthly Workflow

1. **Start dashboard** → `start_dashboard.bat`
2. **Run scraper** → Select states, click "Search for Communities"
3. **Wait ~10 min** → Watch live logs
4. **Check results** → View new/updated counts
5. **Import to WP** → Go to "Add Communities" tab
6. **Review drafts** → Publish in WordPress admin

## 🧪 Testing

```bash
# Run system tests
python monthly_scrapers/test_monthly_update.py

# Test WordPress connection
curl -u "user:pass" "https://your-site/wp-json/wp/v2/listing?per_page=1"
```

## 📊 Coverage

| State | Listings | Status |
|-------|----------|--------|
| Arizona | ~1,800 | ✅ Active |
| California | ~20,000 | ✅ Active |
| Colorado | ~2,000 | ✅ Active |
| Idaho | ~800 | ✅ Active |
| New Mexico | ~600 | ✅ Active |
| Utah | ~1,500 | ✅ Active |

**Total**: ~26,000+ listings across 6 states

## 📖 Documentation

| Doc | Purpose |
|-----|---------|
| [User Guide](docs/USER_GUIDE.md) | Complete usage instructions |
| [Quick Reference](docs/QUICK_REFERENCE.md) | One-page cheat sheet |
| [Developer Guide](docs/DEVELOPER.md) | Contributing & architecture |

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
**Last Updated**: December 2024
