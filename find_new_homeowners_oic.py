"""
New Homeowner Finder – Near One In Christ Church (OIC)
=======================================================
Data sources:
  - Bedford County GIS Open Data Portal (parcels w/ geometry + sale info)
  - Lynchburg City GIS Open Data Portal  (parcels w/ geometry + sale info)
  - Campbell County GIS (AssessorLG/MapServer/38 — Parcel Owner Labels)

HOW TO RUN:
  pip install requests pandas geopy
  python find_new_homeowners_oic.py [--days N] [--miles N]
"""

import argparse
import requests
import pandas as pd
from geopy.distance import geodesic
from datetime import datetime, timedelta

# ── Configuration ──────────────────────────────────────────────────────────────

OIC_LAT = 37.3244
OIC_LON = -79.2885

RADIUS_MILES = 3.0
RECENT_DAYS  = 90

OUTPUT_FILE = "new_homeowners_near_oic.csv"
MAP_FILE    = "new_homeowners_near_oic_map.html"

GOOGLE_MAPS_API_KEY = "AIzaSyDy1GDEOz1L3kST0bFiQ3se8KVTxxI3Bt8"

BEDFORD_API  = (
    "https://webgis.bedfordcountyva.gov/arcgis/rest/services/"
    "OpenData/OpenDataProperty/MapServer/6/query"
)
LYNCHBURG_API = (
    "https://mapviewer.lynchburgva.gov/ArcGIS/rest/services/"
    "OpenData/ODPDynamic/MapServer/41/query"
)
CAMPBELL_API = (
    "https://gis.co.campbell.va.us/arcgis/rest/services/"
    "CommunityDevelopment/AssessorLG/MapServer/38/query"
)

BATCH_SIZE = 1000

# ── Args ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="OIC New Homeowner Outreach Finder")
    parser.add_argument("--days",  type=int,   default=RECENT_DAYS,
                        help="Days back to look for sales (default: %(default)s)")
    parser.add_argument("--miles", type=float, default=RADIUS_MILES,
                        help="Search radius in miles from OIC (default: %(default)s)")
    parser.add_argument("--namsor-key", type=str, default="",
                        help="NameSor API key for accurate given-name Chinese detection "
                             "(free tier at namsor.app). Falls back to heuristic if omitted.")
    return parser.parse_args()

# ── Geometry helper ────────────────────────────────────────────────────────────

