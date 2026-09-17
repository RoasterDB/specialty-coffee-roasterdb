#!/usr/bin/env python3
"""
RoasterDB statistics page generator (`RoasterDB-public`).

Reads the FULL working snapshot (the private pipeline's SQLite, never the public
sample) and writes a citable, embeddable statistics page:

    stats/index.html          the page (URL /stats/)
    stats/charts/<slug>.svg   one standalone SVG per chart (for <img> embeds elsewhere)
    stats/data.json           every figure on the page, machine-readable

Only aggregates leave the private database -- no row-level data is written.
Every figure states its denominator and filter so a reader can reproduce it.

Re-run after each data refresh, then `python scripts/generate_seo_pages.py`
(sitemap), `python scripts/i18n_common.py build` and `... check`.

Usage:
    python scripts/generate_stats.py                 # ../../02_Specialty_Coffee_RoasterDB/data/roasterdb.sqlite
    python scripts/generate_stats.py --db PATH       # or ROASTERDB_SQLITE=PATH
"""
import argparse
import datetime as dt
import html
import json
import os
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "stats"
CHART_DIR = OUT_DIR / "charts"
BASE_URL = "https://roasterdb.dataengineered.io"
PAGE_URL = f"{BASE_URL}/stats/"
BRAND = "RoasterDB"
FIRST_PUBLISHED = "2026-09-17"
DEFAULT_DB = BASE_DIR.parent / "02_Specialty_Coffee_RoasterDB" / "data" / "roasterdb.sqlite"

# Price filters: USD listings only; retail unit sizes (no sample sachets, no bulk
# units); price per 250 g inside a plausible retail band. Everything outside is a
# wholesale unit, a subscription/gift product or a mis-parsed price, not a coffee.
PRICE_MIN_G, PRICE_MAX_G = 100, 2000
PRICE_MIN_250, PRICE_MAX_250 = 5.0, 150.0

# Dark surface palette of the RoasterDB catalog pages. Single-series charts only:
# one hue (the site accent) per chart, text in ink/muted tokens, never the data color.
P = dict(surface="#181715", surface2="#21201d", ink="#f8f7f4", muted="#9c9891",
         grid="#2c2a27", accent="#d94e34")
FONT = "'Outfit', 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"
MONO = "'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s), quote=True)


def n(v):
    """1,234 style thousands grouping for ints."""
    return f"{int(round(v)):,}"


def pct(part, whole, digits=1):
    return 0.0 if not whole else round(100.0 * part / whole, digits)


def data(v):
    """A data value (country, descriptor...) kept verbatim by scripts/i18n_common.py."""
    return f'<span translate="no">{esc(v)}</span>'


def nice_step(vmax, target_ticks=5):
    raw = vmax / target_ticks
    mag = 10 ** int(len(str(int(raw))) - 1) if raw >= 1 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


# ---------------------------------------------------------------------------
# SVG charts (self-contained: work inline and as standalone files)
# ---------------------------------------------------------------------------

def _svg_head(width, height, title, subtitle):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-labelledby="t d" font-family="{FONT}" font-size="12">',
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(subtitle)}</desc>',
        f'<rect width="{width}" height="{height}" fill="{P["surface"]}"/>',
        f'<text x="20" y="26" font-size="15" font-weight="600" fill="{P["ink"]}">{esc(title)}</text>',
        f'<text x="20" y="44" font-size="12" fill="{P["muted"]}">{esc(subtitle)}</text>',
    ]


def _svg_foot(width, height, note):
    return [f'<text x="20" y="{height - 12}" font-size="11" fill="{P["muted"]}">{esc(note)}</text>', "</svg>"]


def svg_hbar(title, subtitle, rows, note, width=720, label_w=196):
    """rows: [(label, value, display)] -- one series, bars in the accent hue,
    <= 24px thick, 4px rounded data-end and square at the baseline, value at the tip."""
    top, row_h, bar_h, val_w = 62, 30, 18, 84
    x0 = label_w + 12
    plot_w = width - x0 - val_w - 16
    vmax = max(v for _, v, _ in rows) or 1
    height = top + len(rows) * row_h + 40
    out = _svg_head(width, height, title, subtitle)
    out.append(f'<line x1="{x0}" y1="{top - 6}" x2="{x0}" y2="{top + len(rows) * row_h}" stroke="{P["grid"]}" stroke-width="1"/>')
    for i, (label, v, disp) in enumerate(rows):
        y = top + i * row_h + (row_h - bar_h) / 2
        w = max(2.0, plot_w * v / vmax)
        if w >= 8:
            shape = (f'<path d="M{x0} {y} h{w - 4:.1f} a4 4 0 0 1 4 4 v{bar_h - 8} a4 4 0 0 1 -4 4 h-{w - 4:.1f} z" '
                     f'fill="{P["accent"]}"/>')
        else:
            shape = f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{P["accent"]}"/>'
        out.append(
            f'<g><title>{esc(label)}: {esc(disp)}</title>'
            f'<rect x="0" y="{top + i * row_h}" width="{width}" height="{row_h}" fill="transparent"/>'
            f'{shape}'
            f'<text x="{x0 - 10}" y="{y + bar_h / 2 + 4}" text-anchor="end" fill="{P["ink"]}">{esc(label)}</text>'
            f'<text x="{x0 + w + 8:.1f}" y="{y + bar_h / 2 + 4}" fill="{P["muted"]}" '
            f'font-family="{MONO}" font-size="11">{esc(disp)}</text></g>')
    out += _svg_foot(width, height, note)
    return "\n".join(out)


