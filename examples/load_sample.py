"""Load the RoasterDB free sample and print a quick summary.

    python examples/load_sample.py

No dependencies beyond the Python standard library.
Full dataset: https://roasterdb.net
"""

import csv
import os
from collections import Counter

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "roasterdb_sample.csv")


def main() -> None:
    with open(SAMPLE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    roasters = {r["source_roaster"] for r in rows}
    print(f"{len(rows)} coffees from {len(roasters)} roasters\n")

    print("Top origins:")
    origins = Counter(r["origin_country"] for r in rows if r["origin_country"])
    for country, n in origins.most_common(5):
        print(f"  {country:16} {n}")

    print("\nProcess methods:")
    for method, n in Counter(r["process_method"] for r in rows).most_common():
        print(f"  {method:12} {n}")

    print("\nExample — flavor mapping + provenance:")
    r = next(x for x in rows if x["tasting_notes_sca_nodes"])
    print(f"  {r['source_roaster']} — {r['title']}")
    print(f"    origin : {r['origin_country'] or 'n/a'} · {r['process_method']} · ${r['price_value']}")
    print(f"    flavors: {r['tasting_notes_sca_nodes']}")
    print(f"    source : {r['source_url']}")


if __name__ == "__main__":
    main()
