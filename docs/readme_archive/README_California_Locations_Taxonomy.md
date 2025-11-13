# California Locations Taxonomy Import

This system converts California city descriptions into WordPress taxonomy terms that can be imported via WP All Import.

## Generated Files

✅ **Successfully Created:**

- `CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT_FLAT.csv` - Flat taxonomy (all cities under "locations")
- `CALIFORNIA_LOCATIONS_TAXONOMY_IMPORT.csv` - Hierarchical taxonomy (cities under state parents)

## File Formats

### Flat Taxonomy Format

```
taxonomy,parent,name,slug,description
locations,,Acton,acton,"Acton offers seniors affordable living..."
locations,,Adelanto,adelanto,"Adelanto provides seniors with..."
```

### Hierarchical Taxonomy Format

```
taxonomy,parent,name,slug,description
locations-ca,ca,"Acton, CA",acton,"Acton offers seniors affordable living..."
locations-ca,ca,"Adelanto, CA",adelanto,"Adelanto provides seniors with..."
```

## WordPress Import Instructions

1. **Go to WP All Import** → New Import
2. **Upload the CSV file** (choose flat or hierarchical version)
3. **Set Post Type** to "Taxonomies"
4. **Map the columns:**
   - `taxonomy` → Taxonomy
   - `parent` → Parent (blank for flat, state slug for hierarchical)
   - `name` → Term Name
   - `slug` → Term Slug
   - `description` → Term Description
5. **Run the import**

## Script Usage

### Basic Usage

```bash
python3 prepare_california_locations_taxonomy.py
```

### Hierarchical Version (Recommended)

```bash
python3 prepare_california_locations_taxonomy.py --hierarchical
```

### Custom Input/Output

```bash
python3 prepare_california_locations_taxonomy.py \
  --input california_city_descriptions_improved.csv \
  --output custom_locations_import.csv \
  --hierarchical
```

## Features

✅ **313 California cities** processed
✅ **Clean URL slugs** (spaces → hyphens, removes special chars)
✅ **Rich descriptions** for each city tailored for seniors
✅ **Two taxonomy structures** (flat and hierarchical)
✅ **WP All Import compatible** format

## Input Files Supported

- `california_city_descriptions_final.csv` (default)
- `california_city_descriptions_improved.csv`
- Any CSV with `City`, `State`, `Description` columns

## Benefits

1. **SEO Enhancement** - Rich descriptions for city landing pages
2. **User Experience** - Detailed information about each California city
3. **Content Marketing** - Pre-written content for city-specific pages
4. **Consistency** - Standardized format across all locations

## Integration with Existing System

The location taxonomy terms will automatically be available for:

- City-based filtering in your senior living directory
- SEO-friendly URLs like `/locations/los-angeles/`
- Rich snippets and meta descriptions for city pages

## Next Steps

1. Import the taxonomy terms via WP All Import
2. Create city landing page templates
3. Map existing listings to use the new location terms
4. Update navigation to include city links

## Troubleshooting

- **Import fails**: Check CSV encoding (UTF-8)
- **Terms not appearing**: Verify taxonomy name matches WordPress setup
- **Parent-child not working**: Ensure parent terms are imported first
- **Descriptions not showing**: Check ACF field mapping in WordPress