def svg_line(title, subtitle, points, fmt, note, width=720, height=320, peak_label=None, last_label=None):
    """points: [(xlabel, value)] -- one 2px line in the accent hue, 10% area wash,
    hairline solid gridlines, >= 8px end marker with a 2px surface ring, direct labels
    only at the end and the peak, per-point hover titles."""
    top, left, right, bottom = 62, 56, 72, 46
    plot_w, plot_h = width - left - right, height - top - bottom
    vmax = max(v for _, v in points)
    step = nice_step(vmax)
    ymax = step * (int(vmax / step) + 1)
    xs = [left + plot_w * i / (len(points) - 1) for i in range(len(points))]
    ys = [top + plot_h - plot_h * v / ymax for _, v in points]
    out = _svg_head(width, height, title, subtitle)
    t = 0
    while t <= ymax + 1e-9:
        y = top + plot_h - plot_h * t / ymax
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="{P["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="{P["muted"]}" font-size="11" '
                   f'font-family="{MONO}">{esc(fmt(t))}</text>')
        t += step
    every = max(1, len(points) // 9)
    for i, (xl, _) in enumerate(points):
        if i % every == 0 or i == len(points) - 1:
            out.append(f'<text x="{xs[i]:.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="{P["muted"]}" '
                       f'font-size="11" font-family="{MONO}">{esc(xl)}</text>')
    path = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f} {ys[i]:.1f}" for i in range(len(points)))
    out.append(f'<path d="{path} L{xs[-1]:.1f} {top + plot_h} L{xs[0]:.1f} {top + plot_h} Z" fill="{P["accent"]}" fill-opacity="0.1"/>')
    out.append(f'<path d="{path}" fill="none" stroke="{P["accent"]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
    for i, (xl, v) in enumerate(points):
        out.append(f'<g><title>{esc(xl)}: {esc(fmt(v))}</title><circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="12" fill="transparent"/></g>')
    if peak_label:
        pi = max(range(len(points)), key=lambda i: points[i][1])
        out.append(f'<circle cx="{xs[pi]:.1f}" cy="{ys[pi]:.1f}" r="5" fill="{P["accent"]}" stroke="{P["surface"]}" stroke-width="2"/>')
        out.append(f'<text x="{xs[pi]:.1f}" y="{ys[pi] - 12:.1f}" text-anchor="middle" fill="{P["ink"]}" font-size="11">{esc(peak_label)}</text>')
    out.append(f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="5" fill="{P["accent"]}" stroke="{P["surface"]}" stroke-width="2"/>')
    if last_label:
        out.append(f'<text x="{xs[-1] + 10:.1f}" y="{ys[-1] + 4:.1f}" fill="{P["ink"]}" font-size="11">{esc(last_label)}</text>')
    out += _svg_foot(width, height, note)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------

def compute(db_path):
    con = sqlite3.connect(str(db_path))
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    s = {}

    s["snapshot_date"] = q("select max(date(last_seen)) from coffee_beans")[0][0]
    s["listings"] = q("select count(*) from coffee_beans")[0][0]
    s["roasters"] = q("select count(distinct roaster_id) from coffee_beans")[0][0]
    s["roaster_countries"] = q("select count(distinct r.country) from roasters r join coffee_beans b using(roaster_id) "
                               "where r.country is not null and r.country<>''")[0][0]
    s["flavor_links"] = q("select count(*) from bean_flavors")[0][0]
    s["flavor_coffees"] = q("select count(distinct bean_id) from bean_flavors")[0][0]
    s["descriptors_per_coffee"] = round(s["flavor_links"] / s["flavor_coffees"], 2)
    s["verified"] = q("select count(*) from coffee_beans where quality_flag='good'")[0][0]

    # origins (first country when a listing names several)
    orig = Counter()
    for (o,) in q("select origin_country from coffee_beans where origin_country is not null and origin_country<>''"):
        o = o.split("/")[0].strip()
        if o and o not in ("Unknown", "Blend"):
            orig[o] += 1
    s["origin_known"] = sum(orig.values())
    s["origin_countries"] = len(orig)
    s["origins"] = [(k, v, pct(v, s["origin_known"])) for k, v in orig.most_common()]

    # SCA flavor families + descriptors
    fam = q("select n.category, count(*) from bean_flavors join sca_flavor_nodes n using(flavor_id) group by 1 order by 2 desc")
    s["families"] = [(k, v, pct(v, s["flavor_links"])) for k, v in fam]
    desc = q("select n.descriptor, n.category, n.subcategory, count(distinct bean_id) from bean_flavors "
             "join sca_flavor_nodes n using(flavor_id) group by 1,2,3 order by 4 desc limit 15")
    s["descriptors"] = [(d, c, sc, v, pct(v, s["flavor_coffees"])) for d, c, sc, v in desc]

    # flavor family by origin (top origins by mapped links)
    fbo = defaultdict(Counter)
    for o, c, v in q("select b.origin_country, n.category, count(*) from bean_flavors bf join coffee_beans b using(bean_id) "
                     "join sca_flavor_nodes n using(flavor_id) where b.origin_country is not null and b.origin_country<>'' "
                     "group by 1,2"):
        fbo[o.split("/")[0].strip()][c] += v
    top_o = sorted(fbo, key=lambda o: -sum(fbo[o].values()))[:8]
    fam_names = [k for k, _, _ in s["families"]]
    s["family_names"] = fam_names
    s["flavor_by_origin"] = [(o, sum(fbo[o].values()), {f: pct(fbo[o][f], sum(fbo[o].values())) for f in fam_names})
                             for o in top_o]

    # process / roast among listings that state one
    proc = q("select process_method, count(*) from coffee_beans where process_method is not null "
             "and process_method not in ('', 'Other', 'Unknown') group by 1 order by 2 desc")
    s["process_known"] = sum(v for _, v in proc)
    s["process"] = [(k, v, pct(v, s["process_known"])) for k, v in proc]
    roast = q("select roast_level, count(*) from coffee_beans where roast_level is not null "
              "and roast_level not in ('', 'Unknown') group by 1 order by 2 desc")
    s["roast_known"] = sum(v for _, v in roast)
    s["roast"] = [(k, v, pct(v, s["roast_known"])) for k, v in roast]

    # price per 250 g
    rows = q("select price_value, weight_grams, origin_country, process_method, roast_level, varietals from coffee_beans "
             "where price_currency='USD' and price_value>0 and weight_grams>0")
    s["price_usd_rows"] = len(rows)
    priced = []
    for pv, wg, o, pm, rl, var in rows:
        if not (PRICE_MIN_G <= wg <= PRICE_MAX_G):
            continue
        p250 = pv / (wg / 250.0)
        if PRICE_MIN_250 <= p250 <= PRICE_MAX_250:
            priced.append((p250, (o or "").split("/")[0].strip(), pm or "", rl or "", (var or "").lower()))
    s["price_n"] = len(priced)
    s["price_median"] = round(statistics.median(p for p, *_ in priced), 2)
    s["price_p25"] = round(statistics.quantiles([p for p, *_ in priced], n=4)[0], 2)
    s["price_p75"] = round(statistics.quantiles([p for p, *_ in priced], n=4)[2], 2)
    by_o = defaultdict(list)
    for p, o, *_ in priced:
        if o:
            by_o[o].append(p)
    s["price_by_origin"] = sorted(((o, len(v), round(statistics.median(v), 2)) for o, v in by_o.items() if len(v) >= 50),
                                  key=lambda t: -t[2])
    by_p = defaultdict(list)
    for p, _, pm, *_ in priced:
        if pm and pm not in ("Other", "Unknown"):
            by_p[pm].append(p)
    s["price_by_process"] = sorted(((k, len(v), round(statistics.median(v), 2)) for k, v in by_p.items()), key=lambda t: -t[2])
    by_r = defaultdict(list)
    for p, _, _, rl, _ in priced:
        if rl and rl != "Unknown":
            by_r[rl].append(p)
    s["price_by_roast"] = sorted(((k, len(v), round(statistics.median(v), 2)) for k, v in by_r.items() if len(v) >= 50),
                                 key=lambda t: -t[2])
    ges = [p for p, *_, var in priced if "gesha" in var or "geisha" in var]
    non = [p for p, *_, var in priced if var and not ("gesha" in var or "geisha" in var)]
    s["gesha"] = dict(n=len(ges), median=round(statistics.median(ges), 2), other_n=len(non),
                      other_median=round(statistics.median(non), 2))
    s["gesha"]["premium"] = round(s["gesha"]["median"] / s["gesha"]["other_median"], 2)

    # elevation
    alt = q("select origin_country, altitude_min_meters, coalesce(altitude_max_meters, altitude_min_meters) from coffee_beans "
            "where altitude_min_meters>0 and origin_country is not null and origin_country<>''")
    by_a = defaultdict(list)
    for o, lo, hi in alt:
        by_a[o.split("/")[0].strip()].append((lo + hi) / 2.0)
    s["alt_n"] = len(alt)
    s["alt_by_origin"] = sorted(((o, len(v), int(round(statistics.mean(v)))) for o, v in by_a.items() if len(v) >= 20),
                                key=lambda t: -t[2])

    # roaster HQ countries (roasters with at least one listing)
    rc = q("select r.country, count(distinct r.roaster_id) from roasters r join coffee_beans b using(roaster_id) "
           "where r.country is not null and r.country<>'' group by 1 order by 2 desc")
    s["roasters_by_country"] = [(k, v, pct(v, s["roasters"])) for k, v in rc]

    # varietals (listings mentioning each; Gesha and Geisha are the same cultivar)
    vc = Counter()
    n_var = 0
    for (v,) in q("select varietals from coffee_beans where varietals is not null and varietals<>''"):
        n_var += 1
        seen = set()
        for tok in v.split(","):
            tok = tok.strip()
            if not tok:
                continue
            if tok.lower() in ("gesha", "geisha"):
                tok = "Gesha (Geisha)"
            if tok not in seen:
                seen.add(tok)
                vc[tok] += 1
    s["varietal_known"] = n_var
    s["varietals"] = [(k, v, pct(v, n_var)) for k, v in vc.most_common(12)]
    con.close()
    return s


# ---------------------------------------------------------------------------
# page
# ---------------------------------------------------------------------------

CSS = """
    :root { --bg-paper: #181715; --bg-paper-2: #21201d; --text-ink: #f8f7f4; --text-muted: #9c9891;
            --rule-color: rgba(248, 247, 244, 0.18); --accent: #d94e34; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body { background: var(--bg-paper); color: var(--text-ink); font-family: 'JetBrains Mono', monospace; line-height: 1.6; padding: 40px 20px; }
    .container { max-width: 1000px; margin: 0 auto; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .font-display { font-family: 'Outfit', sans-serif; }
    .header-bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; border-bottom: 1px solid var(--rule-color); padding-bottom: 20px; margin-bottom: 40px; }
    h1 { font-size: 2.2rem; line-height: 1.15; }
    h2 { font-size: 1.45rem; margin-top: 8px; }
    h3 { font-size: 1rem; }
    .lede { color: var(--text-muted); margin-top: 14px; font-size: 0.95rem; max-width: 72ch; }
    .tiles { list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 28px; padding: 0; }
    .tiles li { background: var(--bg-paper-2); border: 1px solid var(--rule-color); padding: 14px 16px; }
    .tiles span { display: block; color: var(--text-muted); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; }
    .tiles strong { font-family: 'Outfit', sans-serif; font-size: 1.6rem; font-weight: 600; line-height: 1.2; }
    .tiles li.date strong { font-size: 1.15rem; white-space: nowrap; }
    .toc { margin-top: 28px; padding: 16px 20px; border: 1px solid var(--rule-color); font-size: 0.82rem; }
    .toc ol { margin: 8px 0 0 18px; columns: 2; column-gap: 32px; }
    .toc li { break-inside: avoid; }
    section.stat { margin-top: 56px; padding-top: 32px; border-top: 1px solid var(--rule-color); }
    .finding { margin-top: 12px; font-size: 0.95rem; max-width: 72ch; }
    .finding strong { color: var(--accent); }
    figure { margin: 24px 0 0; background: var(--bg-paper); border: 1px solid var(--rule-color); }
    figure svg { display: block; width: 100%; height: auto; }
    figcaption { padding: 10px 14px; font-size: 0.75rem; color: var(--text-muted); border-top: 1px solid var(--rule-color); display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    details { margin-top: 14px; font-size: 0.8rem; }
    summary { cursor: pointer; color: var(--accent); }
    details pre { margin-top: 10px; padding: 12px 14px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); font-size: 0.72rem; white-space: pre-wrap; word-break: break-all; }
    .copy { margin-top: 8px; background: none; border: 1px solid var(--rule-color); color: var(--text-ink); font-family: inherit; font-size: 0.72rem; padding: 6px 12px; cursor: pointer; }
    .copy:hover { border-color: var(--accent); color: var(--accent); }
    .tbl { overflow-x: auto; margin-top: 18px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
    th, td { padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--rule-color); vertical-align: top; }
    th { background: var(--bg-paper-2); text-transform: uppercase; font-size: 0.68rem; letter-spacing: 0.08em; }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .method { margin-top: 12px; font-size: 0.8rem; color: var(--text-muted); max-width: 80ch; }
    .method li { margin: 6px 0 0 18px; }
    .cta { margin-top: 60px; padding: 32px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); text-align: center; }
    .btn { display: inline-block; background: var(--accent); color: #fff; font-weight: bold; padding: 14px 28px; border-radius: 4px; margin-top: 16px; }
    .btn:hover { text-decoration: none; opacity: .92; }
    @media (max-width: 640px) { body { padding: 24px 16px; } h1 { font-size: 1.7rem; } .toc ol { columns: 1; } }
"""


def embed_block(slug, title):
    img = f"{BASE_URL}/stats/charts/{slug}.svg"
    snippet = (f'<a href="{PAGE_URL}#{slug}"><img src="{img}" alt="{esc(title)}" width="720" '
               f'style="max-width:100%;height:auto"></a>\n'
               f'<p><small>Source: <a href="{PAGE_URL}">{BRAND} specialty coffee statistics</a> (CC BY 4.0)</small></p>')
    return (f'<details><summary>Embed this chart</summary>'
            f'<p style="margin-top:8px;color:var(--text-muted)">Paste the snippet into your post. It links the chart back to this page, which is the only attribution we ask for.</p>'
            f'<pre translate="no"><code id="embed-{slug}">{esc(snippet)}</code></pre>'
            f'<button type="button" class="copy" data-target="embed-{slug}">Copy snippet</button></details>')


def figure(slug, svg, title, note):
    return (f'<figure id="fig-{slug}">{svg}<figcaption><span>{esc(note)}</span>'
            f'<a href="/stats/charts/{slug}.svg" download="roasterdb-{slug}.svg">Download SVG</a></figcaption></figure>'
            + embed_block(slug, title))


def table(headers, rows, num_cols):
    th = "".join(f'<th{" class=\"num\"" if i in num_cols else ""}>{esc(h)}</th>' for i, h in enumerate(headers))
    body = []
    for r in rows:
        tds = []
        for i, c in enumerate(r):
            if i in num_cols:
                tds.append(f'<td class="num">{esc(c)}</td>')
            else:
                tds.append(f"<td>{data(c)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def section(slug, heading, finding, fig_html, table_html, method):
    return (f'<section class="stat" id="{slug}"><h2 class="font-display">{heading}</h2>'
            f'<p class="finding">{finding}</p>{fig_html}{table_html}'
            f'<p class="method">{method}</p></section>')


def build_page(s, charts):
    snap = s["snapshot_date"]
    today = dt.date.today().isoformat()
    src_note = f"Source: RoasterDB, roasterdb.dataengineered.io/stats · snapshot {snap} · CC BY 4.0"
    sections = []

    # 1. origins
    top = s["origins"][:12]
    rows = [(o, v, f"{p}%") for o, v, p in top]
    charts["origins"] = svg_hbar("Where specialty coffee comes from",
                                 f"Share of {n(s['origin_known'])} listings that state a producing country",
                                 rows, src_note)
    sections.append(section(
        "origins", "Where specialty coffee comes from",
        f"{data(top[0][0])} alone accounts for <strong>{top[0][2]}%</strong> of listings that name an origin, and "
        f"{data(top[0][0])} plus {data(top[1][0])} together for <strong>{round(top[0][2] + top[1][2], 1)}%</strong>. "
        f"The top five origins cover {round(sum(p for _, _, p in top[:5]), 1)}% of the catalogue; "
        f"{n(s['origin_countries'])} producing countries appear in total.",
        figure("origins", charts["origins"], "Where specialty coffee comes from", f"{n(s['origin_known'])} listings with a stated origin"),
        table(["Origin", "Listings", "Share"], [(o, n(v), f"{p}%") for o, v, p in s["origins"]], {1, 2}),
        f"Denominator: the {n(s['origin_known'])} of {n(s['listings'])} listings whose storefront states a producing country "
        f"(blends and unstated origins are excluded). When a listing names several countries, the first is counted."))

    # 2. flavor families + descriptors
    fam = s["families"]
    charts["flavor-families"] = svg_hbar("What specialty coffee tastes like",
                                         f"Share of {n(s['flavor_links'])} SCA Flavor Wheel descriptors mapped from roasters' tasting notes",
                                         [(k, v, f"{p}%") for k, v, p in fam], src_note)
    des = s["descriptors"][:12]
    charts["descriptors"] = svg_hbar("The most common tasting notes",
                                     f"Share of {n(s['flavor_coffees'])} mapped coffees whose notes resolve to each SCA descriptor",
                                     [(d, v, f"{p}%") for d, _, _, v, p in des], src_note)
    sections.append(section(
        "flavor", "What specialty coffee tastes like",
        f"<strong>{fam[0][2]}%</strong> of all mapped descriptors fall in the SCA {data(fam[0][0])} family, "
        f"{fam[1][2]}% in {data(fam[1][0])} and {fam[2][2]}% in {data(fam[2][0])}. "
        f"The single most common note is {data(des[0][0])}, on <strong>{des[0][4]}%</strong> of mapped coffees, "
        f"followed by {data(des[1][0])} ({des[1][4]}%) and {data(des[2][0])} ({des[2][4]}%). "
        f"A mapped coffee carries {s['descriptors_per_coffee']} descriptors on average.",
        figure("flavor-families", charts["flavor-families"], "What specialty coffee tastes like", f"{n(s['flavor_links'])} descriptor mappings")
        + figure("descriptors", charts["descriptors"], "The most common tasting notes", f"{n(s['flavor_coffees'])} coffees with mapped notes"),
        table(["Descriptor", "SCA family", "Subcategory", "Coffees", "Share of mapped coffees"],
              [(d, c, sc or "", n(v), f"{p}%") for d, c, sc, v, p in s["descriptors"]], {3, 4}),
        f"Roasters' free-text tasting notes are normalized to the SCA Coffee Taster's Flavor Wheel (Category > Subcategory > Descriptor). "
        f"{n(s['flavor_coffees'])} of {n(s['listings'])} listings have at least one mapped descriptor; "
        f"family shares use all {n(s['flavor_links'])} coffee-to-descriptor links, descriptor shares count coffees."))

    # 3. flavor by origin
    fbo = s["flavor_by_origin"]
    fruity = sorted(((o, d.get("Fruity", 0.0)) for o, _, d in fbo), key=lambda t: -t[1])
    charts["fruity-by-origin"] = svg_hbar("Which origins read as fruity",
                                          "Share of an origin's mapped descriptors in the SCA Fruity family",
                                          [(o, p, f"{p}%") for o, p in fruity], src_note)
    nut = sorted(((o, d.get("Nutty/Cocoa", 0.0)) for o, _, d in fbo), key=lambda t: -t[1])
    sections.append(section(
        "flavor-by-origin", "Flavor profile by origin",
        f"{data(fruity[0][0])} is the fruitiest origin in the catalogue: <strong>{fruity[0][1]}%</strong> of its mapped descriptors are Fruity, "
        f"against {fruity[-1][1]}% for {data(fruity[-1][0])}. {data(nut[0][0])} leads the Nutty/Cocoa family at {nut[0][1]}%.",
        figure("fruity-by-origin", charts["fruity-by-origin"], "Which origins read as fruity", f"{len(fbo)} origins with the most mapped descriptors"),
        table(["Origin", "Descriptors"] + s["family_names"],
              [(o, n(t)) + tuple(f"{d.get(f, 0.0)}%" for f in s["family_names"]) for o, t, d in fbo],
              set(range(1, 2 + len(s["family_names"])))),
        "Per origin, the share of its mapped descriptors in each SCA family (rows sum to 100%). "
        "Only the eight origins with the most mapped descriptors are shown."))

    # 4. process
    pr = s["process"]
    charts["process"] = svg_hbar("How specialty coffee is processed",
                                 f"Share of {n(s['process_known'])} listings that state a processing method",
                                 [(k, v, f"{p}%") for k, v, p in pr], src_note)
    sections.append(section(
        "process", "How specialty coffee is processed",
        f"Among listings that state a method, <strong>{pr[0][2]}%</strong> are {data(pr[0][0])} and {pr[1][2]}% {data(pr[1][0])}. "
        f"Experimental fermentation is no longer niche: {data('Anaerobic')} lots are "
        f"<strong>{next(p for k, _, p in pr if k == 'Anaerobic')}%</strong> of stated methods.",
        figure("process", charts["process"], "How specialty coffee is processed", f"{n(s['process_known'])} listings with a stated method"),
        table(["Process", "Listings", "Share"], [(k, n(v), f"{p}%") for k, v, p in pr], {1, 2}),
        f"Denominator: the {n(s['process_known'])} of {n(s['listings'])} listings whose storefront states one of Washed, Natural, Honey or Anaerobic. "
        f"Listings whose process is unstated or non-standard are excluded."))

    # 5. roast
    ro = s["roast"]
    charts["roast"] = svg_hbar("Roast levels in specialty coffee",
                               f"Share of {n(s['roast_known'])} listings that state a roast level",
                               [(k, v, f"{p}%") for k, v, p in ro], src_note)
    light = sum(p for k, _, p in ro if k.startswith("Light"))
    dark = sum(p for k, _, p in ro if k.startswith("Dark") or k == "Medium-Dark")
    sections.append(section(
        "roast", "Roast levels",
        f"Specialty roasters roast light: <strong>{round(light, 1)}%</strong> of listings with a stated roast level are Light or Light-Medium, "
        f"against {round(dark, 1)}% Dark or Medium-Dark.",
        figure("roast", charts["roast"], "Roast levels in specialty coffee", f"{n(s['roast_known'])} listings with a stated roast level"),
        table(["Roast level", "Listings", "Share"], [(k, n(v), f"{p}%") for k, v, p in ro], {1, 2}),
        f"Denominator: the {n(s['roast_known'])} listings that state a roast level. Most storefronts do not, so this is a sample of the catalogue, not the whole."))

    # 6. price
    pbo = s["price_by_origin"]
    charts["price-by-origin"] = svg_hbar("Median price of a 250 g bag, by origin (USD)",
                                         f"Listings priced in USD, {PRICE_MIN_G}-{n(PRICE_MAX_G)} g units, origins with 50+ priced listings",
                                         [(o, m, f"${m:.2f}") for o, _, m in pbo], src_note)
    g = s["gesha"]
    sections.append(section(
        "price", "What specialty coffee costs",
        f"The median specialty coffee lists at <strong>${s['price_median']:.2f} per 250 g</strong> "
        f"(interquartile range ${s['price_p25']:.2f} to ${s['price_p75']:.2f}). "
        f"{data(pbo[0][0])} is the most expensive origin at a median ${pbo[0][2]:.2f}, "
        f"{round(pbo[0][2] / s['price_median'], 1)} times the catalogue median; {data(pbo[-1][0])} is the cheapest at ${pbo[-1][2]:.2f}. "
        f"Lots naming the Gesha varietal carry a <strong>{g['premium']}x</strong> premium: median ${g['median']:.2f} against ${g['other_median']:.2f} for other named varietals.",
        figure("price-by-origin", charts["price-by-origin"], "Median price of a 250 g bag, by origin (USD)", f"{n(s['price_n'])} priced listings"),
        table(["Origin", "Priced listings", "Median USD per 250 g"], [(o, n(c), f"${m:.2f}") for o, c, m in pbo], {1, 2})
        + f'<h3 class="font-display" style="margin-top:24px">By processing method and roast level</h3>'
        + table(["Segment", "Priced listings", "Median USD per 250 g"],
                [(k, n(c), f"${m:.2f}") for k, c, m in s["price_by_process"]] + [(k, n(c), f"${m:.2f}") for k, c, m in s["price_by_roast"]], {1, 2}),
        f"Prices are the storefront list price at crawl time, normalized to 250 g. Filters: USD listings only; unit weight {PRICE_MIN_G} to {n(PRICE_MAX_G)} g "
        f"(excludes sample sachets and bulk units); ${PRICE_MIN_250:.0f} to ${PRICE_MAX_250:.0f} per 250 g (excludes subscriptions, gift sets and mis-parsed prices). "
        f"{n(s['price_n'])} of {n(s['price_usd_rows'])} USD-priced listings pass. Medians, not means, so a few very expensive lots do not move the figures. "
        f"Gesha premium: {n(g['n'])} lots naming Gesha or Geisha against {n(g['other_n'])} lots naming another varietal."))

    # 7. elevation
    alt = s["alt_by_origin"]
    charts["elevation"] = svg_hbar("Growing elevation by origin",
                                   f"Mean stated elevation in metres above sea level, origins with 20+ listings",
                                   [(o, m, f"{n(m)} m") for o, _, m in alt], src_note)
    sections.append(section(
        "elevation", "How high specialty coffee grows",
        f"{data(alt[0][0])} lots are grown highest, at a mean <strong>{n(alt[0][2])} m</strong> above sea level, "
        f"{n(alt[0][2] - alt[-1][2])} m above {data(alt[-1][0])} ({n(alt[-1][2])} m).",
        figure("elevation", charts["elevation"], "Growing elevation by origin", f"{n(s['alt_n'])} listings with a stated elevation"),
        table(["Origin", "Listings with elevation", "Mean elevation (masl)"], [(o, n(c), n(m)) for o, c, m in alt], {1, 2}),
        f"Elevation is stated on {n(s['alt_n'])} listings; where a range is given its midpoint is used. Origins with fewer than 20 stated elevations are omitted."))

    # 8. roasters by country
    rc = s["roasters_by_country"]
    charts["roasters-by-country"] = svg_hbar("Where the roasters are",
                                             f"Headquarters country of the {n(s['roasters'])} roasters with listings in RoasterDB",
                                             [(k, v, f"{v}") for k, v, _ in rc[:12]], src_note)
    sections.append(section(
        "roasters", "Where the roasters are",
        f"<strong>{rc[0][2]}%</strong> of the roasters in the catalogue are headquartered in {data(rc[0][0])}, "
        f"{rc[1][2]}% in {data(rc[1][0])}; {n(s['roaster_countries'])} countries are represented.",
        figure("roasters-by-country", charts["roasters-by-country"], "Where the roasters are", f"{n(s['roasters'])} roasters"),
        table(["Country", "Roasters", "Share"], [(k, n(v), f"{p}%") for k, v, p in rc], {1, 2}),
        "RoasterDB is a curated crawl of artisan roasters' own storefronts, so this describes the catalogue's coverage rather than the world's roaster population."))

    # 9. varietals
    va = s["varietals"]
    charts["varietals"] = svg_hbar("The most listed varietals",
                                   f"Share of {n(s['varietal_known'])} listings that name a varietal",
                                   [(k, v, f"{p}%") for k, v, p in va], src_note)
    sections.append(section(
        "varietals", "The most listed varietals",
        f"{data(va[0][0])} is the most frequently named cultivar, on <strong>{va[0][2]}%</strong> of listings that state a varietal, "
        f"with {data(va[1][0])} second at {va[1][2]}%.",
        figure("varietals", charts["varietals"], "The most listed varietals", f"{n(s['varietal_known'])} listings naming a varietal"),
        table(["Varietal", "Listings", "Share"], [(k, n(v), f"{p}%") for k, v, p in va], {1, 2}),
        f"Denominator: the {n(s['varietal_known'])} listings that name at least one varietal. A listing naming several counts once for each. "
        f"Gesha and Geisha are spellings of the same cultivar and are merged."))

    toc = "".join(f'<li><a href="#{slug}">{title}</a></li>' for slug, title in [
        ("origins", "Origins"), ("flavor", "Flavor families and top notes"), ("flavor-by-origin", "Flavor profile by origin"),
        ("process", "Processing methods"), ("roast", "Roast levels"), ("price", "Prices and the Gesha premium"),
        ("elevation", "Growing elevation"), ("roasters", "Roaster locations"), ("varietals", "Varietals"), ("method", "Method, reuse and citation")])

    title_tag = f"Specialty Coffee Statistics 2026 — Origins, Flavor, Prices | {BRAND}"
    desc = (f"Specialty coffee in numbers: {n(s['listings'])} listings from {n(s['roasters'])} roasters. Origin shares, SCA flavor families, "
            f"processing, roast levels, median prices per 250 g, the Gesha premium. Free to cite and embed.")
    ld_article = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "headline": "Specialty coffee in numbers: statistics from the RoasterDB catalogue",
        "description": desc, "url": PAGE_URL, "datePublished": FIRST_PUBLISHED, "dateModified": today,
        "image": f"{BASE_URL}/og-image.png", "inLanguage": "en",
        "author": {"@type": "Organization", "name": BRAND, "url": BASE_URL},
        "publisher": {"@type": "Organization", "name": "DataEngineered", "url": "https://dataengineered.io/"},
        "isBasedOn": BASE_URL + "/", "license": "https://creativecommons.org/licenses/by/4.0/",
        "about": ["specialty coffee", "coffee origins", "SCA Flavor Wheel", "coffee prices"]}, ensure_ascii=False, indent=2)
    ld_crumbs = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Statistics", "item": PAGE_URL}]}, ensure_ascii=False, indent=2)

    tiles = "".join(
        f'<li{" class=\"date\"" if lbl == "Snapshot" else ""}><span>{lbl}</span><strong>{val}</strong></li>' for lbl, val in [
            ("Coffee listings", n(s["listings"])), ("Roasters", n(s["roasters"])), ("Roaster countries", n(s["roaster_countries"])),
            ("Producing origins", n(s["origin_countries"])), ("SCA flavor mappings", n(s["flavor_links"])), ("Snapshot", snap)])

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title_tag)}</title>
  <meta name="description" content="{esc(desc)}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{PAGE_URL}" />
  <link rel="alternate" hreflang="en" href="{PAGE_URL}" />
  <link rel="icon" href="/favicon.ico" type="image/x-icon" />
  <meta property="og:title" content="Specialty coffee in numbers — {BRAND} statistics {snap[:4]}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{PAGE_URL}" />
  <meta property="og:type" content="article" />
  <meta property="og:image" content="{BASE_URL}/og-image.png" />
  <meta name="twitter:card" content="summary_large_image" />

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'" />
  <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" /></noscript>

  <script type="application/ld+json">
{ld_article}
  </script>
  <script type="application/ld+json">
{ld_crumbs}
  </script>
  <style>{CSS}  </style>
