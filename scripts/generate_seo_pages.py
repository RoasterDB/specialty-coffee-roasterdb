#!/usr/bin/env python3
"""
RoasterDB Static Multi-Page SEO Generator & Sitemap Builder (`RoasterDB-public`)
Reads samples/roasterdb_sample.csv and generates:
1. /roasters/<slug>.html for every unique artisan roaster.
2. /origins/<slug>.html for every unique coffee origin country.
3. /sitemap.xml indexing all pages with lastmod and priority.
"""

import csv
import html
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_common import fit_title, fit_desc, write_sitemap, related_block

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "samples" / "roasterdb_sample.csv"
ROASTERS_DIR = BASE_DIR / "roasters"
ORIGINS_DIR = BASE_DIR / "origins"
BASE_URL = "https://roasterdb.dataengineered.io"
BRAND = "RoasterDB"

ROASTERS_DIR.mkdir(parents=True, exist_ok=True)
ORIGINS_DIR.mkdir(parents=True, exist_ok=True)

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def load_coffees():
    if not CSV_PATH.exists():
        print(f"[WARN] CSV file not found at {CSV_PATH}")
        return []
    coffees = []
    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('title') and row.get('source_roaster'):
                coffees.append(row)
    return coffees

def _origin_of(c):
    return (c.get('origin_country') or '').strip().split('/')[0].strip()

def _ints(values):
    out = []
    for v in values:
        try:
            n = int(float(v))
        except (TypeError, ValueError):
            continue
        if n > 0:
            out.append(n)
    return out

def _oxford(items):
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"

def _plural(n, word):
    """'<n> <word>' or '<n> <word's plural>' -- the one place release-count grammar lives."""
    if n == 1:
        return f"{n} {word}"
    if word.endswith('y') and word[-2:-1].lower() not in 'aeiou':
        return f"{n} {word[:-1]}ies"
    return f"{n} {word}s"

def _cap(text):
    """Capitalize only the first character; unlike str.capitalize() this never
    lowercases the rest of the string (which would mangle 'Dark', 'SCA', etc.)."""
    return text[:1].upper() + text[1:] if text else text

def _families(coffees):
    fams = Counter()
    for c in coffees:
        for node in (c.get('tasting_notes_sca_nodes') or '').split(';'):
            node = node.strip()
            if node:
                fam = node.split('>')[0].strip()
                if fam:
                    fams[fam] += 1
    return fams

def _pad_related(name, ordered_names, have, target, name_idx):
    """Fill up to `target` items using name-order neighbours of `name`, nearest first."""
    if len(have) >= target:
        return []
    idx = name_idx[name]
    candidates = [n for n in ordered_names if n != name and n not in have]
    candidates.sort(key=lambda n: (abs(name_idx[n] - idx), n))
    return candidates[: target - len(have)]

