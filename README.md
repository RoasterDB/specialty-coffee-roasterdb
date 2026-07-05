<div align="center">

# ☕ RoasterDB — Specialty Coffee Dataset

**8,086 specialty-coffee products · 278 artisan roasters · 22 countries · mapped to the SCA Flavor Wheel**

[![Sample: 100 rows](https://img.shields.io/badge/Free%20Sample-100%20rows-brightgreen.svg)](samples/roasterdb_sample.csv)
[![Roasters: 278](https://img.shields.io/badge/Roasters-278-8a5a44.svg)](#whats-inside)
[![Snapshot: 2026.07](https://img.shields.io/badge/Snapshot-2026.07-blue.svg)](CHANGELOG.md)
[![Get the data](https://img.shields.io/badge/Get%20the%20data-roasterdb.net-ff6b4a.svg)](https://roasterdb.net)

**[→ Get the full dataset at roasterdb.net](https://roasterdb.net)**

</div>

---

A structured dataset of specialty-coffee products scraped from the **direct storefronts** of curated artisan roasters worldwide, with tasting notes normalized to the **Specialty Coffee Association (SCA) Flavor Wheel** and a **source URL on every record** so any fact can be re-verified.

This is a **storefront catalog + flavor-mapping** dataset — strong on roaster breadth, product identity, pricing, and SCA flavor structure. It is **not** a farm-provenance dataset; the honest [field-coverage table](#field-coverage) below shows exactly what is and isn't populated. No hype — just what's in the box.

## What's inside

| | Full dataset | Free sample |
| :--- | ---: | ---: |
| Coffee products | **8,086** | 100 |
| Artisan roasters | **278** | 72 |
| Countries (roaster HQ) | **22** | — |
| SCA flavor mappings | **11,838** | ~250 |
| Formats | SQLite · CSV · JSON | CSV |

The free [`samples/roasterdb_sample.csv`](samples/roasterdb_sample.csv) is 100 verified-tier records across 72 roasters — a real taste of the schema and quality. The full dataset is available at **[roasterdb.net](https://roasterdb.net)**.

## Field coverage (the honest numbers)

Measured across all 8,086 records. Published up front so you can decide if the fields you need are covered — not every coffee lists every attribute on its storefront.

| Field | Coverage | | Field | Coverage |
| :--- | ---: | --- | :--- | ---: |
| Title / product ID | 100% | | Process method | 45% |
| Weight | 100% | | Roast level | 32% |
| Price (USD, sanitized) | 88% | | Varietals | 30% |
| ≥1 SCA flavor node | 55% | | Origin region | 20% |
| Origin country | 58% | | Altitude (masl) | 17% |

**Two quality tiers** (both in the full dataset):
- **Full catalog** — all **8,086** records (maximum breadth).
- **Verified tier** — **3,422** records flagged `good`: origin + sanitized price + SCA flavor mapping, QA-passed.

### SCA flavor mapping — the differentiated part
- **4,510 coffees** mapped to the SCA wheel · **11,838** bean→flavor links · avg **2.6** descriptors each.
- All **51** taxonomy descriptors exercised; tasting notes become hierarchical paths, e.g. `Fruity > Other Fruit > Peach`.

## Provenance

Every record is traceable and re-verifiable:

| Field | Meaning |
| :--- | :--- |
| `source_roaster` | Roaster brand |
| `source_url` | Exact product page the data came from |
| `source_platform` | `shopify` |
| `retrieved_at` | Crawl timestamp |
| `dataset_version` | Snapshot id (`2026.07`) |

See [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) for every field.

## Pricing

| Tier | What | Price |
| :--- | :--- | :--- |
| **Sample** | 100 verified rows (this repo) | Free |
| **Snapshot** | Full 8,086 records · SQLite + CSV + JSON | **$99** one-time |
| **Custom & Fresh** | Your target roasters · recurring refreshes · API | **$1,000+** |

**[→ Get it at roasterdb.net](https://roasterdb.net)** · or email **[RoasterDB@proton.me](mailto:RoasterDB@proton.me)** for custom work.

## Use cases

- Coffee subscription & recommendation apps (structured product + flavor data)
- Flavor-based search and discovery on the SCA graph
- ML / RAG corpora over specialty coffee
- Market & assortment research across roasters, origins, and price bands

## Quick look

```python
import csv
rows = list(csv.DictReader(open("samples/roasterdb_sample.csv", encoding="utf-8")))
print(len(rows), "coffees from", len({r["source_roaster"] for r in rows}), "roasters")
# → 100 coffees from 72 roasters
```

A fuller example is in [`examples/load_sample.py`](examples/load_sample.py).

## License

- **Sample data & docs in this repo:** MIT (see [`LICENSE`](LICENSE)).
- **Full dataset:** commercial license, available at [roasterdb.net](https://roasterdb.net). Distributed as derived factual attributes with source attribution.

Are you a roaster and want a record corrected or removed? Email **[RoasterDB@proton.me](mailto:RoasterDB@proton.me)**.