def centroid_of_rings(geometry):
    if not geometry or "rings" not in geometry:
        return None, None
    ring = geometry["rings"][0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return sum(lats) / len(lats), sum(lons) / len(lons)

# ── Step 1a: Bedford County ────────────────────────────────────────────────────

def download_bedford(days):
    cutoff = datetime.now() - timedelta(days=days)
    years  = range(cutoff.year, datetime.now().year + 1)
    where  = " OR ".join(f"Sale1D LIKE '%{y}'" for y in years)

    records, offset = [], 0
    print("📥 Bedford County...")
    while True:
        resp = requests.get(BEDFORD_API, params={
            "where": where,
            "outFields": "PIN,LocAddr,Owner1,Owner2,MailAddr,MailCity,MailStat,MailZip,Sale1D,Sale1Amt,Grantor1",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            break
        for feat in features:
            a = feat["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(feat.get("geometry"))
            a["SOURCE"] = "Bedford"
            a["SALE_DATE_STR"] = a.get("Sale1D", "")
            records.append(a)
        print(f"   {len(records)} so far…")
        if len(features) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    print(f"   ✅ {len(records):,} Bedford records")
    return pd.DataFrame(records)

# ── Step 1b: Lynchburg City ────────────────────────────────────────────────────

def download_lynchburg(days):
    cutoff     = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    records, offset = [], 0
    print("📥 Lynchburg City...")
    while True:
        resp = requests.get(LYNCHBURG_API, params={
            "where": f"Sale1dt >= date '{cutoff_str}'",
            "outFields": "Parcel_ID,LocAddr,LocCity,LocZip,Owner1,Owner2,MailAddr,MailCity,MailStat,MailZip,Sale1dt,Sale1Amt,Grantor1,FinSize,YrBuilt",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            break
        for feat in features:
            a = feat["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(feat.get("geometry"))
            a["SOURCE"] = "Lynchburg"
            ts = a.get("Sale1dt")
            if ts:
                a["SALE_DATE_STR"] = datetime.fromtimestamp(ts / 1000).strftime("%m/%d/%Y")
            else:
                a["SALE_DATE_STR"] = ""
            # Use property address as fallback if no mailing address
            if not a.get("MailCity"):
                a["MailCity"] = a.get("LocCity", "")
            if not a.get("MailZip"):
                a["MailZip"] = a.get("LocZip", "")
            records.append(a)
        print(f"   {len(records)} so far…")
        if len(features) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    print(f"   ✅ {len(records):,} Lynchburg records")
    return pd.DataFrame(records)

# ── Step 1c: Campbell County ──────────────────────────────────────────────────

def download_campbell(days):
    cutoff     = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    records, offset = [], 0
    print("📥 Campbell County...")
    while True:
        resp = requests.get(CAMPBELL_API, params={
            "where": f"SALE1D >= date '{cutoff_str}'",
            "outFields": "NAME1,STRTNUM,STRTNAME,STRTCITY,STRTZIP,SALE1D,SALE1AMT,GRANTOR1",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            break
        for feat in features:
            a = feat["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(feat.get("geometry"))
            a["SOURCE"] = "Campbell"
            # Normalize to match Bedford/Lynchburg field names
            street = f"{a.get('STRTNUM', '')} {a.get('STRTNAME', '')}".strip()
            a["Owner1"]       = a.get("NAME1", "")
            a["LocAddr"]      = street
            a["MailCity"]     = a.get("STRTCITY", "")
            a["MailZip"]      = a.get("STRTZIP", "")
            a["Sale1Amt"]     = a.get("SALE1AMT", "")
            a["Grantor1"]     = a.get("GRANTOR1", "")
            # SALE1D comes back as Unix ms timestamp from this layer
            ts = a.get("SALE1D")
            if ts and isinstance(ts, (int, float)):
                a["SALE_DATE_STR"] = datetime.fromtimestamp(ts / 1000).strftime("%m/%d/%Y")
            else:
                a["SALE_DATE_STR"] = str(ts or "")
            records.append(a)
        print(f"   {len(records)} so far…")
        if len(features) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    print(f"   ✅ {len(records):,} Campbell records")
    return pd.DataFrame(records)

# ── Step 2: Precise date filter ────────────────────────────────────────────────

def filter_recent_sales(df, days):
    print(f"\n🔍 Filtering to sales within last {days} days...")
    cutoff = datetime.now() - timedelta(days=days)

    def parse_date(s):
        s = str(s).strip()
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
        return None

    df["_sale_dt"] = df["SALE_DATE_STR"].apply(parse_date)
    recent = df[df["_sale_dt"] >= cutoff].copy()
    print(f"   ✅ {len(recent):,} sales in the last {days} days")
    return recent

# ── Step 3: Distance filter ────────────────────────────────────────────────────

def filter_by_distance(df, miles):
    print(f"\n📏 Filtering to {miles} miles from OIC...")
    valid = df.dropna(subset=["LAT", "LON"]).copy()

    def dist(row):
        try:
            return geodesic((OIC_LAT, OIC_LON), (row["LAT"], row["LON"])).miles
        except Exception:
            return None

    valid["DISTANCE_MILES"] = valid.apply(dist, axis=1)
    nearby = valid[valid["DISTANCE_MILES"] <= miles].copy()
    nearby = nearby.sort_values("DISTANCE_MILES")
    print(f"   ✅ {len(nearby):,} properties within {miles} miles of OIC")
    return nearby

# ── Step 4a: Chinese/Taiwanese surname filter ──────────────────────────────────

# Covers Pinyin (mainland), Wade-Giles (Taiwan), and Cantonese romanizations.
# Intentionally broad — review output for false positives (e.g. HO, LO, LEE
# can also be non-Chinese). Excludes clearly non-Chinese compounds like CHONG.
CHINESE_TAIWANESE_SURNAMES = {
    # Pinyin (mainland)
    "BAI", "CAI", "CAO", "CHEN", "CHENG", "CUI", "DENG", "DING", "DONG",
    "FAN", "FANG", "FENG", "GAO", "GONG", "GUO", "HAN", "HE", "HOU",
    "HU", "HUANG", "JIANG", "JIN", "KONG", "LI", "LIANG", "LIN", "LIU",
    "LU", "LUO", "MA", "MEI", "MO", "PAN", "PENG", "QIAN",
    "SHAO", "SHEN", "SHI", "SONG", "SU", "SUN", "TANG", "TAO", "WANG",
    "WEI", "WEN", "WU", "XIAO", "XIE", "XU", "XUE", "YAN", "YANG",
    "YAO", "YE", "YU", "ZENG", "ZHANG", "ZHAO", "ZHENG", "ZHOU", "ZHU",
    # Wade-Giles / Taiwanese romanizations
    "CHANG",   # 張/章
    "CHAO",    # 趙
    "CHIANG",  # 蔣
    "CHIEN",   # 錢
    "CHIN",    # 金
    "CHIU",    # 邱
    "CHOU",    # 周
    "CHU",     # 朱
    "HO",      # 何
    "HSIAO",   # 蕭
    "HSIEH",   # 謝
    "HSU",     # 許
    "HSIA",    # 夏
    "KAO",     # 高
    "KUO",     # 郭
    "LAI",     # 賴
    "LO",      # 羅
    "SUNG",    # 宋
    "TENG",    # 鄧
    "TSAI",    # 蔡
    "TSAO",    # 曹
    "TSENG",   # 曾
    "TSUI",    # 崔
    "TUNG",    # 董
    "WONG",    # 黃/王 (Cantonese)
    "YEH",     # 葉
    # Cantonese romanizations
    "CHEUNG",  # 張/鄭
    "KWOK",    # 郭
    "KWONG",   # 鄺
    "LEUNG",   # 梁
    "NG",      # 吳/伍
}

CHINESE_HOUSEHOLDS_FILE     = "chinese_households_near_oic.csv"
CHINESE_FULLNAME_FILE       = "chinese_fullname_households.csv"

# ── Name parsing helpers ───────────────────────────────────────────────────────

# Skip tokens that are titles/suffixes/conjunctions, not given names
_SKIP_TOKENS = {"TRS", "TR", "JR", "SR", "II", "III", "IV", "LLC", "INC",
                "AND", "&", "ET", "AL", "CO", "MR", "MRS", "DR", "REV"}

def _parse_owners(raw):
    """
    Return list of (surname, given_name) tuples from a raw Owner1 string.
    Handles both formats:
      Lynchburg:       "SURNAME, FIRSTNAME [& SURNAME2, FIRSTNAME2]"
      Bedford/Campbell:"SURNAME FIRSTNAME  [& SURNAME2 FIRSTNAME2]"
    """
    if not isinstance(raw, str):
        return []
    results = []
    # Split on & or AND to get individual owners
    parts = [p.strip() for p in raw.replace(" AND ", " & ").split("&")]
    for part in parts:
        part = part.strip().rstrip(".")
        if not part:
            continue
        if "," in part:
            # Lynchburg: "SURNAME, FIRSTNAME..."
            chunks = [c.strip() for c in part.split(",", 1)]
            surname = chunks[0].strip()
            given   = chunks[1].strip() if len(chunks) > 1 else ""
        else:
            # Bedford/Campbell: "SURNAME FIRSTNAME..."
            tokens = part.split()
            if not tokens:
                continue
            surname = tokens[0]
            given   = " ".join(tokens[1:])
        # Strip trailing suffixes from given name
        given_tokens = [t for t in given.split() if t.upper() not in _SKIP_TOKENS]
        given = " ".join(given_tokens).strip(".")
        if surname:
            results.append((surname.upper(), given.upper()))
    return results


def _surname_is_chinese(surname):
    return surname.upper() in CHINESE_TAIWANESE_SURNAMES


# English given-name blocklist — if given name is purely one of these it's
# almost certainly not a Chinese name even if the surname is.
_ENGLISH_NAMES = {
    "WILLIAM", "JAMES", "JOHN", "ROBERT", "MICHAEL", "DAVID", "JOSEPH",
    "THOMAS", "CHARLES", "CHRISTOPHER", "DANIEL", "MATTHEW", "ANDREW",
    "JOSHUA", "RYAN", "KEVIN", "BRIAN", "ERIC", "JASON", "JEFFREY",
    "TIMOTHY", "GARY", "STEPHEN", "MARK", "PAUL", "GEORGE", "DONALD",
    "KENNETH", "LARRY", "FRANK", "SCOTT", "RAYMOND", "JERRY", "DENNIS",
    "WALTER", "PATRICK", "PETER", "HAROLD", "DOUGLAS", "HENRY", "CARL",
    "ARTHUR", "ROGER", "RALPH", "WAYNE", "ROY", "LOUIS", "PHILLIP",
    "ALBERT", "JOHNNY", "BILLY", "BOBBY", "JIMMY", "TOMMY",
    "MARY", "PATRICIA", "LINDA", "BARBARA", "ELIZABETH", "JENNIFER",
    "MARIA", "SUSAN", "MARGARET", "DOROTHY", "LISA", "NANCY", "KAREN",
    "BETTY", "HELEN", "SANDRA", "DONNA", "CAROL", "RUTH", "SHARON",
    "MICHELLE", "LAURA", "SARAH", "KIMBERLY", "DEBORAH", "JESSICA",
    "SHIRLEY", "CYNTHIA", "ANGELA", "MELISSA", "BRENDA", "AMY",
    "ANNA", "VIRGINIA", "REBECCA", "KATHLEEN", "PAMELA", "MARTHA",
    "DEBRA", "AMANDA", "STEPHANIE", "CAROLYN", "DIANE", "JANET",
    "ALICE", "JULIE", "HEATHER", "TERESA", "DORIS", "GLORIA",
    "EVELYN", "JEAN", "CHERYL", "MILDRED", "KATHERINE", "JOAN",
    "ASHLEY", "JUDITH", "ROSE", "JANICE", "KELLY", "NICOLE",
    "JUDY", "CHRISTINA", "KATHY", "THERESA", "BEVERLY", "DENISE",
    "TAMMY", "IRENE", "JANE", "LORI", "RACHEL", "MARILYN", "ANDREA",
    # Common English first names that might appear with Chinese surnames
    "WENDY", "MANDY", "CINDY", "SANDY", "DIANA", "EMILY", "GRACE",
    "HENRY", "VICTOR", "ERIC", "ALBERT", "EDWARD", "FREDRICK",
    "THEODORE", "BENJAMIN", "AUSTIN", "TREVOR", "HUNTER", "TYLER",
    "JUSTIN", "TRAVIS", "BRANDON", "DEREK", "KYLE", "MITCHELL",
    "JAIMYN", "MARCUS", "OLIVER", "KANE", "KORTNI", "KAYLA", "KELLY",
    "KEISHA", "LAROSE", "JOSIAH", "JAMIE", "JAMIE", "JAMIE",
    "DANA", "DENIZ", "ANNE", "GARY", "KESHA",
}

def _given_name_looks_chinese(given):
    """
    Heuristic: given name looks Chinese if it's non-empty, not a known English
    name, and doesn't contain purely Western-looking tokens.
    Falls back gracefully — NameSor gives a more reliable answer.
    """
    if not given:
        return False
    tokens = given.upper().split()
    # If every token is a known English name, it's not Chinese
    if all(t in _ENGLISH_NAMES for t in tokens if t not in _SKIP_TOKENS):
        return False
    # Single-letter middle initials (e.g. "LOUIS W") don't make it non-English
    meaningful = [t for t in tokens if len(t) > 1 and t not in _SKIP_TOKENS]
    if not meaningful:
        return False
    if all(t in _ENGLISH_NAMES for t in meaningful):
        return False
    return True


_ENTITY_SUFFIXES = {"LLC", "INC", "CORP", "LTD", "LP", "LLP", "TRUST",
                    "TRS", "TR", "REVOCABLE", "IRREVOCABLE", "FAMILY",
                    "PROPERTIES", "INVESTMENTS", "HOLDINGS", "VENTURES",
                    "MANAGEMENT", "REALTY", "GROUP", "FUND", "FOUNDATION"}

def _is_entity(raw):
    if not isinstance(raw, str):
        return False
    tokens = set(raw.upper().split())
    return bool(tokens & _ENTITY_SUFFIXES)


def _has_chinese_fullname(raw):
    """Return True if at least one owner in raw has both a Chinese surname
    and a given name that doesn't look purely English, and the record is
    not a corporate entity or trust."""
    if _is_entity(raw):
        return False
    for surname, given in _parse_owners(raw):
        if _surname_is_chinese(surname) and _given_name_looks_chinese(given):
            return True
    return False

# ── NameSor API (optional, more accurate given-name check) ────────────────────

NAMSOR_API_KEY = ""   # set via --namsor-key CLI arg or NAMSOR_API_KEY env var

def _namsor_chinese_score(surname, given):
    """
    Call NameSor chineseNameMatch endpoint.
    Returns score 0–1 (higher = more likely Chinese romanization), or None on error.
    Docs: https://namsor.app/documentation/#chineseNameMatch
    """
    if not NAMSOR_API_KEY:
        return None
    try:
        url = (f"https://v2.namsor.com/NamSorAPIv2/api2/json/"
               f"chineseNameMatch/{requests.utils.quote(surname)}/"
               f"{requests.utils.quote(given)}")
        r = requests.get(url, headers={"X-API-KEY": NAMSOR_API_KEY}, timeout=10)
        r.raise_for_status()
        return r.json().get("score", None)
    except Exception:
        return None


def _namsor_is_chinese(surname, given, threshold=0.5):
    score = _namsor_chinese_score(surname, given)
    if score is None:
        return _given_name_looks_chinese(given)   # fallback to heuristic
    return score >= threshold


# ── Export functions ───────────────────────────────────────────────────────────

def export_chinese_taiwanese(df):
    """Step 4a — surname-only filter, deduped by address (keep latest sale)."""
    def surname_is_chinese(owner):
        if not isinstance(owner, str):
            return False
        parts = owner.strip().split(",")[0].strip().split()
        if not parts:
            return False
        return parts[0].upper() in CHINESE_TAIWANESE_SURNAMES

    matches = df[df["Owner1"].apply(surname_is_chinese)].copy()

    # Dedup by address, keep latest sale
    matches["_sale_dt"] = pd.to_datetime(matches["Sale1D"], errors="coerce")
    matches = (matches.sort_values("_sale_dt", ascending=False)
                      .drop_duplicates(subset=["LocAddr"], keep="first")
                      .drop(columns=["_sale_dt"])
                      .sort_values("DISTANCE_MILES"))

    matches.to_csv(CHINESE_HOUSEHOLDS_FILE, index=False)
    print(f"\n🏠 Chinese/Taiwanese households (surname filter, deduped): "
          f"{len(matches):,} → {CHINESE_HOUSEHOLDS_FILE}")
    for src, grp in matches.groupby("SOURCE"):
        print(f"      {src}: {len(grp):,}")
    return matches


def export_chinese_fullname(df):
    """Step 4b — both surname AND given name must look Chinese, deduped."""
    matches = df[df["Owner1"].apply(_has_chinese_fullname)].copy()

    # Dedup by address, keep latest sale
    matches["_sale_dt"] = pd.to_datetime(matches["Sale1D"], errors="coerce")
    matches = (matches.sort_values("_sale_dt", ascending=False)
                      .drop_duplicates(subset=["LocAddr"], keep="first")
                      .drop(columns=["_sale_dt"])
                      .sort_values("DISTANCE_MILES"))

    matches.to_csv(CHINESE_FULLNAME_FILE, index=False)
    print(f"\n🏠 Chinese/Taiwanese households (full-name filter, deduped): "
          f"{len(matches):,} → {CHINESE_FULLNAME_FILE}")
    for src, grp in matches.groupby("SOURCE"):
        print(f"      {src}: {len(grp):,}")
    return matches

# ── Step 4: Export ─────────────────────────────────────────────────────────────

def export_results(df):
    print(f"\n💾 Exporting results...")
    keep = ["DISTANCE_MILES", "LAT", "LON", "SOURCE",
            "PIN", "Owner1", "Owner2", "LocAddr", "MailAddr", "MailCity", "MailStat", "MailZip",
            "SALE_DATE_STR", "Sale1Amt", "Grantor1", "FinSize", "YrBuilt"]
    keep = [c for c in keep if c in df.columns]
    result = df[keep].copy()
    result = result.rename(columns={"SALE_DATE_STR": "Sale1D"})
    result["VISITED"] = ""
    result["DATE_VISITED"] = ""
    result["NOTES"] = ""
    result["INTERESTED"] = ""
    result["DISTANCE_MILES"] = result["DISTANCE_MILES"].round(2)
    result.to_csv(OUTPUT_FILE, index=False)
    print(f"   ✅ Saved to: {OUTPUT_FILE}")
    print(f"   📋 {len(result):,} new homeowners to visit")
    # Breakdown by source
    for src, grp in result.groupby("SOURCE"):
        print(f"      {src}: {len(grp):,}")
    return result

# ── Step 5: Generate map ───────────────────────────────────────────────────────

def generate_map(df, miles):
    print(f"\n🗺️  Generating map...")

    def color_for_dist(d):
        if d <= 1.0:   return "#e74c3c"
        elif d <= 2.0: return "#e67e22"
        else:           return "#3498db"

    markers_js = []
    for _, row in df.iterrows():
        lat, lon = row.get("LAT"), row.get("LON")
        if lat is None or lon is None:
            continue
        owner  = str(row.get("Owner1", "")).strip() or "Unknown Owner"
        addr   = str(row.get("LocAddr", "")).strip() or "Address not listed"
        sold   = str(row.get("Sale1D", "")).strip()
        amt    = row.get("Sale1Amt", "")
        dist   = row.get("DISTANCE_MILES", "")
        source = str(row.get("SOURCE", ""))
        amt_str = f"${int(float(amt)):,}" if amt and str(amt).strip() not in ("", "0", "None") else "N/A"
        color   = color_for_dist(float(dist)) if dist != "" else "#3498db"
        info = (
            f"<div style='font-family:Arial;font-size:13px;line-height:1.6'>"
            f"<b>{owner}</b><br>{addr}<br>"
            f"Sold: {sold} &nbsp;|&nbsp; Price: {amt_str}<br>"
            f"Distance: {dist} mi &nbsp;|&nbsp; <i>{source}</i></div>"
        )
        markers_js.append(f"addPin({lat},{lon},{repr(color)},{repr(info)});")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>OIC New Homeowner Outreach Map</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ margin:0; font-family: Arial, sans-serif; }}
  #map {{ height: 100vh; width: 100%; }}
  #legend {{
    position: absolute; bottom: 40px; right: 12px; z-index: 5;
    background: white; padding: 12px 16px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3); font-size: 13px;
    line-height: 2;
  }}
  .dot {{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:6px; vertical-align:middle; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="legend">
  <b>OIC Outreach &ndash; {len(df)} homes</b><br>
  <span class="dot" style="background:#e74c3c"></span> &lt; 1 mile<br>
  <span class="dot" style="background:#e67e22"></span> 1&ndash;2 miles<br>
  <span class="dot" style="background:#3498db"></span> &gt; 2 miles<br>
  <span style="font-size:16px;margin-right:4px">⛪</span> OIC Church
</div>
<script>
var map, infoWindow;

function initMap() {{
  map = new google.maps.Map(document.getElementById('map'), {{
    center: {{ lat: {OIC_LAT}, lng: {OIC_LON} }},
    zoom: 12,
    mapTypeId: 'roadmap'
  }});
  infoWindow = new google.maps.InfoWindow();

  new google.maps.Circle({{
    map: map,
    center: {{ lat: {OIC_LAT}, lng: {OIC_LON} }},
    radius: {miles * 1609.34:.0f},
    strokeColor: '#888', strokeOpacity: 0.6, strokeWeight: 1.5,
    fillColor: '#888', fillOpacity: 0.04
  }});

  var churchMarker = new google.maps.Marker({{
    position: {{ lat: {OIC_LAT}, lng: {OIC_LON} }},
    map: map,
    title: 'One In Christ Church (OIC)',
    icon: {{
      url: 'https://maps.google.com/mapfiles/ms/icons/green-dot.png',
      scaledSize: new google.maps.Size(48, 48),
      anchor: new google.maps.Point(24, 48)
    }},
    zIndex: 999
  }});
  churchMarker.addListener('click', function() {{
    infoWindow.setContent('<div style="font-family:Arial;font-size:13px"><b>One In Christ Church (OIC)</b><br>1595 Turkey Foot Rd, Forest VA 24551</div>');
    infoWindow.open(map, churchMarker);
  }});
  infoWindow.setContent('<div style="font-family:Arial;font-size:13px"><b>One In Christ Church (OIC)</b><br>1595 Turkey Foot Rd, Forest VA 24551</div>');
  infoWindow.open(map, churchMarker);

  {''.join(chr(10) + '  ' + m for m in markers_js)}
}}

function addPin(lat, lng, color, html) {{
  var marker = new google.maps.Marker({{
    position: {{ lat: lat, lng: lng }},
    map: map,
    icon: {{
      path: google.maps.SymbolPath.CIRCLE,
      scale: 7,
      fillColor: color, fillOpacity: 0.9,
      strokeColor: '#fff', strokeWeight: 1.5
    }}
  }});
  marker.addListener('click', function() {{
    infoWindow.setContent(html);
    infoWindow.open(map, marker);
  }});
}}
</script>
<script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap" async defer></script>
</body>
</html>"""

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   ✅ Map saved to: {MAP_FILE}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    args  = parse_args()
    days  = args.days
    miles = args.miles

    print("=" * 60)
    print("  OIC New Homeowner Outreach Finder")
    print(f"  Church: 1595 Turkey Foot Rd, Forest VA")
    print(f"  Sources: Bedford County + Lynchburg City + Campbell County")
    print(f"  Radius: {miles} miles | Last {days} days")
    print("=" * 60)

    bedford    = download_bedford(days)
    lynchburg  = download_lynchburg(days)
    campbell   = download_campbell(days)
    df = pd.concat([bedford, lynchburg, campbell], ignore_index=True)
    print(f"\n   Combined: {len(df):,} records total")

    df     = filter_recent_sales(df, days)
    df     = filter_by_distance(df, miles)
    global NAMSOR_API_KEY
    NAMSOR_API_KEY = args.namsor_key

    result = export_results(df)
    export_chinese_taiwanese(result)
    export_chinese_fullname(result)
    generate_map(result, miles)

    print("\n🎉 Done!")
    print(f"   📄 CSV:  {OUTPUT_FILE}")
    print(f"   🗺️   Map:  {MAP_FILE}  ← open in browser")
    if len(result) > 0:
        print("\nSample (first 5 rows):")
        cols = ["DISTANCE_MILES", "SOURCE", "Owner1", "LocAddr", "Sale1D"]
        cols = [c for c in cols if c in result.columns]
        print(result[cols].head().to_string(index=False))
    print("\n📌 Click any pin on the map for owner name, address, and sale info.")

if __name__ == "__main__":
    main()
