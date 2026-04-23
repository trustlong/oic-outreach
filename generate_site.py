"""
Generates docs/index.html — the OIC outreach dashboard.
Produces two ranked tables:
  1. Top 10 for the current calendar month
  2. Top 10 for the past 12 months (no recency filter)

Run after find_all_homeowners_20mi.py.
"""

import re, os
import pandas as pd
from datetime import datetime, timedelta

INPUT_FILE = "all_homeowners_20mi.csv"
os.makedirs("docs", exist_ok=True)
OUT_FILE   = "docs/index.html"

ENTITY_RE = re.compile(
    r"\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRS|PROPERTIES|HOLDINGS|REALTY|"
    r"GROUP|FUND|FOUNDATION|SERIES|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS|"
    r"VENTURES|CAPITAL|INVESTMENTS|ESTATE|MORTGAGE|TITLE|ABSTRACT)\b",
    re.IGNORECASE,
)

ETH_COLOR = {
    "Asian/PI":   "#e8f4fd",
    "Hispanic":   "#fef9e7",
    "Black":      "#fdf2f8",
    "White":      "#f9f9f9",
    "Unknown":    "#f5f5f5",
    "Am.Indian":  "#f0fff0",
    "Multiracial":"#fff0f5",
}

def parse_date(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(str(s).strip(), fmt)
        except: pass
    return None

def score(row, include_recency=True, cutoff_30=None):
    eth    = str(row.get("ESTIMATED_ETHNICITY", ""))
    origin = str(row.get("MOVE_ORIGIN", ""))
    dist   = float(row.get("DISTANCE_MILES", 99))
    dt     = row.get("_dt")
    s  = {"Asian/PI": 3, "Hispanic": 2, "Black": 2}.get(eth, 1)
    s += 2 if origin.startswith("Out-of-state") else 1
    s += 2 if dist <= 5 else (1 if dist <= 10 else 0)
    if include_recency and cutoff_30 and dt and dt >= cutoff_30:
        s += 1
    return s

def load_and_clean():
    df = pd.read_csv(INPUT_FILE, dtype=str)
    df["_dt"] = df["Sale1D"].apply(parse_date)
    df = df[df["_dt"].notna()].copy()
    df = df[~df["Owner1"].apply(lambda x: bool(ENTITY_RE.search(str(x))))].copy()
    df = df[~df["MOVE_ORIGIN"].isin(["Local"])].copy()
    return df

def top10_month(df, year, month):
    sub = df[(df["_dt"].apply(lambda d: d.year == year and d.month == month))].copy()
    sub["SCORE"] = sub.apply(lambda r: score(r, include_recency=False), axis=1)
    return sub.sort_values(["SCORE", "DISTANCE_MILES"], ascending=[False, True]).head(10)

def top10_year(df):
    cutoff_30 = datetime.now() - timedelta(days=30)
    df = df.copy()
    df["SCORE"] = df.apply(lambda r: score(r, include_recency=True, cutoff_30=cutoff_30), axis=1)
    return df.sort_values(["SCORE", "DISTANCE_MILES"], ascending=[False, True]).head(10)

def fmt_origin(o):
    o = str(o)
    if o.startswith("Out-of-state"):
        state = o.replace("Out-of-state (","").replace(")","")
        return f'<span style="color:#c0392b;font-weight:600">✈ {state}</span>'
    if o.startswith("In-state"):
        return '<span style="color:#2980b9">↔ In-state VA</span>'
    return '<span style="color:#888">? Unknown</span>'

def table_html(df, title, subtitle):
    rows = ""
    for _, r in df.iterrows():
        eth   = str(r.get("ESTIMATED_ETHNICITY",""))
        color = ETH_COLOR.get(eth, "#fff")
        dist  = float(r.get("DISTANCE_MILES", 0))
        hh    = r.get("EST_HOUSEHOLD_SIZE", "")
        rows += f"""
        <tr style="background:{color}">
          <td style="text-align:center;font-weight:700;font-size:1.1em">{int(r['SCORE'])}</td>
          <td style="text-align:center">{dist:.1f} mi</td>
          <td>{r.get('SOURCE','')}</td>
          <td style="font-weight:600">{r.get('Owner1','')}</td>
          <td style="color:#555;font-size:.9em">{r.get('LocAddr','') or '—'}</td>
          <td style="text-align:center">{r.get('Sale1D','')}</td>
          <td><span style="background:{color};border:1px solid #ccc;border-radius:4px;padding:2px 6px;font-size:.85em">{eth}</span></td>
          <td style="font-size:.9em">{fmt_origin(r.get('MOVE_ORIGIN',''))}</td>
          <td style="text-align:center">{hh}</td>
        </tr>"""

    return f"""
    <div class="table-block">
      <h2>{title}</h2>
      <p class="subtitle">{subtitle}</p>
      <table>
        <thead><tr>
          <th>Score</th><th>Distance</th><th>County</th><th>Owner</th>
          <th>Address</th><th>Sale Date</th><th>Ethnicity</th><th>Origin</th><th>HH</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

def build_html(t_month, t_year, now, month_label):
    scoring_note = """
    <b>Scoring (max 8):</b>
    Asian/PI +3 &nbsp;|&nbsp; Hispanic/Black +2 &nbsp;|&nbsp; Other +1 &nbsp;&nbsp;
    Out-of-state +2 &nbsp;|&nbsp; In-state/Unknown +1 &nbsp;&nbsp;
    ≤5 mi +2 &nbsp;|&nbsp; 5–10 mi +1 &nbsp;&nbsp;
    Past 30 days +1 (year table only)
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>OIC Outreach — New Homeowners</title>
  <style>
    body {{ font-family: -apple-system, Arial, sans-serif; margin: 0; background: #f4f6f9; color: #333; }}
    header {{ background: #2c3e50; color: white; padding: 24px 32px; }}
    header h1 {{ margin: 0 0 4px; font-size: 1.6em; }}
    header p  {{ margin: 0; opacity: .75; font-size: .95em; }}
    .container {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px; }}
    .table-block {{ background: white; border-radius: 10px; padding: 24px; margin-bottom: 32px;
                    box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    h2 {{ margin: 0 0 4px; font-size: 1.25em; color: #2c3e50; }}
    .subtitle {{ color: #888; margin: 0 0 16px; font-size: .9em; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .9em; }}
    th {{ background: #2c3e50; color: white; padding: 10px 12px; text-align: left; font-weight: 600; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #eee; vertical-align: middle; }}
    tr:last-child td {{ border-bottom: none; }}
    .scoring {{ background: white; border-radius: 10px; padding: 16px 24px; margin-bottom: 24px;
                font-size: .85em; color: #555; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
    footer {{ text-align: center; padding: 24px; font-size: .8em; color: #aaa; }}
    .legend {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }}
    .leg-item {{ display: flex; align-items: center; gap: 6px; font-size: .82em; }}
    .leg-dot {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #ccc; }}
  </style>
</head>
<body>
<header>
  <h1>⛪ OIC New Homeowner Outreach</h1>
  <p>One In Christ Church &nbsp;·&nbsp; 1595 Turkey Foot Rd, Forest VA &nbsp;·&nbsp;
     20-mile radius &nbsp;·&nbsp; Updated {now.strftime("%B %d, %Y")}</p>
</header>
<div class="container">
  <div class="scoring">{scoring_note}</div>
  <div class="legend">
    {''.join(f'<div class="leg-item"><div class="leg-dot" style="background:{c}"></div>{e}</div>' for e,c in ETH_COLOR.items())}
  </div>
  {table_html(t_month, f"Top 10 — {month_label}", "Scored within this calendar month only. Recency not included (all records are this month).")}
  {table_html(t_year,  "Top 10 — Past 12 Months", "Best overall across the full year. Recency bonus (+1) applied for sales within past 30 days.")}
</div>
<footer>Data sourced from Bedford, Lynchburg, Campbell, Amherst &amp; Appomattox County GIS &nbsp;·&nbsp;
Ethnicity estimated via surgeo BISG (Census surname model) &nbsp;·&nbsp;
Refreshed weekly every Monday</footer>
</body>
</html>"""

def main():
    now   = datetime.now()
    df    = load_and_clean()
    t_month = top10_month(df, now.year, now.month)
    t_year  = top10_year(df)
    month_label = now.strftime("%B %Y")
    html = build_html(t_month, t_year, now, month_label)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Site generated → {OUT_FILE}")

if __name__ == "__main__":
    main()