</head>
<body>
  <div class="container">
    <div class="header-bar">
      <div>
        <a href="/" translate="no" style="font-weight: 700; letter-spacing: -0.02em; color: var(--text-ink);">ROASTERDB</a>
        <span style="opacity: 0.6; font-size: 0.75rem; margin-left: 12px;">| Market statistics</span>
      </div>
      <a href="/" style="font-size: 0.85rem;">← Back to Main Explorer</a>
    </div>

    <h1 class="font-display">Specialty coffee in numbers</h1>
    <p class="lede">Aggregate statistics computed from every listing in the RoasterDB catalogue: {n(s['listings'])} specialty coffees crawled from the storefronts of {n(s['roasters'])} artisan roasters, with tasting notes normalized to the SCA Flavor Wheel. Snapshot of {snap}, refreshed monthly. Every figure is free to cite, quote and embed with a link to this page.</p>
    <ul class="tiles">{tiles}</ul>
    <nav class="toc" aria-label="Contents"><strong>On this page</strong><ol>{toc}</ol></nav>

{"".join(sections)}

    <section class="stat" id="method">
      <h2 class="font-display">Method, reuse and citation</h2>
      <ul class="method">
        <li><strong>Source.</strong> The full RoasterDB snapshot of {snap}: {n(s['listings'])} product listings collected from the public online storefronts of {n(s['roasters'])} specialty roasters in {n(s['roaster_countries'])} countries, each with its source URL and crawl timestamp. {n(s['verified'])} listings form the verified tier (origin, sanitized price and SCA mapping all present).</li>
        <li><strong>Coverage is uneven by design.</strong> Storefronts do not all publish origin, process, roast level, varietal, elevation or price. Every figure above names its denominator, so a percentage is always a share of the listings that state that attribute, never of the whole catalogue. Blank fields are never guessed.</li>
        <li><strong>Refresh.</strong> The catalogue is re-crawled monthly; this page and its charts are regenerated after each refresh, so figures move. Cite the snapshot date.</li>
        <li><strong>Reuse.</strong> The figures and charts on this page are published under <a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>: use them in articles, slides and posts with a link to <span translate="no">{PAGE_URL}</span>. The machine-readable version is <a href="/stats/data.json">data.json</a>. The underlying row-level dataset is a separate <a href="/#pricing">commercial product</a>.</li>
        <li><strong>Suggested citation.</strong> <span translate="no">RoasterDB ({snap[:4]}). <em>Specialty coffee in numbers</em>, snapshot {snap}. DataEngineered. {PAGE_URL}</span></li>
        <li><strong>Questions or corrections:</strong> <a href="/#support">contact form</a> or roasterdb@dataengineered.io.</li>
      </ul>
    </section>

    <div class="cta">
      <h3 class="font-display" style="font-size: 1.4rem;">Need the row-level data behind these numbers?</h3>
      <p style="color: var(--text-muted); margin-top: 8px; font-size: 0.85rem;">Every listing with its origin, process, roast, varietals, price and SCA flavor nodes, as SQLite, CSV and JSON.</p>
      <a href="/#pricing" class="btn">Get the full dataset ($49) →</a>
    </div>
  </div>
  <footer style="border-top:1px solid var(--rule-color); margin-top:40px; padding:24px 16px; text-align:center;">
    <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog →</a> · <a href="https://dataengineered.io/about">About</a> · <a href="https://dataengineered.io/terms">Terms</a> · <a href="https://dataengineered.io/privacy">Privacy</a> · <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
  </footer>
  <script>
    document.querySelectorAll('button.copy').forEach(function (b) {{
      b.addEventListener('click', function () {{
        var el = document.getElementById(b.getAttribute('data-target'));
        if (!el) return;
        var done = function () {{ var old = b.textContent; b.textContent = 'Copied'; setTimeout(function () {{ b.textContent = old; }}, 1500); }};
        var select = function () {{ var r = document.createRange(); r.selectNodeContents(el); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); }};
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          navigator.clipboard.writeText(el.textContent).then(done, select);
        }} else {{ select(); }}
      }});
    }});
  </script>
