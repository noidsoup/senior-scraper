# Senior Scraper Web Dashboard

A visual interface for managing senior living community data.

## Quick Start

**Windows:**
```cmd
start_dashboard.bat
```

**Then open:** http://localhost:5000

## Features

- 🔍 **Find Communities** - Scrape Senior Place for new listings
- 📌 **Single Listing** - Fetch one community by URL  
- 📥 **Import to WordPress** - Add listings as drafts
- 📜 **History** - View past runs and statistics
- 🧪 **System Check** - Test all connections

## Requirements

- Python 3.10+
- Configured `wp_config.env` file

## Documentation

- **User Guide:** `docs/USER_GUIDE.md`
- **Quick Reference:** `docs/QUICK_REFERENCE.md`

## Credentials

Store in `wp_config.env` (never commit to git):

```env
WP_URL=https://your-site.kinsta.cloud
WP_USER=your_username
WP_PASSWORD="your app password"
SP_USERNAME="email@example.com"
SP_PASSWORD="password"
```

## Support

Run the **🧪 Check System** tab for diagnostics.

Logs are saved in `web_interface/logs/`
