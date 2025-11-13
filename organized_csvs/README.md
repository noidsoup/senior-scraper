# 📁 ORGANIZED CSV FILES - SENIOR SCRAPR PROJECT

## 🚀 **IMMEDIATE ACTION REQUIRED:**

### **01_WORDPRESS_IMPORT_READY.csv** ⭐ **UPLOAD THIS ONE TO WORDPRESS**
- **Purpose:** Final corrected file ready for WordPress import
- **Contains:** All listings with corrected Senior Place care types + existing Seniorly categories
- **Size:** 551KB
- **Status:** ✅ READY TO IMPORT

---

## 📋 **BACKUP & REFERENCE FILES:**

### **02_CURRENT_SITE_STATE_BACKUP.csv**
- **Purpose:** Current state of the live site (exported Aug 27)
- **Use:** Compare after import to verify changes
- **Size:** 497KB

### **03_PREVIOUS_IMPORT_ATTEMPT.csv**
- **Purpose:** Previous import file that was attempted
- **Use:** Reference only - don't import this
- **Size:** 528KB

### **04_PRE_IMPORT_BACKUP.csv**
- **Purpose:** Site backup before any imports (Aug 21)
- **Use:** Reference only - don't import this
- **Size:** 496KB

---

## 🔍 **SCRAPING & PROCESSING FILES:**

### **05_UNMAPPED_TYPES_REPORT.csv**
- **Purpose:** Listings with care types not in our mapping system
- **Use:** Review for potential mapping updates
- **Size:** 585 bytes

### **06_SCRAPING_OUTPUT_RAW.csv**
- **Purpose:** Raw output from Senior Place scraping
- **Use:** Debug scraping issues if needed
- **Size:** 553KB

### **07_SCRAPING_OUTPUT_PROCESSED.csv**
- **Purpose:** Processed scraping output with normalized types
- **Use:** Debug processing issues if needed
- **Size:** 546KB

---

## 🐛 **DEBUG & LOG FILES:**

### **08_DEBUG_MISSING_PRICES.csv**
- **Purpose:** Listings missing price data
- **Use:** Debug price scraping issues
- **Size:** 44KB

### **09_DEBUG_TYPE_UPDATES.csv**
- **Purpose:** Log of type field updates
- **Use:** Debug type mapping issues
- **Size:** 56KB

### **10_DEBUG_PRICE_UPDATES.csv**
- **Purpose:** Log of price field updates
- **Use:** Debug price updates
- **Size:** 7KB

---

## 📥 **ORIGINAL IMPORT FILES:**

### **11_ORIGINAL_MAIN_IMPORT.csv**
- **Purpose:** Original main import file
- **Use:** Reference only - don't import this
- **Size:** 518KB

### **12_MAIN_IMPORT_MISSING_PRICES.csv**
- **Purpose:** Main import file with missing prices identified
- **Use:** Reference only - don't import this
- **Size:** 269KB

---

## 🎯 **SUMMARY:**

**FOR WORDPRESS IMPORT:** Use **01_WORDPRESS_IMPORT_READY.csv**

**FOR REFERENCE:** Keep all other files organized

**FOR CLEANUP:** All old CSV files are now organized and labeled

---

## 🔧 **SCRAPING SCRIPTS:**

### **SCRAPING_SCRIPTS/scrape_seniorly_care_types.py**
- **Purpose:** Scrape accurate community types from Seniorly listings
- **Status:** ✅ **COMPLETED & TESTED**
- **Capability:** Handles 1,492 Seniorly-only listings with precise community type extraction
- **Key Feature:** Targets `<section id="care">` specifically to avoid global page template confusion
