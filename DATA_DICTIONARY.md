# RoasterDB — Data Dictionary

Field reference for the RoasterDB specialty coffee dataset.
The free sample (`samples/roasterdb_sample.csv`) uses the columns below. The full
dataset ships the same fields in CSV and JSON, plus a relational SQLite build.

## Columns

| Column | Type | Description | Coverage* |
| :--- | :--- | :--- | ---: |
| `product_id` | string | Roaster's Shopify product ID | 100% |
| `source_roaster` | string | Roaster brand name | 100% |
| `title` | string | Coffee / product name as listed | 100% |
| `origin_country` | string | Producing country, where stated or inferred | 73% |
| `origin_region` | string | Producing region, where stated | 27% |
| `altitude_min_meters` | integer | Minimum growing elevation (masl), where stated | 21% |
| `altitude_max_meters` | integer | Maximum growing elevation (masl), where stated | 21% |
| `process_method` | enum | `Washed` · `Natural` · `Honey` · `Anaerobic` · `Other` | 60%† |
| `roast_level` | enum | `Light` · `Medium` · `Dark` (+ split levels) · `Unknown` | 34%† |
| `varietals` | string | Comma-separated varietals (e.g. `Gesha, SL28`) | 40% |
| `weight_grams` | integer | Net weight of the listed unit as the listing states it; empty when it states none§ | 96%§ |
| `price_currency` | string | The store's own currency (ISO 4217: `USD`, `GBP`, `EUR`, `AUD`, `CAD`, `ZAR`, …), read from the store; empty when it could not be read | 99.9%‡ |
| `price_value` | float | Listed price in `price_currency`, sanitized to a plausible single-bag band (3–150 USD, applied in each currency at fixed reference rates); empty when outside the band or when the currency is unknown | 98%‡ |
| `tasting_notes_sca_nodes` | string | `; `-separated SCA paths, e.g. `Fruity > Berry > Blueberry` | 64% |
| `tasting_notes_confidence` | float | 0–1 confidence of the flavor normalization | — |
| `quality_flag` | enum | `good` (verified tier) or `questionable` | 100% |
| `source_platform` | string | Source channel — `shopify` | 100% |
| `source_url` | string | Exact product page the record was extracted from | 100% |
| `retrieved_at` | datetime | Crawl timestamp (when the fact was true) | 100% |
| `dataset_version` | string | Snapshot id, e.g. `2026.07` | 100% |

\* Share of the full dataset with a non-empty value, measured on 2026-11-07 across all 13,670 records of the 2026.11 edition.
† `process_method` and `roast_level` are present on 100% of rows but are `Other` and `Unknown` when not stated; only a specific value counts (60% carry a specific method, 34% a specific roast level).
‡ One store's currency could not be read, so its 4 records have no `price_currency` and no `price_value`.
§ Until 2026-10 a listing without a stated weight was recorded as 250 g, so a 250 on a record retrieved before then may be a default rather than a stated weight: 263 of the 1,999 records with 250 were last retrieved before that change (2026-10-02). From the 2026-10 crawl on, a missing weight is left empty (539 records).

## Notes

- **Coverage is honest and uneven.** Storefronts don't all publish farm-level data, so origin/altitude/process are partial. Use the `quality_flag = good` **verified tier** (6,500+ records) when you need complete rows.
- **SCA flavor mapping** normalizes free-text tasting notes to the SCA 3-tier Flavor Wheel (`Category > Subcategory > Descriptor`). Multiple nodes per coffee are joined with `; `.
- **Provenance.** `source_url` + `retrieved_at` let you trace and re-verify any record against the original listing.
- **Currencies.** Each price is in its store's own currency, read from the store's Shopify `/meta.json`; it is never inferred from the roaster's country (a Japanese roaster can sell in USD). Compare prices within one currency, or convert them yourself. Editions up to 2026.09 labelled every price `USD`, including the roughly half sold by non-US stores; the free sample was relabelled with each store's currency on 2026-10-02 (its 100 rows now carry USD, GBP, EUR, AUD, CAD, SGD, ZAR and SEK). Its weights are unchanged, so the 250 g caveat (§) applies to it.
- **Relational build (full dataset).** The SQLite export normalizes into `roasters`, `coffee_beans`, `sca_flavor_nodes`, and `bean_flavors`.

Full dataset: **[roasterdb.dataengineered.io](https://roasterdb.dataengineered.io)** · Questions: roasterdb@dataengineered.io
