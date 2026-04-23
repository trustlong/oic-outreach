"""
Generates docs/index.html — OIC outreach dashboard (mobile-first design).
Two views toggled by a switch: This Month vs Past 12 Months.
Each homeowner shown as a compact card, expandable for full details.
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
    "Asian/PI":    "#1a73e8",
    "Hispanic":    "#e67e22",
    "Black":       "#8e44ad",
    "White":       "#7f8c8d",
    "Unknown":     "#95a5a6",
    "Am.Indian":   "#27ae60",
    "Multiracial": "#c0392b",
}

def parse_date(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(str(s).strip(), fmt)
        except: pass
    return None

def score(row, include_recency=False, cutoff_30=None):
    eth       = str(row.get("ESTIMATED_ETHNICITY", ""))
    origin    = str(row.get("MOVE_ORIGIN", ""))
    dist      = float(row.get("DISTANCE_MILES", 99))
    is_cn     = str(row.get("IS_CHINESE", "")).lower() in ("true", "1")

    # Ethnicity: Chinese=3, other Asian=2, Hispanic/Black=1, White/Unknown=0
    if is_cn:                               eth_s = 3
    elif eth == "Asian/PI":                 eth_s = 2
    elif eth in ("Hispanic", "Black"):      eth_s = 1
    else:                                   eth_s = 0

    ori_s = 2 if origin.startswith("Out-of-state") else 1
    dis_s = 2 if dist <= 5 else (1 if dist <= 10 else 0)
    return eth_s + ori_s + dis_s

def load_and_clean():
    df = pd.read_csv(INPUT_FILE, dtype=str)
    df["_dt"] = df["Sale1D"].apply(parse_date)
    df = df[df["_dt"].notna()].copy()
    df = df[~df["Owner1"].apply(lambda x: bool(ENTITY_RE.search(str(x))))].copy()
    df = df[~df["MOVE_ORIGIN"].isin(["Local"])].copy()
    return df

def top10_month(df, year, month):
    sub = df[df["_dt"].apply(lambda d: d.year == year and d.month == month)].copy()
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
        state = o.replace("Out-of-state (", "").replace(")", "")
        return f"✈ Moved from {state}"
    if o.startswith("In-state"):
        return "↔ Moved within VA"
    return "? Origin unknown"

def fmt_name(owner):
    """Title-case and clean up owner name."""
    if not isinstance(owner, str): return owner
    # Remove trailing suffixes
    name = owner.strip().rstrip(".")
    # Title case
    return " ".join(w.capitalize() for w in name.split())

def cards_json(df):
    """Serialize top-10 rows to a JS-safe list of dicts."""
    import json
    rows = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        eth    = str(r.get("ESTIMATED_ETHNICITY", "Unknown"))
        origin = str(r.get("MOVE_ORIGIN", ""))
        dist   = float(r.get("DISTANCE_MILES", 0))
        hh     = r.get("EST_HOUSEHOLD_SIZE", "")
        addr   = str(r.get("LocAddr", "") or "").strip()
        lat = r.get("LAT", "")
        lon = r.get("LON", "")
        try:
            nav_url = f"https://maps.google.com/?q={float(lat)},{float(lon)}" if lat and lon else ""
        except Exception:
            nav_url = ""
        rows.append({
            "rank":    i,
            "score":   int(r.get("SCORE", 0)),
            "name":    fmt_name(str(r.get("Owner1", ""))),
            "addr":    addr if addr and addr != "0.0" else "Address on file",
            "county":  str(r.get("SOURCE", "")),
            "date":    str(r.get("Sale1D", "")),
            "eth":     eth,
            "color":   ETH_COLOR.get(eth, "#95a5a6"),
            "origin":  fmt_origin(origin),
            "hh":      str(hh) if hh else "—",
            "dist":    f"{dist:.1f}",
            "nav":     nav_url,
            "lat":     float(lat) if lat else 0,
            "lon":     float(lon) if lon else 0,
        })
    return json.dumps(rows)

def build_html(t_month, t_year, now, month_label):
    month_data = cards_json(t_month)
    year_data  = cards_json(t_year)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <title>OIC Outreach</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      min-height: 100vh;
    }}

    /* ── Header ── */
    header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      padding: 20px 16px 16px;
      text-align: center;
    }}
    header h1 {{ font-size: 1.2em; font-weight: 700; letter-spacing: .3px; }}
    header p  {{ font-size: .78em; opacity: .65; margin-top: 4px; }}

    /* ── Following Up section ── */
    .followup-wrap {{
      display: none;
      margin: 0 12px 4px;
      background: #fff8ee;
      border: 1px solid #f5d78e;
      border-radius: 12px;
      overflow: hidden;
    }}
    .followup-wrap.has-items {{ display: block; }}
    .followup-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px 6px;
      font-size: .82em;
      font-weight: 700;
      color: #b7791f;
    }}
    .followup-header span {{ font-weight: 400; color: #c4933f; font-size: .9em; }}
    .followup-cards {{ padding: 0 8px 8px; }}

    /* ── Toggle ── */
    .toggle-wrap {{
      display: flex;
      justify-content: center;
      padding: 16px;
      gap: 0;
    }}
    .toggle-btn {{
      flex: 1;
      max-width: 180px;
      padding: 10px 0;
      font-size: .88em;
      font-weight: 600;
      border: 2px solid #1a73e8;
      cursor: pointer;
      transition: all .2s;
      background: white;
      color: #1a73e8;
    }}
    .toggle-btn:first-child {{ border-radius: 8px 0 0 8px; border-right: none; }}
    .toggle-btn:last-child  {{ border-radius: 0 8px 8px 0; }}
    .toggle-btn.active {{ background: #1a73e8; color: white; }}

    /* ── Section label ── */
    .section-label {{
      text-align: center;
      font-size: .78em;
      color: #888;
      padding: 0 16px 12px;
    }}

    /* ── Cards ── */
    .cards {{ padding: 0 12px 80px; }}

    .card {{
      background: white;
      border-radius: 12px;
      margin-bottom: 10px;
      overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
      border-left: 4px solid #ccc;
      transition: box-shadow .2s;
    }}
    .card.open {{ box-shadow: 0 4px 16px rgba(0,0,0,.12); }}

    .card-header {{
      display: flex;
      align-items: center;
      padding: 13px 14px;
      cursor: pointer;
      gap: 12px;
      -webkit-tap-highlight-color: transparent;
    }}

    .rank {{
      font-size: 1.1em;
      font-weight: 800;
      color: #bbb;
      min-width: 22px;
      text-align: center;
    }}

    .card-main {{ flex: 1; min-width: 0; }}
    .card-name {{
      font-size: .95em;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: #1a1a2e;
    }}
    .card-meta {{
      font-size: .78em;
      color: #888;
      margin-top: 3px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .eth-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 20px;
      font-size: .72em;
      font-weight: 700;
      color: white;
      white-space: nowrap;
    }}

    .chevron {{
      font-size: .8em;
      color: #ccc;
      transition: transform .25s;
      min-width: 16px;
    }}
    .card.open .chevron {{ transform: rotate(180deg); }}

    /* ── Expanded detail ── */
    .card-detail {{
      display: none;
      padding: 0 14px 14px 48px;
      font-size: .84em;
      color: #555;
      border-top: 1px solid #f0f0f0;
    }}
    .card.open .card-detail {{ display: block; padding-top: 12px; }}

    .detail-row {{
      display: flex;
      gap: 8px;
      margin-bottom: 6px;
      align-items: flex-start;
    }}
    .detail-label {{
      color: #aaa;
      min-width: 64px;
      font-size: .88em;
      padding-top: 1px;
    }}
    .detail-value {{ color: #333; font-weight: 500; }}

    .score-dots {{
      display: flex;
      gap: 4px;
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #f0f0f0;
    }}
    .dot {{
      width: 10px; height: 10px;
      border-radius: 50%;
      background: #e0e0e0;
    }}
    .dot.filled {{ background: #1a73e8; }}
    .score-label {{ font-size: .75em; color: #aaa; margin-left: 6px; align-self: center; }}

    .nav-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-top: 12px;
      padding: 7px 14px;
      background: transparent;
      color: #1a73e8;
      border: 1px solid #d0d8e8;
      border-radius: 8px;
      font-size: .82em;
      font-weight: 500;
      text-decoration: none;
      -webkit-tap-highlight-color: transparent;
    }}
    .nav-btn:active {{ opacity: .6; }}

    /* ── Action buttons ── */
    .actions {{
      display: flex;
      gap: 8px;
      margin-top: 12px;
      flex-wrap: wrap;
    }}
    .action-btn {{
      flex: 1;
      min-width: 80px;
      padding: 8px 6px;
      border-radius: 8px;
      font-size: .78em;
      font-weight: 600;
      border: 1px solid #e0e0e0;
      background: white;
      color: #555;
      cursor: pointer;
      text-align: center;
      -webkit-tap-highlight-color: transparent;
      transition: all .15s;
    }}
    .action-btn.visited  {{ background: #eafaf1; border-color: #27ae60; color: #27ae60; }}
    .action-btn.interested {{ background: #fef9e7; border-color: #f39c12; color: #e67e22; }}

    /* ── Note textarea ── */
    .note-area {{
      width: 100%;
      margin-top: 10px;
      padding: 8px 10px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      font-size: .82em;
      font-family: inherit;
      color: #333;
      resize: none;
      min-height: 60px;
      display: none;
    }}
    .note-area.visible {{ display: block; }}
    .note-save {{
      margin-top: 6px;
      padding: 6px 14px;
      background: #f0f0f0;
      border: none;
      border-radius: 6px;
      font-size: .78em;
      font-weight: 600;
      color: #555;
      cursor: pointer;
      display: none;
    }}
    .note-save.visible {{ display: inline-block; }}
    .note-saved-text {{
      font-size: .78em;
      color: #aaa;
      margin-top: 6px;
      display: none;
    }}

    /* ── Updated stamp ── */
    .updated {{
      text-align: center;
      font-size: .72em;
      color: #bbb;
      padding: 8px;
    }}

    /* ── Footnotes ── */
    .footnotes {{
      padding: 0 16px 24px;
      font-size: .74em;
      color: #aaa;
      line-height: 1.7;
    }}
    .footnotes p {{ margin-bottom: 4px; }}

    /* ── Empty state ── */
    .empty {{
      text-align: center;
      color: #bbb;
      padding: 40px 16px;
      font-size: .9em;
    }}
  </style>
</head>
<body>

<header>
  <h1>⛪ OIC Outreach</h1>
  <p>New homeowners within 20 miles · Updated {now.strftime("%b %d, %Y")}</p>
  <a href="nearme.html" style="display:inline-block;margin-top:10px;font-size:.8em;color:rgba(255,255,255,.7);text-decoration:none">📍 Near me →</a>
</header>

<div class="followup-wrap" id="followup-wrap">
  <div class="followup-header" onclick="toggleFollowUpSection()" style="cursor:pointer">
    📌 Following Up <span id="followup-count"></span>
    <span id="followup-chevron" style="font-size:.8em;color:#c4933f;margin-left:auto;transition:transform .25s;display:inline-block">▲</span>
  </div>
  <div class="followup-cards" id="followup-cards"></div>
</div>

<div class="toggle-wrap">
  <button class="toggle-btn active" id="btn-month" onclick="showView('month')">
    This Month
  </button>
  <button class="toggle-btn" id="btn-year" onclick="showView('year')">
    Past 12 Months
  </button>
</div>

<p class="section-label" id="section-label">{month_label} · Top 10 priority households</p>

<div class="cards" id="cards-container"></div>

<div class="footnotes">
  <p>¹ Ethnicity estimated from US Census surname data (BISG model) — not verified.</p>
  <p>² "Origin unknown" means the mailing address was already updated to the new home, or county has no mailing data (Campbell).</p>
  <p>³ Household size estimated from sqft where available (Lynchburg, Amherst), otherwise from sale price — treat as approximate.</p>
  <p>⁴ Companies, LLCs, and confirmed local movers are excluded.</p>
  <p>⁵ Priority score (max 7): ethnicity Chinese=+3, other Asian=+2, Hispanic/Black=+1, White/Unknown=+0 · origin out-of-state=+2, in-state/unknown=+1 · distance ≤5mi=+2, ≤10mi=+1.</p>
</div>

<script>
const MONTH_DATA = {month_data};
const YEAR_DATA  = {year_data};
const MONTH_LABEL = "{month_label} · Top 10 priority households";
const YEAR_LABEL  = "Past 12 months · Top 10 priority households";

let currentView = 'month';

function showView(view) {{
  currentView = view;
  document.getElementById('btn-month').classList.toggle('active', view === 'month');
  document.getElementById('btn-year').classList.toggle('active', view  === 'year');
  document.getElementById('section-label').textContent = view === 'month' ? MONTH_LABEL : YEAR_LABEL;
  const data = view === 'month' ? MONTH_DATA : YEAR_DATA;
  renderCards(data);
  setTimeout(() => loadState(view, data), 50);
}}

function renderCards(data) {{
  const container = document.getElementById('cards-container');
  if (!data.length) {{
    container.innerHTML = '<div class="empty">No records for this period.</div>';
    return;
  }}
  container.innerHTML = data.map((r, i) => `
    <div class="card" id="card-${{i}}" style="border-left-color:${{r.color}}" >
      <div class="card-header" onclick="toggleCard(${{i}})">
        <span class="rank">${{r.rank}}</span>
        <div class="card-main">
          <div class="card-name">${{r.name}}</div>
          <div class="card-meta">
            <span>${{r.dist}} mi · ${{r.county}}</span>
            <span style="color:#aaa">·</span>
            <span>${{r.date}}</span>
          </div>
        </div>
        <span class="eth-badge" style="background:${{r.color}}">${{r.eth}}</span>
        <span class="chevron">▼</span>
      </div>
      <div class="card-detail">
        <div class="detail-row">
          <span class="detail-label">Address</span>
          <span class="detail-value">${{r.addr}}, ${{r.county}}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Origin</span>
          <span class="detail-value">${{r.origin}}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Household</span>
          <span class="detail-value">Est. ${{r.hh}} people</span>
        </div>
        <div class="score-dots">
          ${{Array.from({{length: 8}}, (_, j) =>
            `<div class="dot ${{j < r.score ? 'filled' : ''}}"></div>`
          ).join('')}}
          <span class="score-label">Priority score ${{r.score}}/8</span>
        </div>
        ${{r.nav ? `<a class="nav-btn" href="${{r.nav}}" target="_blank" rel="noopener">
          📍 Navigate to address
        </a>` : ''}}
        <div class="actions">
          <button class="action-btn" id="visited-${{i}}" onclick="toggleVisited(${{i}}, event)">❓ Visited</button>
          <button class="action-btn" id="interested-${{i}}" onclick="toggleInterested(${{i}}, event)">❓ Follow Up?</button>
          <button class="action-btn" onclick="toggleNote(${{i}}, event)">📝 Note</button>
        </div>
        <textarea class="note-area" id="note-${{i}}" placeholder="Add a note..." oninput="saveNote(${{i}})" onchange="saveNote(${{i}})"></textarea>
        <button class="note-save" id="note-save-${{i}}" onclick="saveNote(${{i}})">Save note</button>
        <div class="note-saved-text" id="note-saved-${{i}}">✓ Saved</div>
      </div>
    </div>
  `).join('');
}}

function toggleCard(i) {{
  const card = document.getElementById('card-' + i);
  card.classList.toggle('open');
  // Re-apply gray only when collapsed and marked visited
  const isOpen = card.classList.contains('open');
  const isVisited = document.getElementById('visited-' + i)?.classList.contains('visited');
  card.style.opacity = (!isOpen && isVisited) ? '0.45' : '1';
}}

// Collect all cards from both views (deduplicated by key)
const ALL_CARDS = Object.values(
  [...MONTH_DATA, ...YEAR_DATA].reduce((acc, c) => {{
    const k = cardKey(null, c); acc[k] = c; return acc;
  }}, {{}})
);

function renderFollowUp() {{
  const interested = ALL_CARDS.filter(c => getState(c).interested);
  const wrap  = document.getElementById('followup-wrap');
  const count = document.getElementById('followup-count');
  const cont  = document.getElementById('followup-cards');
  if (!interested.length) {{ wrap.classList.remove('has-items'); return; }}
  wrap.classList.add('has-items');
  count.textContent = `(${{interested.length}})`;
  cont.innerHTML = interested.map(r => `
    <div class="card" id="fp-card-${{cardKey(null,r)}}" style="border-left-color:${{r.color}};margin-bottom:6px">
      <div class="card-header" onclick="toggleFpCard('${{cardKey(null,r)}}')">
        <div class="card-main">
          <div class="card-name">${{r.name}}</div>
          <div class="card-meta"><span>${{r.dist}} mi · ${{r.county}}</span><span style="color:#aaa">·</span><span>${{r.date}}</span></div>
        </div>
        <span class="eth-badge" style="background:${{r.color}}">${{r.eth}}</span>
        <span class="chevron">▼</span>
      </div>
      <div class="card-detail">
        <div class="detail-row"><span class="detail-label">Address</span><span class="detail-value">${{r.addr}}, ${{r.county}}</span></div>
        <div class="detail-row"><span class="detail-label">Origin</span><span class="detail-value">${{r.origin}}</span></div>
        ${{(function() {{
          const key = cardKey(null, r);
          const note = getState(r).note || '';
          return `<div class="detail-row" style="flex-direction:column;gap:4px">
            <span class="detail-label">Note</span>
            <textarea class="note-area visible" id="fp-note-${{key}}"
              style="margin-top:4px"
              placeholder="Add a note..."
              oninput="saveFpNote('${{key}}')"
              onchange="saveFpNote('${{key}}')"
            >${{note}}</textarea>
            <button class="note-save visible" onclick="saveFpNote('${{key}}')">Save note</button>
            <div class="note-saved-text" id="fp-note-saved-${{key}}">✓ Saved</div>
          </div>`;
        }})()}}
        ${{r.nav ? `<a class="nav-btn" href="${{r.nav}}" target="_blank" rel="noopener">📍 Navigate to address</a>` : ''}}
        <div style="margin-top:10px">
          <button style="font-size:.78em;color:#c0392b;background:none;border:1px solid #eaa;border-radius:6px;padding:5px 10px;cursor:pointer"
            onclick="removeFollowUp('${{cardKey(null,r)}}', event)">✕ Remove from Following Up</button>
        </div>
      </div>
    </div>
  `).join('');
}}

function toggleFpCard(key) {{
  document.getElementById('fp-card-' + key)?.classList.toggle('open');
}}

function toggleFollowUpSection() {{
  const cards = document.getElementById('followup-cards');
  const chevron = document.getElementById('followup-chevron');
  const collapsed = cards.style.display === 'none';
  cards.style.display = collapsed ? '' : 'none';
  chevron.style.transform = collapsed ? '' : 'rotate(180deg)';
}}

function saveFpNote(key) {{
  const val = document.getElementById('fp-note-' + key)?.value || '';
  const stored = JSON.parse(localStorage.getItem(key) || '{{}}');
  localStorage.setItem(key, JSON.stringify({{...stored, note: val}}));
  // Sync to matching main list textarea if it exists in current view
  const data = currentView === 'month' ? MONTH_DATA : YEAR_DATA;
  data.forEach((r, i) => {{
    if (cardKey(null, r) === key) {{
      const mainTA = document.getElementById('note-' + i);
      if (mainTA && mainTA.value !== val) mainTA.value = val;
    }}
  }});
  // Flash saved confirmation
  const saved = document.getElementById('fp-note-saved-' + key);
  if (saved) {{ saved.style.display = 'block'; setTimeout(() => saved.style.display = 'none', 1500); }}
}}

function removeFollowUp(key, e) {{
  e.stopPropagation();
  const stored = JSON.parse(localStorage.getItem(key) || '{{}}');
  localStorage.setItem(key, JSON.stringify({{...stored, interested: false}}));
  // Also update the button in the main list if visible
  ALL_CARDS.forEach((c, idx) => {{
    if (cardKey(null,c) === key) {{
      ['month','year'].forEach(v => {{
        const data = v === 'month' ? MONTH_DATA : YEAR_DATA;
        data.forEach((r, i) => {{
          if (cardKey(null,r) === key) {{
            const btn = document.getElementById('interested-' + i);
            if (btn) {{ btn.classList.remove('interested'); btn.textContent = '❓ Follow Up?'; }}
          }}
        }});
      }});
    }}
  }});
  renderFollowUp();
}}

function cardKey(view, card) {{
  // owner + sale date + coords — unique per transaction even if address resells
  const name = card.name.replace(/[^a-z0-9]/gi,'').toLowerCase().slice(0,12);
  const date = card.date.replace(/[^0-9]/g,'');
  return `oic-${{name}}-${{date}}-${{card.lat.toFixed(3)}}-${{card.lon.toFixed(3)}}`;
}}

function loadState(view, data) {{
  data.forEach((r, i) => {{
    const state = getState(r);
    if (state.visited) {{
      const btn = document.getElementById('visited-' + i);
      if (btn) {{ btn.classList.add('visited'); btn.textContent = '✅ Visited'; }}
      const card = document.getElementById('card-' + i);
      if (card && !card.classList.contains('open')) card.style.opacity = '0.45';
    }}
    if (state.interested) {{
      const btn = document.getElementById('interested-' + i);
      if (btn) {{ btn.classList.add('interested'); btn.textContent = '📌 Following Up'; }}
    }}
    if (state.note) {{
      const ta = document.getElementById('note-' + i);
      if (ta) {{ ta.value = state.note; ta.classList.add('visible'); }}
      const btn = document.getElementById('note-save-' + i);
      if (btn) btn.classList.add('visible');
    }}
  }});
}}

function getState(card) {{
  return JSON.parse(localStorage.getItem(cardKey(null, card)) || '{{}}');
}}
function setState(card, patch) {{
  const s = getState(card);
  localStorage.setItem(cardKey(null, card), JSON.stringify({{...s, ...patch}}));
}}

function toggleVisited(i, e) {{
  e.stopPropagation();
  const btn = document.getElementById('visited-' + i);
  const active = btn.classList.toggle('visited');
  btn.textContent = active ? '✅ Visited' : '❓ Visited';
  const data = currentView === 'month' ? MONTH_DATA : YEAR_DATA;
  setState(data[i], {{visited: active}});
  // Gray out only if card is collapsed
  const card = document.getElementById('card-' + i);
  const isOpen = card.classList.contains('open');
  card.style.opacity = (active && !isOpen) ? '0.45' : '1';
}}

function toggleInterested(i, e) {{
  e.stopPropagation();
  const btn = document.getElementById('interested-' + i);
  const active = btn.classList.toggle('interested');
  btn.textContent = active ? '📌 Following Up' : '❓ Follow Up?';
  const data = currentView === 'month' ? MONTH_DATA : YEAR_DATA;
  setState(data[i], {{interested: active}});
  renderFollowUp();
}}

function toggleNote(i, e) {{
  e.stopPropagation();
  document.getElementById('note-' + i).classList.toggle('visible');
  document.getElementById('note-save-' + i).classList.toggle('visible');
  document.getElementById('note-' + i).focus();
}}

function saveNote(i) {{
  const val = document.getElementById('note-' + i).value;
  const data = currentView === 'month' ? MONTH_DATA : YEAR_DATA;
  setState(data[i], {{note: val}});
  // Sync to Following Up textarea if present
  const key = cardKey(null, data[i]);
  const fpTA = document.getElementById('fp-note-' + key);
  if (fpTA && fpTA.value !== val) fpTA.value = val;
  const saved = document.getElementById('note-saved-' + i);
  saved.style.display = 'block';
  setTimeout(() => saved.style.display = 'none', 1500);
}}

// Init
renderCards(MONTH_DATA);
setTimeout(() => {{ loadState('month', MONTH_DATA); renderFollowUp(); }}, 50);
</script>

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

    # Copy CSV to docs/ so GitHub Pages can serve it for nearme.html
    import shutil
    shutil.copy(INPUT_FILE, "docs/all_homeowners_20mi.csv")
    print(f"✅ CSV copied → docs/all_homeowners_20mi.csv")

if __name__ == "__main__":
    main()