def build_profile(name, coffees, kind):
    """Data-derived, per-entity prose + stat tiles.
    kind: 'roaster' (links out to origins) or 'origin' (links out to roasters)."""
    n = len(coffees)
    rel = "release" if n == 1 else "releases"
    esc = html.escape
    countries = Counter(_origin_of(c) for c in coffees if _origin_of(c))
    roasters = Counter((c.get('source_roaster') or '').strip()
                       for c in coffees if (c.get('source_roaster') or '').strip())
    alts = _ints([c.get('altitude_min_meters') for c in coffees]
                 + [c.get('altitude_max_meters') for c in coffees])
    processes = Counter(p for c in coffees
                        if (p := (c.get('process_method') or '').strip()) and p != 'Unknown')
    roasts = Counter(r for c in coffees
                     if (r := (c.get('roast_level') or '').strip()) and r != 'Unknown')
    prices = []
    for c in coffees:
        try:
            prices.append(float(c.get('price_value')))
        except (TypeError, ValueError):
            pass
    fams = _families(coffees)

    # Paragraph 1 -- who / where / elevation
    if kind == 'roaster':
        origin_phrase = ("sourced from " + _oxford([esc(c) for c, _ in countries.most_common(5)])
                         if countries else "spanning multiple origins")
        p1 = f"This RoasterDB snapshot of {esc(name)} catalogues {n} specialty coffee {rel} {origin_phrase}."
    else:
        rphrase = _oxford([esc(r) for r, _ in roasters.most_common(5)]) or "various artisan roasters"
        p1 = f"RoasterDB catalogues {n} specialty coffee {rel} grown in {esc(name)}, offered by {rphrase}."
    if alts:
        lo, hi = min(alts), max(alts)
        p1 += (f" Documented growing elevation sits at {lo} metres above sea level."
               if lo == hi else
               f" Growing elevations range from {lo} to {hi} metres above sea level.")

    # Paragraph 2 -- processing / flavor / roast / price
    bits = []
    if processes:
        bits.append("processing methods recorded include "
                    + _oxford([f"{esc(p)} ({cnt})" for p, cnt in processes.most_common(4)]))
    if fams:
        bits.append("tasting descriptors resolve most often to the "
                    + _oxford([f"{esc(f)} ({cnt})" for f, cnt in fams.most_common(4)])
                    + " families of the SCA Flavor Wheel")
    if roasts:
        bits.append("roast levels span " + _oxford([esc(r) for r, _ in roasts.most_common()]))
    p2 = ("Across these lots, " + "; ".join(bits) + ".") if bits else ""
    if prices:
        cur = esc(next((c.get('price_currency') for c in coffees if c.get('price_currency')), ""))
        lo, hi = min(prices), max(prices)
        p2 += (f" Listed retail price is {cur} {lo:.0f}."
               if lo == hi else
               f" Listed retail prices range {cur} {lo:.0f}-{hi:.0f}.")

    # Stat tiles
    tiles = [("Coffees indexed", str(n))]
    if kind == 'roaster' and countries:
        tiles.append(("Origin countries", str(len(countries))))
    if kind == 'origin' and roasters:
        tiles.append(("Roasters", str(len(roasters))))
    if alts:
        tiles.append(("Elevation range", f"{min(alts)}-{max(alts)} masl"))
    if processes:
        tiles.append(("Processing methods", str(len(processes))))
    if fams:
        tiles.append(("Top flavor family", esc(fams.most_common(1)[0][0])))
    tiles_html = "".join(
        '<li style="background:var(--bg-paper-2);border:1px solid var(--rule-color);padding:12px 14px;">'
        f'<span style="display:block;color:var(--text-muted);font-size:0.68rem;text-transform:uppercase;letter-spacing:0.06em;">{label}</span>'
        f'<strong style="font-size:1.05rem;">{value}</strong></li>'
        for label, value in tiles)

    # Full reciprocal chip list -- every sibling gets an inbound link from this page,
    # independent of (and uncapped by) the curated .related section below, so a busy
    # origin like Colombia (28 roasters) still links every one of them somewhere.
    links = ""
    if kind == 'roaster' and countries:
        chips = [f'<a href="/origins/{slugify(c)}">{esc(c)}</a>' for c in sorted(countries)]
        links = ('<p style="margin-top:16px;font-size:0.85rem;color:var(--text-muted);">'
                 '<strong style="color:var(--text-ink);">Origins in this collection:</strong> '
                 + " &middot; ".join(chips) + "</p>")
    elif kind == 'origin' and roasters:
        chips = [f'<a href="/roasters/{slugify(r)}">{esc(r)}</a>' for r in sorted(roasters)]
        links = ('<p style="margin-top:16px;font-size:0.85rem;color:var(--text-muted);">'
                 f'<strong style="color:var(--text-ink);">Roasters sourcing {esc(name)}:</strong> '
                 + " &middot; ".join(chips) + "</p>")

    heading = "Collection Profile" if kind == 'roaster' else "Origin Profile"
    p2_html = f'<p style="margin-top:10px;">{p2}</p>' if p2 else ""
    return f"""
    <section style="margin-top:36px;">
      <h2 class="font-display" style="font-size:1.5rem;">{heading} &mdash; {esc(name)}</h2>
      <p style="margin-top:12px;">{p1}</p>
      {p2_html}
      <ul style="list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:20px;padding:0;">
        {tiles_html}
      </ul>
      {links}
    </section>"""

