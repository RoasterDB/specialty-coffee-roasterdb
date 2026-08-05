# Contributing to RoasterDB

Thanks for your interest! This repository is the **public showcase** for the
RoasterDB specialty-coffee dataset — it holds a free sample, documentation, and
a starter notebook. The data pipeline itself is not open source, so
contributions here focus on **data quality, docs, and examples**.

## Ways to help

### 🐛 Report a data issue
Spotted a wrong origin, price, or flavor mapping in the sample? Open an issue
with:
- the `product_id` and `source_roaster`,
- what's wrong and what it should be,
- ideally the `source_url` so we can re-verify against the live listing.

### ✏️ Improve docs or examples
Typos, clearer explanations, or a better `examples/load_sample.py` /
notebook are welcome via pull request.

### 💡 Request a field or feature
Want a column the dataset doesn't have yet, or a specific set of roasters?
Open an issue describing the use case — it helps prioritize snapshots and
informs custom builds.

## Roasters: correction or removal requests

If you're a roaster and want a record corrected or removed, please email
**RoasterDB@proton.me** (or open an issue). We honor removal requests for the
public sample promptly.

## Pull request guidelines

- Keep PRs focused and describe the *why*.
- Docs/examples only — please don't add scraping/pipeline code here.
- Data changes to the sample should preserve the schema in
  [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

## Licensing of contributions

By contributing, you agree that your contributions to the sample and docs are
licensed under **CC-BY-NC-4.0**, the same license as this repository (see
[`LICENSE`](LICENSE)).

Questions? **RoasterDB@proton.me** · full dataset: [roasterdb.net](https://specialty-coffee-roasterdb.pages.dev)
