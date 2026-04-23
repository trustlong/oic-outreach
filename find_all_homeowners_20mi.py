"""
Full homeowner download — all ethnicities, 20-mile radius, 1 year, all 5 counties.
Enriches with surgeo ethnicity, household size, and move origin.
Splits into per-ethnicity CSV layers.

Usage:
  python find_all_homeowners_20mi.py
"""

import os, re
import requests
import pandas as pd
from geopy.distance import geodesic
from datetime import datetime, timedelta
from surgeo import SurnameModel

OIC_LAT      = 37.3244
OIC_LON      = -79.2885
RADIUS_MILES = 20.0
DAYS         = 365
BATCH_SIZE   = 1000
OUTPUT_FILE  = "all_homeowners_20mi.csv"
LAYERS_DIR   = "layers_20mi"

BEDFORD_API    = "https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/6/query"
LYNCHBURG_API  = "https://mapviewer.lynchburgva.gov/ArcGIS/rest/services/OpenData/ODPDynamic/MapServer/41/query"
CAMPBELL_API   = "https://gis.co.campbell.va.us/arcgis/rest/services/CommunityDevelopment/AssessorLG/MapServer/38/query"
AMHERST_API    = "https://services8.arcgis.com/TvqqWejphpVuqRec/arcgis/rest/services/Amherst_WL_P/FeatureServer/30/query"
APPOMATTOX_API = "https://services6.arcgis.com/wnL4os9xzGCi48td/arcgis/rest/services/Appomattox_WL_D/FeatureServer/12/query"

# ── Helpers ────────────────────────────────────────────────────────────────────

def centroid_of_rings(geometry):
    if not geometry or "rings" not in geometry:
        return None, None
    ring = geometry["rings"][0]
    return sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring)

def dist_miles(lat, lon):
    try:
        return geodesic((OIC_LAT, OIC_LON), (lat, lon)).miles
    except Exception:
        return None

