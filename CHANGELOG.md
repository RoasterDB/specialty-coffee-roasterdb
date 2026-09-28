# Changelog

All notable changes to the RoasterDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `8,000+`). The dataset is refreshed
> on a recurring schedule, so the live figures only grow — the numbers below
> stay accurate between snapshots.

## Site update — 2026-09-28

- **Repository files off the website**: the translation catalogs (`/locales/`), the build scripts (`/scripts/`), `i18n.config.json`, `README.md`, `vercel.json` and the dotfiles belong to this repository, not to the website, but the site served them as plain files. They now answer the site's normal 404 page (also when requested as `/locales%2Fes.json` or `//locales/es.json`) and stay available here on GitHub. Pages, data files, samples, `llms.txt` and the sitemap are unchanged (2026-09-28).

## Site update — 2026-09-27

- **Translated Dataset markup**: on the Spanish, German, French and Portuguese pages the Dataset structured data now names its English original in `sameAs` (next to any existing `sameAs` links), so dataset search can tie the language copies to one canonical entry. English pages and all visible text are unchanged (2026-09-27).
- **Section links**: links to a homepage section (`/#pricing`, `/#support`, the header nav, and the same on the Spanish, German, French and Portuguese homepages) now stop below the sticky header instead of under it, which matters most on phones where the header wraps to several rows. A visitor arriving from another page is also put back on the section once the web fonts have loaded and shifted the layout, unless they have already scrolled. The statistics page gets the same re-alignment, and each chart's "Embed this chart" snippet now links to that chart (`/stats/#fig-<chart>`); five of the ten snippets pointed at an anchor that did not exist. Figures, charts, `data.json` and all visible text are unchanged (2026-09-27).

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
