# Senior Scraper - Quick Reference Card

## Start Dashboard
```
start_dashboard.bat
```
Then open: **http://localhost:5000**

---

## Daily Tasks

| Task | Steps |
|------|-------|
| **Check status** | Open dashboard → view status cards |
| **Find new listings** | Find Communities tab → Select states → Start |
| **Look up one listing** | Single Listing tab → Paste URL → Fetch |
| **Import to WordPress** | Add Communities tab → Select CSV → Start |
| **View history** | Search History tab |
| **Test system** | Check System tab → Run Tests |

---

## Stop Things

| What | How |
|------|-----|
| Stop a scraper | Click red **⏹️ STOP** button |
| Stop dashboard | Press `Ctrl+C` in terminal |

---

## Files

| File | Purpose |
|------|---------|
| `start_dashboard.bat` | Launch dashboard |
| `wp_config.env` | Your credentials (secret!) |
| `web_interface/logs/` | Activity logs |
| `monthly_updates/` | Generated CSV files |

---

## Monthly Workflow

1. ▶️ Start dashboard
2. 🔍 Run "Find Communities" (all states)
3. ⏱️ Wait 5-10 minutes
4. 📊 Check "Search History" for results
5. 📥 Go to "Add Communities"
6. 📄 Select the new CSV file
7. ▶️ Click "Add Communities"
8. 📝 Review drafts in WordPress
9. ✅ Publish approved listings

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Won't start | Check wp_config.env exists |
| "Already running" | Restart dashboard |
| WordPress error | Run "Check System" tests |
| No CSV files | Run a scrape first |

---

## Support

📁 **Logs:** `web_interface/logs/`  
📖 **Full Guide:** `docs/USER_GUIDE.md`  
🧪 **Diagnostics:** Dashboard → Check System tab