def parse_date(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(str(s).strip(), fmt)
        except: pass
    return None

def parse_city_state(addr2):
    s = str(addr2 or "").strip()
    m = re.search(r'\b([A-Z]{2})\b\s*\d{0,5}[-]?\d{0,4}\s*$', s)
    if m:
        return s[:m.start()].strip().rstrip(',').strip(), m.group(1)
    return s, ""

# ── Downloads ──────────────────────────────────────────────────────────────────

def download_bedford(cutoff_str, years):
    where = " OR ".join(f"Sale1D LIKE '%{y}'" for y in years)
    records, offset = [], 0
    print("📥 Bedford County...")
    while True:
        r = requests.get(BEDFORD_API, params={
            "where": where,
            "outFields": "PIN,LocAddr,Owner1,MailAddr,MailCity,MailStat,MailZip,Sale1D,Sale1Amt",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        feats = r.json().get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"]       = "Bedford"
            a["SALE_DATE_STR"]= a.get("Sale1D", "")
            a["MailStat_src"] = a.get("MailStat", "") or ""
            a["MailCity_src"] = a.get("MailCity", "") or ""
            a["MailAddr_src"] = a.get("MailAddr", "") or ""
            a["SalePrice"]    = float(a.get("Sale1Amt") or 0)
            a["FinSqft"]      = None
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,}")
    return pd.DataFrame(records)

def download_lynchburg(cutoff_str):
    records, offset = [], 0
    print("📥 Lynchburg City...")
    while True:
        r = requests.get(LYNCHBURG_API, params={
            "where": f"Sale1dt >= date '{cutoff_str}'",
            "outFields": "LocAddr,Owner1,MailAddr,MailCity,MailStat,MailZip,Sale1dt,Sale1Amt,FinSize",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        feats = r.json().get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"] = "Lynchburg"
            ts = a.get("Sale1dt")
            a["SALE_DATE_STR"] = datetime.fromtimestamp(ts / 1000).strftime("%m/%d/%Y") if ts else ""
            a["MailStat_src"]  = a.get("MailStat", "") or ""
            a["MailCity_src"]  = a.get("MailCity", "") or ""
            a["MailAddr_src"]  = a.get("MailAddr", "") or ""
            a["SalePrice"]     = float(a.get("Sale1Amt") or 0)
            a["FinSqft"]       = a.get("FinSize")
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,}")
    return pd.DataFrame(records)

def download_campbell(cutoff_str):
    records, offset = [], 0
    print("📥 Campbell County...")
    while True:
        r = requests.get(CAMPBELL_API, params={
            "where": f"SALE1D >= date '{cutoff_str}'",
            "outFields": "NAME1,STRTNUM,STRTNAME,STRTCITY,STRTZIP,SALE1D,SALE1AMT",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        feats = r.json().get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"]       = "Campbell"
            a["Owner1"]       = a.get("NAME1", "")
            a["LocAddr"]      = f"{a.get('STRTNUM','')} {a.get('STRTNAME','')}".strip()
            ts = a.get("SALE1D")
            a["SALE_DATE_STR"] = datetime.fromtimestamp(ts/1000).strftime("%m/%d/%Y") if isinstance(ts,(int,float)) else str(ts or "")
            a["MailStat_src"] = ""
            a["MailCity_src"] = a.get("STRTCITY", "")
            a["MailAddr_src"] = ""
            a["SalePrice"]    = float(a.get("SALE1AMT") or 0)
            a["FinSqft"]      = None
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,}")
    return pd.DataFrame(records)

def download_amherst(cutoff_str):
    records, offset = [], 0
    print("📥 Amherst County...")
    while True:
        r = requests.get(AMHERST_API, params={
            "where": f"RecordedDate >= DATE '{cutoff_str}'",
            "outFields": "MLNAM,ParcelAddress1,OwnerAddress1,OwnerAddress2,MSELLP,RecordedDate,CNS_AREA_LIVING",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        data = r.json()
        if "error" in data: print(f"   ⚠️  {data['error']}"); break
        feats = data.get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"]  = "Amherst"
            a["Owner1"]  = a.get("MLNAM", "") or ""
            a["LocAddr"] = a.get("ParcelAddress1", "") or ""
            ts = a.get("RecordedDate")
            a["SALE_DATE_STR"] = datetime.fromtimestamp(ts/1000).strftime("%m/%d/%Y") if ts else ""
            city, state = parse_city_state(a.get("OwnerAddress2", ""))
            a["MailCity_src"] = city
            a["MailStat_src"] = state
            a["MailAddr_src"] = a.get("OwnerAddress1", "") or ""
            a["SalePrice"]    = float(a.get("MSELLP") or 0)
            a["FinSqft"]      = a.get("CNS_AREA_LIVING")
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,}")
    return pd.DataFrame(records)

def download_appomattox(cutoff_str):
    records, offset = [], 0
    print("📥 Appomattox County...")
    while True:
        r = requests.get(APPOMATTOX_API, params={
            "where": f"AMCDAT >= DATE '{cutoff_str}' AND Owner1 IS NOT NULL",
            "outFields": "Owner1,ParcelAddress1,OwnerAddress1,OwnerAddress2,AMCAMT,AMCDAT",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        data = r.json()
        if "error" in data: print(f"   ⚠️  {data['error']}"); break
        feats = data.get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"]  = "Appomattox"
            a["LocAddr"] = a.get("ParcelAddress1", "") or ""
            ts = a.get("AMCDAT")
            a["SALE_DATE_STR"] = datetime.fromtimestamp(ts/1000).strftime("%m/%d/%Y") if ts else ""
            city, state = parse_city_state(a.get("OwnerAddress2", ""))
            a["MailCity_src"] = city
            a["MailStat_src"] = state
            a["MailAddr_src"] = a.get("OwnerAddress1", "") or ""
            try: a["SalePrice"] = float(a.get("AMCAMT") or 0)
            except: a["SalePrice"] = 0
            a["FinSqft"] = None
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,}")
    return pd.DataFrame(records)

# ── Enrichment ─────────────────────────────────────────────────────────────────

LOCAL_CITIES = {
    "FOREST","LYNCHBURG","BEDFORD","MONETA","HUDDLESTON","GOODE","GOODVIEW",
    "THAXTON","EVINGTON","RUSTBURG","MONROE","CONCORD","AMHERST","MADISON HEIGHTS",
    "APPOMATTOX","BLUE RIDGE","MONTVALE","BIG ISLAND","HARDY","VINTON",
    "TIMBERLAKE","GLASS","LYNCH STATION","LOWRY","PITTSVILLE","BROOKNEAL",
    "GLADSTONE","PAMPLIN","SPOUT SPRING","COLEMAN FALLS","CLIFFORD",
}

ENTITY_RE = re.compile(
    r"\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRS|PROPERTIES|HOLDINGS|REALTY|"
    r"GROUP|FUND|FOUNDATION|SERIES|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS)\b",
    re.IGNORECASE,
)

def classify_origin(mailstat, mailcity, mailaddr, locaddr):
    norm = lambda s: re.sub(r'[^a-z0-9]', '', str(s).lower().strip()) if s else ''
    if norm(mailaddr) and norm(mailaddr) == norm(locaddr):
        return "Unknown (mailing updated)"
    if not mailstat:
        return "Unknown (no mail data)"
    state = str(mailstat).strip().upper()
    city  = str(mailcity).strip().upper()
    if state != "VA":
        return f"Out-of-state ({state})"
    if city in LOCAL_CITIES:
        return "Local"
    return "In-state (VA)"

SQFT_BRACKETS = [(1000,1.8),(1500,2.3),(2000,2.7),(2500,3.0),(3000,3.2),(3500,3.4),(4000,3.5),(float('inf'),3.4)]

def estimate_hh(sqft, price):
    if sqft and float(sqft) > 0:
        sq = float(sqft)
        for ceiling, size in SQFT_BRACKETS:
            if sq <= ceiling: return int(round(size)), f"sqft={int(sq)}"
        return 3, f"sqft={int(sq)}"
    p = float(price) if price else 0
    if p == 0:       return 2, "non-market"
    if p < 100000:   return 2, f"price=${int(p):,}"
    if p < 200000:   return 2, f"price=${int(p):,}"
    if p < 300000:   return 3, f"price=${int(p):,}"
    if p < 400000:   return 3, f"price=${int(p):,}"
    if p < 500000:   return 3, f"price=${int(p):,}"
    if p < 750000:   return 3, f"price=${int(p):,}"
    return 3, f"price=${int(p):,}"

RACE_MAP = {"white":"White","black":"Black","api":"Asian/PI","native":"Am.Indian","multiple":"Multiracial","hispanic":"Hispanic"}
RACE_COLS = list(RACE_MAP.keys())

def add_ethnicity(df):
    def get_surname(o):
        if not isinstance(o, str) or not o.strip(): return ""
        raw = o.strip()
        tok = raw.split(',')[0].strip().upper().split() if ',' in raw else raw.split()
        return tok[0].upper() if tok else ""

    surnames = df["Owner1"].apply(get_surname)
    model = SurnameModel()
    probs = model.get_probabilities(surnames)
    has_data = probs[RACE_COLS].notna().any(axis=1)

    eth, conf = [], []
    for i in range(len(df)):
        if has_data.iloc[i]:
            row = probs.iloc[i]
            top = row[RACE_COLS].idxmax()
            eth.append(RACE_MAP[top])
            conf.append(round(float(row[top]), 3))
        else:
            eth.append("Unknown")
            conf.append(None)

    df["ESTIMATED_ETHNICITY"]  = eth
    df["ETHNICITY_CONFIDENCE"] = conf
    return df

# ── Split into layers ──────────────────────────────────────────────────────────

def split_layers(df):
    os.makedirs(LAYERS_DIR, exist_ok=True)
    ethnicities = df["ESTIMATED_ETHNICITY"].unique()
    print(f"\n📂 Splitting into {LAYERS_DIR}/")
    for eth in sorted(ethnicities):
        grp = df[df["ESTIMATED_ETHNICITY"] == eth].copy()
        fname = eth.lower().replace("/","_").replace(" ","_").replace(".","")
        path = f"{LAYERS_DIR}/{fname}.csv"
        grp.to_csv(path, index=False)
        print(f"   {path}: {len(grp):,} rows")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    cutoff     = datetime.now() - timedelta(days=DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    years      = range(cutoff.year, datetime.now().year + 1)

    print("=" * 60)
    print("  OIC All Homeowners — 20-Mile Radius, 1 Year, 5 Counties")
    print(f"  Cutoff: {cutoff_str}  |  Radius: {RADIUS_MILES} miles")
    print("=" * 60)

    df = pd.concat([
        download_bedford(cutoff_str, years),
        download_lynchburg(cutoff_str),
        download_campbell(cutoff_str),
        download_amherst(cutoff_str),
        download_appomattox(cutoff_str),
    ], ignore_index=True)
    print(f"\n   Combined: {len(df):,} total")

    # Date filter
    df["_dt"] = df["SALE_DATE_STR"].apply(parse_date)
    df = df[df["_dt"] >= cutoff].copy()
    print(f"   After date filter: {len(df):,}")

    # Distance filter
    df = df.dropna(subset=["LAT","LON"]).copy()
    df["DISTANCE_MILES"] = df.apply(lambda r: dist_miles(r["LAT"], r["LON"]), axis=1)
    df = df[df["DISTANCE_MILES"] <= RADIUS_MILES].copy()
    print(f"   Within {RADIUS_MILES} miles: {len(df):,}")

    # Move origin
    df["MOVE_ORIGIN"] = df.apply(
        lambda r: classify_origin(r["MailStat_src"], r["MailCity_src"], r["MailAddr_src"], r.get("LocAddr","")), axis=1
    )

    # Non-local filter
    df = df[~df["MOVE_ORIGIN"].isin(["Local"])].copy()
    print(f"   Non-local movers: {len(df):,}")

    # Household size
    hh = df.apply(lambda r: estimate_hh(r.get("FinSqft"), r.get("SalePrice")), axis=1)
    df["EST_HOUSEHOLD_SIZE"] = hh.apply(lambda x: x[0])
    df["HH_SIZE_BASIS"]      = hh.apply(lambda x: x[1])

    # Ethnicity
    print("\n🔬 Running surgeo ethnicity estimation...")
    df = add_ethnicity(df)

    # Clean up columns
    keep = ["DISTANCE_MILES","LAT","LON","SOURCE","Owner1","LocAddr",
            "SALE_DATE_STR","SalePrice","MOVE_ORIGIN",
            "ESTIMATED_ETHNICITY","ETHNICITY_CONFIDENCE",
            "EST_HOUSEHOLD_SIZE","HH_SIZE_BASIS",
            "MailCity_src","MailStat_src"]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].rename(columns={"SALE_DATE_STR":"Sale1D","MailCity_src":"MailCity","MailStat_src":"MailStat"})
    df["DISTANCE_MILES"] = df["DISTANCE_MILES"].round(2)
    df["VISITED"] = ""
    df["NOTES"]   = ""
    df = df.sort_values("DISTANCE_MILES")

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Saved {len(df):,} records → {OUTPUT_FILE}")

    print("\n📊 Ethnicity breakdown:")
    for eth, grp in df.groupby("ESTIMATED_ETHNICITY"):
        print(f"   {eth:<15} {len(grp):>5}")

    print("\n📊 Move origin breakdown:")
    for orig, grp in df.groupby("MOVE_ORIGIN"):
        print(f"   {orig:<40} {len(grp):>5}")

    split_layers(df)
    print("\n🎉 Done!")

if __name__ == "__main__":
    main()
