# Senior Scrapr - Test Runner

This repo contains Python utilities and tests for duplicate detection, merging, and frontend search validation for A Place for Seniors.

## Prerequisites

- Python 3.9+
- Node.js (for convenient npm scripts)

Optional: create a virtualenv and install requirements.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Running Tests (via npm scripts)

- Run the full suite:

```bash
npm run test
```

- Frontend search tests (validates zip weighting/pagination ordering):

```bash
npm run test:frontend
```

- General filter tests (care type, location, price, search combos):

```bash
npm run test:filters
```

- State filter tests (uses correct `?states=` param):

```bash
npm run test:filters:states
```

- Targeted problem tests (zip weighting, community type mapping checks, relevance vs alphabetical):

```bash
npm run test:targeted
```

## Frontend Search Test Notes

- Tests hit `https://communities.aplaceforseniors.org/listings` directly (not WP REST) with params:
  - `onBehalf`, `timeline`, `budget`, `state`, `city`, `location`, `zip`
- Listing counts are parsed from the visible "X results found" header; fallback to price or "View Details" markers.
- Zip boost is validated by comparing page 1 vs page 2 ratios and checking that exemplar addresses appear for `80224` (Highpointe, Springbrooke).

## Data/CSV Notes

- Always use the latest dated WordPress export in `organized_csvs/`.
- Use ACF `website` as primary key for dedupe across sources.
- When merging, prioritize Senior Place fields while retaining Seniorly photos/content.

## Troubleshooting

- If requests time out, rerun individual scripts or increase timeouts.
- For local dev, ensure your IP isn’t blocked and the site is reachable.
