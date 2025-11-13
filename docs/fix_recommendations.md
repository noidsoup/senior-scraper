# Fix Recommendations for Discovered Issues

## 🚨 **Priority 1: ZIP CODE SEARCH BROKEN**

### Problem

- 0% relevance rate across all zip codes
- No results found for any zip code searches
- Users can't find facilities by location

### Root Cause Analysis

Zip codes are likely stored in the `address` ACF field but WordPress search isn't indexing/searching ACF fields by default.

### Recommended Fixes

1. **Immediate Fix**: Add zip codes to post content or excerpt for indexing
2. **Better Fix**: Install SearchWP or similar plugin to index ACF fields
3. **Custom Fix**: Add custom search functionality that queries ACF address field

### Implementation

```php
// Add to functions.php - make ACF fields searchable
function make_acf_searchable($where, $wp_query) {
    if (!is_admin() && $wp_query->is_main_query() && $wp_query->is_search()) {
        global $wpdb;
        $search_term = $wp_query->get('s');
        if (!empty($search_term)) {
            $where .= " OR EXISTS (
                SELECT 1 FROM {$wpdb->postmeta}
                WHERE {$wpdb->postmeta}.post_id = {$wpdb->posts}.ID
                AND {$wpdb->postmeta}.meta_key = 'address'
                AND {$wpdb->postmeta}.meta_value LIKE '%{$search_term}%'
            )";
        }
    }
    return $where;
}
add_filter('posts_where', 'make_acf_searchable', 10, 2);
```

---

## 🚨 **Priority 2: COMMUNITY TYPE MAPPING CHAOS**

### Problem

- Same listings appearing in ALL care type categories
- "Yampa Makarios" and "Xanadu" assigned to 5+ different types simultaneously
- Users can't trust filter results

### Root Cause Analysis

The WordPress taxonomy assignment is corrupted - listings have multiple incorrect type assignments.

### Recommended Fixes

1. **Data Cleanup**: Remove incorrect taxonomy assignments
2. **Re-sync Types**: Use your existing mapping scripts to fix assignments
3. **Validation**: Add checks to prevent multiple conflicting types

### Implementation

```bash
# Run your existing care type sync script
cd /Users/nicholas/Repos/senior-scrapr
python3 fix_seniorplace_care_types.py --input organized_csvs/Listings-Export-2025-August-28-1956.csv

# Then import the corrected types via WP All Import
```

---

## 🚨 **Priority 3: MARIGOLD DUPLICATE ISSUE**

### Problem

- Posts 10521 & 8610 at same address with different titles
- Affecting search ranking for zip code 85048
- Confirmed case from user reports

### Recommended Fix

1. **Merge the duplicates** using your existing duplicate merge process
2. **Keep Senior Place version** (ID 8610) as primary
3. **Delete Seniorly duplicate** (ID 10521)

### Implementation

```csv
# Add to deletion CSV:
ID,Status
10521,trash
```

---

## ⚠️ **Priority 4: SEARCH WEIGHTING ALGORITHM**

### Problem

- Phoenix location search shows "mixed/unclear sorting"
- Higher relevance scores appearing after lower scores
- Search results not properly weighted

### Root Cause Analysis

WordPress default search doesn't weight by relevance - it sorts by date or alphabetical.

### Recommended Fixes

1. **Install Relevanssi** or **SearchWP** for better search weighting
2. **Custom search weights**: Title matches > Address matches > Content matches
3. **Location priority**: Exact city matches should rank higher

### Implementation

```php
// Custom search weighting (if not using plugin)
function custom_search_weighting($posts, $query) {
    if (!is_admin() && $query->is_search()) {
        $search_term = $query->get('s');

        // Sort by custom relevance score
        usort($posts, function($a, $b) use ($search_term) {
            $score_a = calculate_relevance_score($a, $search_term);
            $score_b = calculate_relevance_score($b, $search_term);
            return $score_b - $score_a; // Higher scores first
        });
    }
    return $posts;
}
add_filter('posts_results', 'custom_search_weighting', 10, 2);
```

---

## 🎯 **Implementation Priority**

### Week 1 (Critical)

1. Fix zip code search (ACF field indexing)
2. Clean up community type assignments
3. Remove Marigold duplicate

### Week 2 (Important)

1. Implement search weighting improvements
2. Test all fixes with your existing test suite
3. Monitor user feedback

### Week 3 (Validation)

1. Run comprehensive tests again
2. Verify all issues resolved
3. Document fixes for future reference

---

## 📋 **Testing Checklist**

After implementing fixes, verify:

- [ ] Zip code 85048 returns relevant results
- [ ] Community types show correct listings only
- [ ] Search results sorted by relevance, not alphabetically
- [ ] No duplicate Marigold listings in same zip code
- [ ] Performance remains good (<2s response times)

---

## 🔧 **WordPress Plugin Recommendations**

For long-term stability:

1. **SearchWP** - Best for ACF field indexing and custom weighting
2. **Relevanssi** - Good alternative with advanced search features
3. **FacetWP** - Excellent for advanced filtering (if needed)

These plugins would solve most search issues automatically and provide better user experience.