def roaster_description(name, coffees):
    # Plain text only -- the caller HTML-escapes once at the embed point.
    n = len(coffees)
    countries = Counter(_origin_of(c) for c in coffees if _origin_of(c))
    roasts = Counter(r for c in coffees
                     if (r := (c.get('roast_level') or '').strip()) and r != 'Unknown')
    processes = Counter(p for c in coffees
                        if (p := (c.get('process_method') or '').strip()) and p != 'Unknown')
    text = f"{name} lists {_plural(n, 'specialty coffee release')} on RoasterDB"
    if countries:
        text += f" across {_plural(len(countries), 'origin country')}" if len(countries) != 1 \
            else f" from {_oxford(list(countries))}"
    text += "."
    tail_bits = []
    if roasts:
        tail_bits.append("roast levels span " + _oxford([r for r, _ in roasts.most_common()]))
    if processes:
        tail_bits.append("processing includes " + _oxford([p for p, _ in processes.most_common(3)]))
    if tail_bits:
        text += " " + _cap("; ".join(tail_bits)) + "."
    return fit_desc(text)

def origin_description(name, coffees):
    # Plain text only -- the caller HTML-escapes once at the embed point.
    n = len(coffees)
    alts = _ints([c.get('altitude_min_meters') for c in coffees]
                 + [c.get('altitude_max_meters') for c in coffees])
    processes = Counter(p for c in coffees
                        if (p := (c.get('process_method') or '').strip()) and p != 'Unknown')
    fams = _families(coffees)
    text = f"{name} appears in {_plural(n, 'specialty coffee release')} on RoasterDB"
    if alts:
        lo, hi = min(alts), max(alts)
        text += f" grown at {lo} masl" if lo == hi else f" grown between {lo}-{hi} masl"
    text += "."
    tail_bits = []
    if processes:
        tail_bits.append("processing methods seen include " + _oxford([p for p, _ in processes.most_common(3)]))
    if fams:
        tail_bits.append("top SCA descriptors are " + _oxford([f for f, _ in fams.most_common(3)]))
    if tail_bits:
        text += " " + _cap("; ".join(tail_bits)) + "."
    return fit_desc(text)

def build_roaster_related(name, coffees, ctx):
    """Reserved slots (not one combined cap), so a roaster with several origins never
    crowds out its sibling-roaster items: up to 3 origins + up to 2 sibling roasters
    (preferring roasters sharing this roaster's top origin, topped up from roasters
    sharing its top roast level when fewer than 2 origin-siblings exist) + the hub."""
    items = []
    origins_here = sorted({_origin_of(c) for c in coffees if _origin_of(c) and _origin_of(c) not in ('Unknown', 'Blend')})
    for o in origins_here[:3]:
        items.append((f"../origins/{slugify(o)}", o, "origin sourced by this roaster"))

    seen = {name}
    siblings = []
    top_origin = ctx['roaster_top_origin'].get(name)
    if top_origin:
        for r in ctx['origin_to_roasters'].get(top_origin, []):
            if r in seen:
                continue
            siblings.append((r, f"also sources {top_origin}"))
            seen.add(r)
            if len(siblings) >= 2:
                break
    if len(siblings) < 2:
        top_roast = ctx['roaster_top_roast'].get(name)
        if top_roast:
            for r in ctx['roast_level_roasters'].get(top_roast, []):
                if r in seen:
                    continue
                siblings.append((r, f"same {top_roast.lower()} roast level"))
                seen.add(r)
                if len(siblings) >= 2:
                    break
    for r, reason in siblings:
        items.append((f"../roasters/{slugify(r)}", r, reason))

    have = {label for _, label, _ in items} | {name}
    if len(items) < 3:
        for r in _pad_related(name, ctx['roaster_names'], have, 3, ctx['roaster_idx']):
            items.append((f"../roasters/{slugify(r)}", r, None))
    items.append(("../roasters/", "All specialty roasters", None))
    return items

