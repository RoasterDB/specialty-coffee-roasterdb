# Changelog

All notable changes to the RoasterDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `8,000+`). The dataset is refreshed
> on a recurring schedule, so the live figures only grow — the numbers below
> stay accurate between snapshots.

## Site update — 2026-09-27

- **Translated Dataset markup**: on the Spanish, German, French and Portuguese pages the Dataset structured data now names its English original in `sameAs` (next to any existing `sameAs` links), so dataset search can tie the language copies to one canonical entry. English pages and all visible text are unchanged (2026-09-27).

## Site update — 2026-09-20

- **Sale attribution**: every Stripe buy link carries `?client_reference_id=<brand>_<lang>_<surface>` (`home` / `landing`); the i18n build swaps the language token per locale and the delivery worker prints the id in the order email. Stripe does not store UTM parameters, so this is the only per-page attribution that reaches the order record (2026-09-20).

## 2026.07 — 2026-07-04

- Initial public snapshot.
- **8,000+** specialty-coffee products from **280+** artisan roasters across **20+** countries.
- **11,000+** SCA Flavor Wheel mappings across all 51 taxonomy descriptors.
- Verified tier: **3,400+** QA-passed records (origin + sanitized price + flavor).
- Per-record provenance: `source_url`, `retrieved_at`, `dataset_version`.
- Prices sanitized to a plausible retail band.

Full dataset & updates: [roasterdb.net](https://roasterdb.dataengineered.io)
