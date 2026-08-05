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
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "samples" / "roasterdb_sample.csv"
ROASTERS_DIR = BASE_DIR / "roasters"
ORIGINS_DIR = BASE_DIR / "origins"
SITEMAP_PATH = BASE_DIR / "sitemap.xml"

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

def build_profile(name, coffees, kind):
    """Data-derived, per-entity prose + stat tiles + internal sibling links.
    kind: 'roaster' (links out to origins) or 'origin' (links out to roasters)."""
    n = len(coffees)
    rel = "release" if n == 1 else "releases"
    esc = html.escape
    countries = Counter((c.get('origin_country') or '').split('/')[0].strip()
                        for c in coffees if (c.get('origin_country') or '').strip())
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

    # Paragraph 1 — who / where / elevation
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

    # Paragraph 2 — processing / flavor / roast / price
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
               f" Listed retail prices range {cur} {lo:.0f}–{hi:.0f}.")

    # Stat tiles
    tiles = [("Coffees indexed", str(n))]
    if kind == 'roaster' and countries:
        tiles.append(("Origin countries", str(len(countries))))
    if kind == 'origin' and roasters:
        tiles.append(("Roasters", str(len(roasters))))
    if alts:
        tiles.append(("Elevation range", f"{min(alts)}–{max(alts)} masl"))
    if processes:
        tiles.append(("Processing methods", str(len(processes))))
    if fams:
        tiles.append(("Top flavor family", esc(fams.most_common(1)[0][0])))
    tiles_html = "".join(
        '<li style="background:var(--bg-paper-2);border:1px solid var(--rule-color);padding:12px 14px;">'
        f'<span style="display:block;color:var(--text-muted);font-size:0.68rem;text-transform:uppercase;letter-spacing:0.06em;">{label}</span>'
        f'<strong style="font-size:1.05rem;">{value}</strong></li>'
        for label, value in tiles)

    # Internal links to sibling pages (roaster <-> origin)
    links = ""
    if kind == 'roaster' and countries:
        chips = [f'<a href="/origins/{slugify(c)}">{esc(c)}</a>' for c in list(countries)[:12]]
        links = ('<p style="margin-top:16px;font-size:0.85rem;color:var(--text-muted);">'
                 '<strong style="color:var(--text-ink);">Origins in this collection:</strong> '
                 + " &middot; ".join(chips) + "</p>")
    elif kind == 'origin' and roasters:
        chips = [f'<a href="/roasters/{slugify(r)}">{esc(r)}</a>' for r in list(roasters)[:12]]
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

def generate_roaster_page(roaster_name: str, coffees: list):
    slug = slugify(roaster_name)
    file_path = ROASTERS_DIR / f"{slug}.html"
    url = f"https://specialty-coffee-roasterdb.pages.dev/roasters/{slug}"
    
    # Build ItemList schema
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
    
    page_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(roaster_name)} — Specialty Coffee Beans & SCA Flavor Profile | RoasterDB</title>
  <meta name="description" content="Explore {len(coffees)} specialty coffee releases from {html.escape(roaster_name)} mapped directly to the SCA Flavor Wheel taxonomy with altitude, origin, and process method data." />
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
      {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://specialty-coffee-roasterdb.pages.dev/" }},
      {{ "@type": "ListItem", "position": 2, "name": "Roasters", "item": "https://specialty-coffee-roasterdb.pages.dev/#explorer" }},
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

    <div style="margin-top: 60px; padding: 32px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); text-align: center;">
      <h3 class="font-display" style="font-size: 1.4rem;">Need Full SQL / CSV Access to All 8,000+ Releases?</h3>
      <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.85rem;">Download our normalized relational SQLite snapshot covering 280+ roasters worldwide.</p>
      <a href="/#pricing" style="display: inline-block; background: var(--accent); color: #ffffff; font-weight: bold; padding: 14px 28px; border-radius: 4px; margin-top: 16px; text-decoration: none;">Get Full Snapshot Dataset ($49) →</a>
    </div>
  </div>
</body>
</html>"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(page_content)
    return url

def generate_origin_page(origin_name: str, coffees: list):
    slug = slugify(origin_name)
    file_path = ORIGINS_DIR / f"{slug}.html"
    url = f"https://specialty-coffee-roasterdb.pages.dev/origins/{slug}"
    
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
    
    page_content = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(origin_name)} Specialty Coffee Beans — SCA Tasting Notes & Elevation | RoasterDB</title>
  <meta name="description" content="Explore {len(coffees)} specialty coffee releases from {html.escape(origin_name)} across top artisan roasters, mapped to SCA flavor notes, altitude masl, and processing methods." />
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
      {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://specialty-coffee-roasterdb.pages.dev/" }},
      {{ "@type": "ListItem", "position": 2, "name": "Origins", "item": "https://specialty-coffee-roasterdb.pages.dev/#explorer" }},
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

    <div style="margin-top: 60px; padding: 32px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); text-align: center;">
      <h3 class="font-display" style="font-size: 1.4rem;">Need Full SQL / CSV Access to All 8,000+ Releases?</h3>
      <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.85rem;">Download our normalized relational SQLite snapshot covering 280+ roasters worldwide.</p>
      <a href="/#pricing" style="display: inline-block; background: var(--accent); color: #ffffff; font-weight: bold; padding: 14px 28px; border-radius: 4px; margin-top: 16px; text-decoration: none;">Get Full Snapshot Dataset ($49) →</a>
    </div>
  </div>
</body>
</html>"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(page_content)
    return url

def main():
    print("Starting RoasterDB-public Multi-Page SEO Generator...")
    coffees = load_coffees()
    print(f"Loaded {len(coffees)} coffee records from sample dataset.")
    
    roasters_map = {}
    origins_map = {}
    
    for c in coffees:
        roaster = (c.get('source_roaster') or '').strip()
        origin = (c.get('origin_country') or '').strip().split('/')[0].strip()
        
        if roaster:
            roasters_map.setdefault(roaster, []).append(c)
        if origin and origin not in ['Unknown', 'Blend']:
            origins_map.setdefault(origin, []).append(c)
            
    sitemap_urls = ["https://specialty-coffee-roasterdb.pages.dev/"]
    
    print(f"Generating {len(roasters_map)} Roaster SEO Landing Pages...")
    for r_name, r_coffees in roasters_map.items():
        url = generate_roaster_page(r_name, r_coffees)
        sitemap_urls.append(url)
        
    print(f"Generating {len(origins_map)} Origin Country SEO Landing Pages...")
    for o_name, o_coffees in origins_map.items():
        url = generate_origin_page(o_name, o_coffees)
        sitemap_urls.append(url)
        
    # Build Sitemap XML
    now_str = datetime.now().strftime('%Y-%m-%d')
    url_tags = []
    for u in sitemap_urls:
        priority = "1.0" if u == "https://specialty-coffee-roasterdb.pages.dev/" else "0.8"
        url_tags.append(f"""  <url>
    <loc>{u}</loc>
    <lastmod>{now_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>{priority}</priority>
  </url>""")
        
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"\n".join(url_tags)}
</urlset>
"""
    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)
    print(f"Generated {len(sitemap_urls)} URLs in {SITEMAP_PATH}")
    print("RoasterDB-public Multi-Page SEO generation completed successfully!")

if __name__ == "__main__":
    main()
