# ⚠️ CORRECT STATES FOR SCRAPING

## The 6 Hand-Picked States

Per the "A Place For Seniors" website, only these states are needed:

1. **Arizona**
2. **California**
3. **Colorado**
4. **Idaho**
5. **New Mexico**
6. **Utah**

## ❌ Do NOT Scrape

- Wyoming
- Connecticut
- Arkansas
- Any other states

## Why Only These 6?

From your website:

> "Our experts are up-to-date on the best communities in these hand-picked states"

These are your service areas.

## Correct Command

```bash
python3 scrape_all_states.py --states AZ CA CO ID NM UT --headless
```

## Current Run (In Progress)

The scraper is currently running with 8 states (includes WY, CT, AR by mistake).

- Let it finish since it's already at page 114 California
- Just ignore the WY, CT, AR data when done
- Future runs will use only the 6 correct states

## Estimated Totals

| State      | Estimated Listings |
| ---------- | ------------------ |
| Arizona    | 1,831 (confirmed)  |
| California | ~20,000            |
| Colorado   | ~2,000             |
| Idaho      | ~800               |
| New Mexico | ~600               |
| Utah       | ~1,500             |
| **TOTAL**  | **~26,700**        |

---

**Remember**: Only 6 states needed!  
**Saved to memory**: AI will remember for future sessions