def build_origin_related(name, coffees, ctx):
    """Reserved slots: up to 3 roasters carrying this origin + up to 2 origins with the
    closest altitude band + the hub -- kept separate so a busy origin (e.g. Colombia,
    28 roasters) still gets its altitude siblings instead of the roaster list crowding
    them out under a single combined cap. Every roaster is still linked from this page
    via the full, uncapped chip list in build_profile()."""
    items = []
    roasters_here = sorted({(c.get('source_roaster') or '').strip() for c in coffees
                            if (c.get('source_roaster') or '').strip()})
    for r in roasters_here[:3]:
        items.append((f"../roasters/{slugify(r)}", r, "roaster sourcing this origin"))

    avg = ctx['origin_alt_avg'].get(name)
    if avg is not None:
        others = sorted(
            ((o, abs(ctx['origin_alt_avg'][o] - avg)) for o in ctx['origin_names']
             if o != name and ctx['origin_alt_avg'].get(o) is not None),
            key=lambda t: (t[1], t[0]))
        for o, _ in others[:2]:
            items.append((f"../origins/{slugify(o)}", o, "similar growing elevation"))

    have = {label for _, label, _ in items} | {name}
    if len(items) < 3:
        for o in _pad_related(name, ctx['origin_names'], have, 3, ctx['origin_idx']):
            items.append((f"../origins/{slugify(o)}", o, None))
    items.append(("../origins/", "All coffee origins", None))
    return items

RELATED_CSS = """
    .related { margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--rule-color); }
    .related h2 { font-size: 1.15rem; font-family: 'Outfit', sans-serif; }
    .related ul { list-style: none; padding: 0; margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 6px 18px; }
    .related li { font-size: 0.85rem; color: var(--text-muted); }
    .related-why { font-size: 0.78rem; }
"""

