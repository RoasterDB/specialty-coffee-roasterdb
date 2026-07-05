# RoasterDB — Data Dictionary

Field reference for the RoasterDB specialty coffee dataset (snapshot `2026.07`).
The free sample (`samples/roasterdb_sample.csv`) uses the columns below. The full
dataset ships the same fields in CSV and JSON, plus a relational SQLite build.

## Columns

| Column | Type | Description | Coverage* |
| :--- | :--- | :--- | ---: |
| `product_id` | string | Roaster's Shopify product ID | 100% |
| `source_roaster` | string | Roaster brand name | 100% |
| `title` | string | Coffee / product name as listed | 100% |
| `origin_country` | string | Producing country, where stated or inferred | 58% |
| `origin_region` | string | Producing region, where stated | 20% |
| `altitude_min_meters` | integer | Minimum growing elevation (masl), where stated | 17% |
| `altitude_max_meters` | integer | Maximum growing elevation (masl), where stated | 17% |
| `process_method` | enum | `Washed` · `Natural` · `Honey` · `Anaerobic` · `Other` | 45%† |
| `roast_level` | enum | `Light` · `Medium` · `Dark` (+ split levels), where stated | 32% |
| `varietals` | string | Comma-separated varietals (e.g. `Gesha, SL28`) | 30% |
| `weight_grams` | integer | Net weight of the listed unit | 100% |
| `price_currency` | string | Currency code (typically `USD`) | 100% |
| `price_value` | float | Retail price, sanitized to a plausible band ($3–$150) | 88% |
| `tasting_notes_sca_nodes` | string | `; `-separated SCA paths, e.g. `Fruity > Berry > Blueberry` | 55% |
| `tasting_notes_confidence` | float | 0–1 confidence of the flavor normalization | — |
| `quality_flag` | enum | `good` (verified tier) or `questionable` | 100% |
| `source_platform` | string | Source channel — `shopify` | 100% |
| `source_url` | string | Exact product page the record was extracted from | 100% |
| `retrieved_at` | datetime | Crawl timestamp (when the fact was true) | 100% |
| `dataset_version` | string | Snapshot id, e.g. `2026.07` | 100% |

\* Share of the full 8,086-record dataset with a non-empty value.
† `process_method` is present on 100% of rows but is `Other` when not stated; 45% carry a specific method.

## Notes

- **Coverage is honest and uneven.** Storefronts don't all publish farm-level data, so origin/altitude/process are partial. Use the `quality_flag = good` **verified tier** (3,422 records) when you need complete rows.
- **SCA flavor mapping** normalizes free-text tasting notes to the SCA 3-tier Flavor Wheel (`Category > Subcategory > Descriptor`). Multiple nodes per coffee are joined with `; `.
- **Provenance.** `source_url` + `retrieved_at` let you trace and re-verify any record against the original listing.
- **Relational build (full dataset).** The SQLite export normalizes into `roasters`, `coffee_beans`, `sca_flavor_nodes`, and `bean_flavors`.

Full dataset: **[roasterdb.net](https://specialty-coffee-roasterdb.pages.dev)** · Questions: **[RoasterDB@proton.me](mailto:RoasterDB@proton.me)**
