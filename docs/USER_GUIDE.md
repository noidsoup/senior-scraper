# Senior Scraper Dashboard - User Guide

> A simple web interface for managing senior living community data

---

## Quick Start

### Windows
```
Double-click: start_dashboard.bat
```

### Then Open Your Browser
```
http://localhost:5000
```

That's it! The dashboard loads automatically.

---

## What This Tool Does

The Senior Scraper Dashboard helps you:

1. **Find new communities** - Scrapes Senior Place for senior living listings
2. **Compare with your database** - Checks what's already in WordPress
3. **Import new listings** - Adds new communities as draft posts
4. **Track changes** - See pricing and care type updates

---

## Dashboard Overview

When you open the dashboard, you'll see:

### Status Cards (Top Row)

| Card | What It Shows |
|------|---------------|
| **WordPress Status** | Connection status + total listings count |
| **Environment** | Whether credentials are configured |
| **Last Run** | Results from the most recent scrape |

### Main Tabs

| Tab | Purpose |
|-----|---------|
| 🔍 **Find Communities** | Run the scraper to find new listings |
| 📌 **Single Listing** | Fetch one specific listing by URL |
| 📥 **Add Communities** | Import CSV files to WordPress |
| 📜 **Search History** | View past scraper runs |
| 🧪 **Check System** | Test that everything is working |

---

## How To: Find New Communities

1. Click the **"🔍 Find Communities"** tab
2. Check/uncheck the states you want to search
3. Click **"🚀 Search for Communities"**
4. Watch the live logs as it runs
5. When done, check results in **"📜 Search History"**

**Time:** About 5-10 minutes for all 6 states

**What happens:**
- Logs into Senior Place
- Scrapes listings for each state
- Compares with WordPress
- Generates CSV files with new/updated listings

---

## How To: Import a Single Listing

1. Click the **"📌 Single Listing"** tab
2. Paste a Senior Place URL:
   ```
   https://app.seniorplace.com/communities/show/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
3. Click **"🔗 Fetch Listing"**
4. Preview the data
5. Use the info to manually add to WordPress if needed

**Use this for:**
- Quick data verification
- Checking a specific community
- Testing before bulk imports

---

## How To: Import to WordPress

1. Click the **"📥 Add Communities"** tab
2. Select a CSV file from the dropdown
3. Set **Batch Size** (default 25 is good)
4. Optionally set a **Limit** for testing (e.g., 5)
5. Click **"📥 Add Communities"**
6. Watch the progress in real-time

**Important:**
- All imports create **DRAFT** posts (not published)
- Review drafts in WordPress before publishing
- Duplicates are automatically skipped

---

## How To: Stop a Running Process

If you need to cancel a scraper or import:

1. Look for the red **"⏹️ STOP"** button
2. Click it
3. Wait for confirmation

The process will be terminated and you can start fresh.

---

## How To: Test the System

1. Click the **"🧪 Check System"** tab
2. Click **"🧪 Run Tests"**
3. Wait about 30 seconds
4. Review results

**What gets tested:**
- Python dependencies installed
- WordPress API connection
- Senior Place login
- File permissions

**Expected result:** All green checkmarks ✅

---

## Troubleshooting

### Dashboard won't start

**Check:**
- Is Python installed? Run `python --version`
- Is `wp_config.env` file present?
- Are credentials correct in the file?

**Try:**
```
cd senior-scraper
python -m pip install flask
python web_interface/app.py
```

### "Scraper is already running"

**Cause:** A previous scrape didn't finish cleanly

**Fix:** Close the dashboard (Ctrl+C) and restart it

### WordPress shows "Disconnected"

**Check:**
- Is `WP_PASSWORD` correct in `wp_config.env`?
- Is the WordPress site accessible?
- Is the Application Password valid?

**Test:** Click "🧪 Check System" for detailed errors

### No CSV files showing in dropdown

**Cause:** No scraper runs have completed yet

**Fix:** Run a scrape first, then the CSV files will appear

### Tests show failures

**Check:**
- Environment variables are set
- Internet connection is working
- Senior Place hasn't changed their login

---

## File Locations

| What | Where |
|------|-------|
| Dashboard | `web_interface/app.py` |
| Config file | `wp_config.env` |
| Scraper logs | `web_interface/logs/` |
| Generated CSVs | `monthly_updates/YYYYMMDD_HHMMSS/` |
| State data | `*_seniorplace_data_*.csv` |

---

## Configuration

### wp_config.env

Your credentials file. Never share this!

```env
# WordPress
WP_URL=https://your-site.kinsta.cloud
WP_USER=your_username
WP_PASSWORD="your app password"

# Senior Place
SP_USERNAME="email@example.com"
SP_PASSWORD="password"
```

### Getting a WordPress App Password

1. Log into WordPress admin
2. Go to Users → Your Profile
3. Scroll to "Application Passwords"
4. Enter a name (e.g., "Senior Scraper")
5. Click "Add New"
6. Copy the password (spaces are part of it!)

---

## Best Practices

### Before Running a Scrape

- ✅ Check system connection first
- ✅ Start with one state to test
- ✅ Keep the browser open to watch progress

### Before Importing

- ✅ Review the CSV file contents
- ✅ Test with limit=5 first
- ✅ Check WordPress drafts after import

### Monthly Workflow

1. **First of month:** Run full scrape (all 6 states)
2. **Review:** Check history for new/updated counts
3. **Import:** Add new listings as drafts
4. **Publish:** Review and publish in WordPress

---

## Getting Help

### Check Logs

All operations are logged. Find them in:
```
web_interface/logs/
```

### Run Diagnostics

Click **"🧪 Check System"** for a full health check.

### Common Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| "Scraper already running" | Previous process still active | Restart dashboard |
| "WordPress credentials missing" | Config not loaded | Check wp_config.env |
| "Connection timeout" | Network issue | Check internet, try again |
| "Login failed" | Wrong password | Update wp_config.env |

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Stop dashboard | `Ctrl+C` (in terminal) |
| Refresh page | `F5` or `Ctrl+R` |
| Open dev tools | `F12` |

---

## FAQ

**Q: How long does a full scrape take?**
A: About 5-10 minutes for all 6 states.

**Q: Will it create duplicates?**
A: No. The system checks URLs and addresses before importing.

**Q: Can I run it while doing other work?**
A: Yes! The scraper runs in the background.

**Q: What if I close my browser?**
A: The scraper keeps running. Just reopen localhost:5000.

**Q: How do I add more states?**
A: Contact your developer to add state configurations.

---

*Last Updated: November 2025*