def generate_roaster_page(roaster_name: str, coffees: list, ctx: dict):
    slug = slugify(roaster_name)
    file_path = ROASTERS_DIR / f"{slug}.html"
    url = f"{BASE_URL}/roasters/{slug}"

    item_list = []
    for idx, c in enumerate(coffees[:20], 1):
        item_list.append(f"""      {{
        "@type": "ListItem",
        "position": {idx},
        "name": "{html.escape(c['title'])}"
      }}""")
    item_list_json = ",\n".join(item_list)

    rows_html = []
    for c in coffees:
        origin = c.get('origin_country', 'Blend/Multi') or 'Blend/Multi'
        masl = c.get('altitude_min_meters', '') or '-'
        process = c.get('process_method', 'Unknown') or 'Unknown'
        nodes = c.get('tasting_notes_sca_nodes', '') or ''
        nodes_badge = " ".join([f"<code>{html.escape(n.strip())}</code>" for n in nodes.split(';') if n.strip()][:3])

        rows_html.append(f"""            <tr>
              <td><strong>{html.escape(c['title'])}</strong></td>
              <td>{html.escape(origin)}</td>
              <td>{html.escape(masl)}m</td>
              <td>{html.escape(process)}</td>
              <td>{nodes_badge}</td>
            </tr>""")

    table_body = "\n".join(rows_html)
    title_tag = fit_title(roaster_name, ["SCA flavor profile", "coffee roaster"], BRAND)
    desc = roaster_description(roaster_name, coffees)
    related_html = related_block(build_roaster_related(roaster_name, coffees, ctx), heading="Related roasters and origins", limit=None)

    page_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title_tag)}</title>
  <meta name="description" content="{html.escape(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="icon" href="/favicon.ico" type="image/x-icon" />
  <link rel="alternate" hreflang="en" href="{url}" />

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'" />
  <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" /></noscript>

  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{BASE_URL}/" }},
      {{ "@type": "ListItem", "position": 2, "name": "Roasters", "item": "{BASE_URL}/#explorer" }},
      {{ "@type": "ListItem", "position": 3, "name": "{html.escape(roaster_name)}", "item": "{url}" }}
    ]
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "ItemList",
    "name": "{html.escape(roaster_name)} Specialty Coffees",
    "numberOfItems": {len(coffees)},
    "itemListElement": [
{item_list_json}
    ]
  }}
  </script>

  <style>
    :root {{
      --bg-paper: #181715;
      --bg-paper-2: #21201d;
      --text-ink: #f8f7f4;
      --text-muted: #9c9891;
      --rule-color: rgba(248, 247, 244, 0.18);
      --accent: #d94e34;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg-paper); color: var(--text-ink); font-family: 'JetBrains Mono', monospace; line-height: 1.6; padding: 40px 20px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .font-display {{ font-family: 'Outfit', sans-serif; }}
    .header-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--rule-color); padding-bottom: 20px; margin-bottom: 40px; }}
    h1 {{ font-size: 2.2rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 24px; font-size: 0.85rem; }}
    th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid var(--rule-color); }}
    th {{ background: var(--bg-paper-2); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.08em; }}
    code {{ background: rgba(217, 78, 52, 0.18); color: #ff7a63; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; display: inline-block; margin: 2px 0; }}
{RELATED_CSS}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <div>
        <a href="/" style="font-weight: 700; letter-spacing: -0.02em; color: var(--text-ink);">ROASTERDB.NET</a>
        <span style="opacity: 0.6; font-size: 0.75rem; margin-left: 12px;">| Roaster Catalog Snapshot</span>
      </div>
      <a href="/" style="font-size: 0.85rem;">← Back to Main Explorer</a>
    </div>

    <h1 class="font-display">{html.escape(roaster_name)} — Specialty Coffee Releases</h1>
    <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.9rem;">
      Indexed <strong>{len(coffees)} specialty coffee releases</strong> from {html.escape(roaster_name)} with tasting descriptors normalized to the SCA Flavor Wheel.
    </p>
{build_profile(roaster_name, coffees, 'roaster')}
    <div style="overflow-x: auto; margin-top: 24px;">
      <table>
        <thead>
          <tr>
            <th>Coffee Title</th>
            <th>Origin Country</th>
            <th>Elevation</th>
            <th>Process Method</th>
            <th>SCA Flavor Wheel Nodes</th>
          </tr>
        </thead>
        <tbody>
{table_body}
        </tbody>
      </table>
    </div>

    {related_html}

    <div style="margin-top: 60px; padding: 32px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); text-align: center;">
      <h3 class="font-display" style="font-size: 1.4rem;">Need Full SQL / CSV Access to All 8,000+ Releases?</h3>
      <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.85rem;">Download our normalized relational SQLite snapshot covering 280+ roasters worldwide.</p>
      <a href="/#pricing" style="display: inline-block; background: var(--accent); color: #ffffff; font-weight: bold; padding: 14px 28px; border-radius: 4px; margin-top: 16px; text-decoration: none;">Get Full Snapshot Dataset ($49) →</a>
    </div>
  </div>
</body>
</html>"""
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page_content)
    return url, file_path

def generate_origin_page(origin_name: str, coffees: list, ctx: dict):
    slug = slugify(origin_name)
    file_path = ORIGINS_DIR / f"{slug}.html"
    url = f"{BASE_URL}/origins/{slug}"

    rows_html = []
    for c in coffees:
        roaster = c.get('source_roaster', '') or '-'
        masl = c.get('altitude_min_meters', '') or '-'
        process = c.get('process_method', 'Unknown') or 'Unknown'
        nodes = c.get('tasting_notes_sca_nodes', '') or ''
        nodes_badge = " ".join([f"<code>{html.escape(n.strip())}</code>" for n in nodes.split(';') if n.strip()][:3])

        rows_html.append(f"""            <tr>
              <td><strong>{html.escape(c['title'])}</strong></td>
              <td>{html.escape(roaster)}</td>
              <td>{html.escape(masl)}m</td>
              <td>{html.escape(process)}</td>
              <td>{nodes_badge}</td>
            </tr>""")
    table_body = "\n".join(rows_html)
    n_releases = len(coffees)
    title_tag = fit_title(origin_name, [f"{_plural(n_releases, 'specialty release')}", "coffee origin"], BRAND)
    desc = origin_description(origin_name, coffees)
    related_html = related_block(build_origin_related(origin_name, coffees, ctx), heading="Related origins and roasters", limit=None)

    page_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title_tag)}</title>
  <meta name="description" content="{html.escape(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="icon" href="/favicon.ico" type="image/x-icon" />
  <link rel="alternate" hreflang="en" href="{url}" />

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'" />
  <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" /></noscript>

  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{BASE_URL}/" }},
      {{ "@type": "ListItem", "position": 2, "name": "Origins", "item": "{BASE_URL}/#explorer" }},
      {{ "@type": "ListItem", "position": 3, "name": "{html.escape(origin_name)}", "item": "{url}" }}
    ]
  }}
  </script>

  <style>
    :root {{
      --bg-paper: #181715;
      --bg-paper-2: #21201d;
      --text-ink: #f8f7f4;
      --text-muted: #9c9891;
      --rule-color: rgba(248, 247, 244, 0.18);
      --accent: #d94e34;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg-paper); color: var(--text-ink); font-family: 'JetBrains Mono', monospace; line-height: 1.6; padding: 40px 20px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .font-display {{ font-family: 'Outfit', sans-serif; }}
    .header-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--rule-color); padding-bottom: 20px; margin-bottom: 40px; }}
    h1 {{ font-size: 2.2rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 24px; font-size: 0.85rem; }}
    th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid var(--rule-color); }}
    th {{ background: var(--bg-paper-2); text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.08em; }}
    code {{ background: rgba(217, 78, 52, 0.18); color: #ff7a63; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; display: inline-block; margin: 2px 0; }}
{RELATED_CSS}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <div>
        <a href="/" style="font-weight: 700; letter-spacing: -0.02em; color: var(--text-ink);">ROASTERDB.NET</a>
        <span style="opacity: 0.6; font-size: 0.75rem; margin-left: 12px;">| Origin Catalog Snapshot</span>
      </div>
      <a href="/" style="font-size: 0.85rem;">← Back to Main Explorer</a>
    </div>

    <h1 class="font-display">{html.escape(origin_name)} — Specialty Coffee Releases</h1>
    <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.9rem;">
      Indexed <strong>{len(coffees)} specialty coffee releases</strong> from {html.escape(origin_name)} with elevation (masl) and SCA Flavor Wheel descriptors.
    </p>
{build_profile(origin_name, coffees, 'origin')}
    <div style="overflow-x: auto; margin-top: 24px;">
      <table>
        <thead>
          <tr>
            <th>Coffee Title</th>
            <th>Artisan Roaster</th>
            <th>Elevation</th>
            <th>Process Method</th>
            <th>SCA Flavor Wheel Nodes</th>
          </tr>
        </thead>
        <tbody>
{table_body}
        </tbody>
      </table>
    </div>

    {related_html}

    <div style="margin-top: 60px; padding: 32px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); text-align: center;">
      <h3 class="font-display" style="font-size: 1.4rem;">Need Full SQL / CSV Access to All 8,000+ Releases?</h3>
      <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.85rem;">Download our normalized relational SQLite snapshot covering 280+ roasters worldwide.</p>
      <a href="/#pricing" style="display: inline-block; background: var(--accent); color: #ffffff; font-weight: bold; padding: 14px 28px; border-radius: 4px; margin-top: 16px; text-decoration: none;">Get Full Snapshot Dataset ($49) →</a>
    </div>
  </div>
</body>
</html>"""
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page_content)
    return url, file_path

def main():
    print("Starting RoasterDB-public Multi-Page SEO Generator...")
    coffees = load_coffees()
    print(f"Loaded {len(coffees)} coffee records from sample dataset.")

    roasters_map = {}
    origins_map = {}

    for c in coffees:
        roaster = (c.get('source_roaster') or '').strip()
        origin = _origin_of(c)

        if roaster:
            roasters_map.setdefault(roaster, []).append(c)
        if origin and origin not in ('Unknown', 'Blend'):
            origins_map.setdefault(origin, []).append(c)

    # Cross-reference context for related-block construction.
    roaster_names = sorted(roasters_map)
    origin_names = sorted(origins_map)
    roaster_idx = {n: i for i, n in enumerate(roaster_names)}
    origin_idx = {n: i for i, n in enumerate(origin_names)}

    origin_to_roasters = {
        o: sorted({(c.get('source_roaster') or '').strip() for c in cs if (c.get('source_roaster') or '').strip()})
        for o, cs in origins_map.items()
    }

    roaster_top_origin = {}
    for r, cs in roasters_map.items():
        cnt = Counter(_origin_of(c) for c in cs if _origin_of(c) and _origin_of(c) not in ('Unknown', 'Blend'))
        roaster_top_origin[r] = cnt.most_common(1)[0][0] if cnt else None

    roast_level_roasters = {}
    roaster_top_roast = {}
    for r, cs in roasters_map.items():
        cnt = Counter(rl for c in cs if (rl := (c.get('roast_level') or '').strip()) and rl != 'Unknown')
        roaster_top_roast[r] = cnt.most_common(1)[0][0] if cnt else None
        for lvl in cnt:
            roast_level_roasters.setdefault(lvl, set()).add(r)
    roast_level_roasters = {k: sorted(v) for k, v in roast_level_roasters.items()}

    origin_alt_avg = {}
    for o, cs in origins_map.items():
        alts = _ints([c.get('altitude_min_meters') for c in cs] + [c.get('altitude_max_meters') for c in cs])
        origin_alt_avg[o] = (sum(alts) / len(alts)) if alts else None

    ctx = {
        'roaster_names': roaster_names,
        'origin_names': origin_names,
        'roaster_idx': roaster_idx,
        'origin_idx': origin_idx,
        'origin_to_roasters': origin_to_roasters,
        'roaster_top_origin': roaster_top_origin,
        'roast_level_roasters': roast_level_roasters,
        'roaster_top_roast': roaster_top_roast,
        'origin_alt_avg': origin_alt_avg,
    }

    sitemap_entries = [(f"{BASE_URL}/", BASE_DIR / "index.html", "weekly", "1.0")]

    print(f"Generating {len(roasters_map)} Roaster SEO Landing Pages...")
    for r_name, r_coffees in roasters_map.items():
        url, fp = generate_roaster_page(r_name, r_coffees, ctx)
        sitemap_entries.append((url, fp, "monthly", "0.8"))

    print(f"Generating {len(origins_map)} Origin Country SEO Landing Pages...")
    for o_name, o_coffees in origins_map.items():
        url, fp = generate_origin_page(o_name, o_coffees, ctx)
        sitemap_entries.append((url, fp, "monthly", "0.8"))

    for slug, label in (("roasters", "Roaster directory"), ("origins", "Origin directory")):
        idx_path = BASE_DIR / slug / "index.html"
        if idx_path.exists():
            sitemap_entries.append((f"{BASE_URL}/{slug}/", idx_path, "monthly", "0.7"))

    n_urls = write_sitemap(BASE_DIR, sitemap_entries)
    print(f"Generated {n_urls} URLs in sitemap.xml")
    print("RoasterDB-public Multi-Page SEO generation completed successfully!")

if __name__ == "__main__":
    main()
