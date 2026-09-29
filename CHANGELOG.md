# Changelog

All notable changes to the RoasterDB dataset snapshots.

> Counts are stated as **minimums** (e.g. `8,000+`). The dataset is refreshed
> on a recurring schedule, so the live figures only grow — the numbers below
> stay accurate between snapshots.

## Site update — 2026-09-29

- **Kaggle metadata file**: `kaggle/dataset/dataset-metadata.json` now carries the live Kaggle description (with the `/stats/` link), keyword order, sources list and update frequency, so a push from this file no longer rolls the Kaggle page back (2026-09-29).
- **Site name**: the header of the 72 roaster pages and 16 origin pages (English, Spanish, German, French and Portuguese; 440 pages) read `ROASTERDB.NET`; it now reads `ROASTERDB`, as on the homepage (`scripts/generate_seo_pages.py`). The licence attribution, the Kaggle dataset description and starter notebook, and `assets/README.md` now name `roasterdb.dataengineered.io` instead of `roasterdb.net`. The sitemap dates those 440 pages 2026-09-29, and the ten directory hubs and `/stats/` get their real last-change date (2026-09-28) instead of 2026-09-15/17 (2026-09-29).
- **Security policy link**: `SECURITY.md` showed the site link as `roasterdb.net`; it now shows `roasterdb.dataengineered.io`, the address the link already pointed to (2026-09-29).
- **Visit counts**: Cloudflare Web Analytics adds its cookie-free page-view beacon to every page, but the Content-Security-Policy in `_headers` let browsers run scripts from this site only, so they refused the beacon and no visits were counted since Web Analytics was switched on (2026-09-05). The policy now also allows the beacon script (`https://static.cloudflareinsights.com`, `script-src`) and the address it reports to (`https://cloudflareinsights.com`, `connect-src`). No other source is added.

## Site update — 2026-09-28

- **Directory pages render sooner**: the coffee origin and roaster directories (`/origins/`, `/roasters/` and their Spanish, German, French and Portuguese copies) loaded the Google Fonts stylesheet twice: once without blocking, and once as a render-blocking copy of the no-JavaScript fallback, which had lost its `<noscript>` wrapper. The fallback is wrapped again, so these pages no longer wait for the font file before they render. Nothing visible changes (2026-09-28).
- **Edition label**: the homepage (pricing card, license note, Dataset and breadcrumb structured data) and the README badge said "Snapshot 2026.07"; buyers have downloaded edition 2026.09 since 2026-09-04. All now say 2026.09, on the Spanish, German, French and Portuguese homepages too; homepage sitemap `lastmod` set to 2026-09-28. The free sample (`samples/roasterdb_sample.csv`) and the field-coverage figures are still the 2026.07 measurement; every figure is at or below the 2026.09 value, so the stated minimums hold.
- **Repository files off the website**: the translation catalogs (`/locales/`), the build scripts (`/scripts/`), `i18n.config.json`, `README.md`, `vercel.json` and the dotfiles belong to this repository, not to the website, but the site served them as plain files. They now answer the site's normal 404 page (also when requested as `/locales%2Fes.json` or `//locales/es.json`) and stay available here on GitHub. Pages, data files, samples, `llms.txt` and the sitemap are unchanged (2026-09-28).
- **Chart titles on `/stats/`**: every chart's built-in title and description (what a screen reader announces for the chart) used the same two ids, `t` and `d`, repeated once per chart, so the page had duplicate ids and every chart was announced with the first chart's title. The ids now carry the chart's name (`t-origins` / `d-origins`, and so on) on the page and in the downloadable SVGs under `/stats/charts/`. `scripts/generate_stats.py` writes them on the next regeneration; the committed page and SVGs were patched to exactly what it writes, without regenerating (no figure, date or `data.json` changes).

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

Full dataset & updates: [roasterdb.dataengineered.io](https://roasterdb.dataengineered.io)