</body>
</html>
"""


def build_data_json(s):
    return {
        "dataset": BRAND, "page": PAGE_URL, "generated": dt.date.today().isoformat(), "snapshot": s["snapshot_date"],
        "license": "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/) - attribute with a link to the page",
        "totals": {k: s[k] for k in ("listings", "roasters", "roaster_countries", "origin_countries", "flavor_links",
                                     "flavor_coffees", "descriptors_per_coffee", "verified")},
        "origins": {"denominator": s["origin_known"], "rows": [dict(origin=o, listings=v, share_pct=p) for o, v, p in s["origins"]]},
        "flavor_families": {"denominator": s["flavor_links"], "rows": [dict(family=k, links=v, share_pct=p) for k, v, p in s["families"]]},
        "descriptors": {"denominator": s["flavor_coffees"],
                        "rows": [dict(descriptor=d, family=c, subcategory=sc, coffees=v, share_pct=p) for d, c, sc, v, p in s["descriptors"]]},
        "flavor_by_origin": [dict(origin=o, descriptors=t, family_share_pct=d) for o, t, d in s["flavor_by_origin"]],
        "process": {"denominator": s["process_known"], "rows": [dict(process=k, listings=v, share_pct=p) for k, v, p in s["process"]]},
        "roast": {"denominator": s["roast_known"], "rows": [dict(roast=k, listings=v, share_pct=p) for k, v, p in s["roast"]]},
        "price_usd_per_250g": {
            "filters": dict(currency="USD", unit_weight_g=[PRICE_MIN_G, PRICE_MAX_G], price_per_250g_usd=[PRICE_MIN_250, PRICE_MAX_250]),
            "n": s["price_n"], "median": s["price_median"], "p25": s["price_p25"], "p75": s["price_p75"],
            "by_origin": [dict(origin=o, n=c, median=m) for o, c, m in s["price_by_origin"]],
            "by_process": [dict(process=k, n=c, median=m) for k, c, m in s["price_by_process"]],
            "by_roast": [dict(roast=k, n=c, median=m) for k, c, m in s["price_by_roast"]],
            "gesha": s["gesha"]},
        "elevation_masl": {"denominator": s["alt_n"], "rows": [dict(origin=o, n=c, mean=m) for o, c, m in s["alt_by_origin"]]},
        "roasters_by_country": [dict(country=k, roasters=v, share_pct=p) for k, v, p in s["roasters_by_country"]],
        "varietals": {"denominator": s["varietal_known"], "rows": [dict(varietal=k, listings=v, share_pct=p) for k, v, p in s["varietals"]]},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", default=os.environ.get("ROASTERDB_SQLITE", str(DEFAULT_DB)))
    args = ap.parse_args()
    db = Path(args.db)
    if not db.is_file():
        raise SystemExit(f"SQLite snapshot not found: {db}")
    s = compute(db)
    charts = {}
    page = build_page(s, charts)
    OUT_DIR.mkdir(exist_ok=True)
    CHART_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.html").write_text(page, encoding="utf-8", newline="\n")
    for slug, svg in charts.items():
        (CHART_DIR / f"{slug}.svg").write_text(svg + "\n", encoding="utf-8", newline="\n")
    (OUT_DIR / "data.json").write_text(json.dumps(build_data_json(s), ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8", newline="\n")
    print(f"stats/index.html + {len(charts)} charts + data.json  (snapshot {s['snapshot_date']}, "
          f"{s['listings']:,} listings, {s['roasters']} roasters)")


if __name__ == "__main__":
    main()
