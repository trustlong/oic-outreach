"""
Asian New Homeowner Finder — 20-mile radius from OIC, past 365 days, all 5 counties.

Sources:
  Bedford County   — webgis.bedfordcountyva.gov  (existing)
  Lynchburg City   — mapviewer.lynchburgva.gov   (existing)
  Campbell County  — gis.co.campbell.va.us        (existing)
  Amherst County   — services8.arcgis.com/TvqqWejphpVuqRec (new, via Chrome DevTools)
  Appomattox County— services6.arcgis.com/wnL4os9xzGCi48td (new, via Chrome DevTools)

Usage:
  python find_asian_homeowners_20mi.py
"""

import re
import requests
import pandas as pd
from geopy.distance import geodesic
from datetime import datetime, timedelta

OIC_LAT   = 37.3244
OIC_LON   = -79.2885
RADIUS_MILES = 20.0
DAYS         = 365
OUTPUT_FILE  = "asian_homeowners_20mi.csv"
BATCH_SIZE   = 1000

BEDFORD_API   = "https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/6/query"
LYNCHBURG_API = "https://mapviewer.lynchburgva.gov/ArcGIS/rest/services/OpenData/ODPDynamic/MapServer/41/query"
CAMPBELL_API  = "https://gis.co.campbell.va.us/arcgis/rest/services/CommunityDevelopment/AssessorLG/MapServer/38/query"
AMHERST_API   = "https://services8.arcgis.com/TvqqWejphpVuqRec/arcgis/rest/services/Amherst_WL_P/FeatureServer/30/query"
APPOMATTOX_API= "https://services6.arcgis.com/wnL4os9xzGCi48td/arcgis/rest/services/Appomattox_WL_D/FeatureServer/12/query"

# ── Geometry ───────────────────────────────────────────────────────────────────

def centroid_of_rings(geometry):
    if not geometry or "rings" not in geometry:
        return None, None
    ring = geometry["rings"][0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return sum(lats) / len(lats), sum(lons) / len(lons)

def dist_miles(lat, lon):
    try:
        return geodesic((OIC_LAT, OIC_LON), (lat, lon)).miles
    except Exception:
        return None

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
            a["SOURCE"]        = "Bedford"
            a["SALE_DATE_STR"] = a.get("Sale1D", "")
            a["Owner1"]        = a.get("Owner1", "")
            a["LocAddr_src"]   = a.get("LocAddr", "")
            a["MailStat_src"]  = a.get("MailStat", "")
            a["MailCity_src"]  = a.get("MailCity", "")
            a["MailAddr_src"]  = a.get("MailAddr", "")
            a["SalePrice"]     = a.get("Sale1Amt", 0) or 0
            a["FinSqft"]       = None
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,} Bedford records")
    return pd.DataFrame(records)


def download_lynchburg(cutoff_str):
    records, offset = [], 0
    print("📥 Lynchburg City...")
    while True:
        r = requests.get(LYNCHBURG_API, params={
            "where": f"Sale1dt >= date '{cutoff_str}'",
            "outFields": "Parcel_ID,LocAddr,Owner1,MailAddr,MailCity,MailStat,MailZip,Sale1dt,Sale1Amt,FinSize",
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
            a["LocAddr_src"]  = a.get("LocAddr", "")
            a["MailStat_src"] = a.get("MailStat", "") or ""
            a["MailCity_src"] = a.get("MailCity", "") or a.get("LocCity", "")
            a["MailAddr_src"] = a.get("MailAddr", "") or ""
            a["SalePrice"]    = a.get("Sale1Amt", 0) or 0
            a["FinSqft"]      = a.get("FinSize")
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,} Lynchburg records")
    return pd.DataFrame(records)


def download_campbell(cutoff_str):
    records, offset = [], 0
    print("📥 Campbell County...")
    while True:
        r = requests.get(CAMPBELL_API, params={
            "where": f"SALE1D >= date '{cutoff_str}'",
            "outFields": "NAME1,STRTNUM,STRTNAME,STRTCITY,STRTZIP,SALE1D,SALE1AMT,GRANTOR1",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        feats = r.json().get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"]  = "Campbell"
            a["Owner1"]  = a.get("NAME1", "")
            ts = a.get("SALE1D")
            a["SALE_DATE_STR"] = datetime.fromtimestamp(ts / 1000).strftime("%m/%d/%Y") if isinstance(ts, (int,float)) else str(ts or "")
            a["LocAddr_src"]  = f"{a.get('STRTNUM','')} {a.get('STRTNAME','')}".strip()
            a["MailStat_src"] = ""
            a["MailCity_src"] = a.get("STRTCITY", "")
            a["MailAddr_src"] = ""
            a["SalePrice"]    = a.get("SALE1AMT", 0) or 0
            a["FinSqft"]      = None
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,} Campbell records")
    return pd.DataFrame(records)


def download_amherst(cutoff_str):
    records, offset = [], 0
    print("📥 Amherst County...")
    while True:
        r = requests.get(AMHERST_API, params={
            "where": f"RecordedDate >= DATE '{cutoff_str}' AND MSELLP > 0",
            "outFields": "MLNAM,ParcelAddress1,OwnerAddress1,OwnerAddress2,MSELLP,RecordedDate,M_BR,CNS_AREA_LIVING",
            "outSR": "4326", "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE, "f": "json",
        }, timeout=60)
        data = r.json()
        if "error" in data:
            print(f"   ⚠️  Amherst error: {data['error']}")
            break
        feats = data.get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"]  = "Amherst"
            a["Owner1"]  = a.get("MLNAM", "") or ""
            ts = a.get("RecordedDate")
            a["SALE_DATE_STR"] = datetime.fromtimestamp(ts / 1000).strftime("%m/%d/%Y") if ts else ""
            a["LocAddr_src"]   = a.get("ParcelAddress1", "") or ""
            # OwnerAddress2 format: "CITY ST ZIP"
            addr2 = str(a.get("OwnerAddress2", "") or "")
            a["MailAddr_src"]  = a.get("OwnerAddress1", "") or ""
            a["MailCity_src"], a["MailStat_src"] = _parse_city_state(addr2)
            a["SalePrice"]     = a.get("MSELLP", 0) or 0
            a["FinSqft"]       = a.get("CNS_AREA_LIVING")
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,} Amherst records")
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
        if "error" in data:
            print(f"   ⚠️  Appomattox error: {data['error']}")
            break
        feats = data.get("features", [])
        if not feats: break
        for f in feats:
            a = f["attributes"]
            a["LAT"], a["LON"] = centroid_of_rings(f.get("geometry"))
            a["SOURCE"]  = "Appomattox"
            a["Owner1"]  = a.get("Owner1", "") or ""
            ts = a.get("AMCDAT")
            a["SALE_DATE_STR"] = datetime.fromtimestamp(ts / 1000).strftime("%m/%d/%Y") if ts else ""
            a["LocAddr_src"]   = a.get("ParcelAddress1", "") or ""
            addr2 = str(a.get("OwnerAddress2", "") or "")
            a["MailAddr_src"]  = a.get("OwnerAddress1", "") or ""
            a["MailCity_src"], a["MailStat_src"] = _parse_city_state(addr2)
            try:
                a["SalePrice"] = float(a.get("AMCAMT", 0) or 0)
            except Exception:
                a["SalePrice"] = 0
            a["FinSqft"] = None
            records.append(a)
        if len(feats) < BATCH_SIZE: break
        offset += BATCH_SIZE
    print(f"   ✅ {len(records):,} Appomattox records")
    return pd.DataFrame(records)


def _parse_city_state(addr2):
    """Parse 'CITY ST ZIP' or 'CITY, ST ZIP' into (city, state)."""
    s = addr2.strip()
    if not s:
        return "", ""
    # Match trailing 2-letter state abbreviation (before optional zip)
    m = re.search(r'\b([A-Z]{2})\b\s*\d{0,5}[-]?\d{0,4}\s*$', s)
    if m:
        state = m.group(1)
        city = s[:m.start()].strip().rstrip(',').strip()
        return city, state
    return s, ""

# ── Asian surname sets ─────────────────────────────────────────────────────────

ASIAN_SURNAMES = {
    # Chinese/Taiwanese
    "CHEN","WANG","LI","ZHANG","LIU","YANG","HUANG","ZHAO","WU","ZHOU","SUN",
    "MA","GUO","HE","LIN","TANG","CHANG","TSE","CHENG","ZHENG","YE","LAM",
    "LEUNG","CHEUNG","KWOK","NG","HO","CHAN","LIANG","TSAI","DU","WEI","JIN",
    "CHIANG","CHIEN","CHIN","CHIU","CHOU","CHU","HSIAO","HSIEH","HSU","HSIA",
    "KAO","KUO","LAI","LO","SUNG","TENG","TSAO","TSENG","TSUI","TUNG","WONG",
    "YEH","KWONG","CAI","CAO","CUI","DENG","DING","DONG","FAN","FANG","FENG",
    "GAO","GONG","HAN","HOU","HU","JIANG","KONG","LU","LUO","MEI","MO","PAN",
    "PENG","QIAN","SHAO","SHEN","SHI","SONG","SU","TAO","XIAO","XIE","XU",
    "XUE","YAN","YAO","ZOU","ZENG","ZHU","BAI",
    # Korean
    "KIM","LEE","PARK","CHOI","JUNG","JANG","LIM","HAN","OH","SEO","SHIN",
    "KWON","YOO","AHN","KANG","NAM","MOON","BAEK","NOH","RYU","JEON","YOON",
    # Vietnamese
    "NGUYEN","TRAN","LE","PHAM","HOANG","HUYNH","DANG","BUI","DO","NGO",
    "DUONG","DINH","TRINH","LUONG","TRUONG","VU","VO",
    # South Asian
    "PATEL","SHAH","SHARMA","VERMA","SINGH","KUMAR","GUPTA","MEHTA","DESAI",
    "JOSHI","NAIR","RAO","REDDY","IYER","KRISHNA","PANCHAL","PARIKH","BHATT",
    # Nepali
    "GURUNG","TAMANG","MAGAR","LAMA","THAPA","RANA","SHRESTHA","ADHIKARI",
    "KARKI","BHATTARAI","REGMI","BHANDARI",
    # Filipino
    "SANTOS","REYES","CRUZ","GARCIA","MENDOZA","BAUTISTA","AQUINO","VILLANUEVA",
    "RAMOS","FLORES","TORRES","PASCUAL","SALAZAR",
    # Japanese
    "TANAKA","SUZUKI","SATO","WATANABE","ITO","YAMAMOTO","NAKAMURA","KOBAYASHI",
    "KATO","YOSHIDA","YAMADA","SASAKI","MATSUMOTO","INOUE","KIMURA",
    # Pakistani/Muslim (commonly Asian-origin)
    "KHAN","MALIK","SHEIKH","NAWAZ","AFTAB","HUSSAIN","CHAUDHRY","MIRZA",
    "SIDDIQUI","QURESHI","ASLAM","BHATTI",
}

ENTITY_RE = re.compile(
    r"\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRS|TR|PROPERTIES|HOLDINGS|REALTY|"
    r"GROUP|FUND|FOUNDATION|SERIES|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS)\b",
    re.IGNORECASE,
)

def extract_surname(owner1):
    if not isinstance(owner1, str) or not owner1.strip():
        return ""
    raw = owner1.strip()
    if "," in raw:
        return raw.split(",")[0].strip().upper().split()[0] if raw.split(",")[0].strip() else ""
    parts = raw.split()
    return parts[0].upper() if parts else ""

def is_asian(owner1):
    if ENTITY_RE.search(str(owner1)):
        return False
    return extract_surname(owner1) in ASIAN_SURNAMES

# ── Move origin ────────────────────────────────────────────────────────────────

LOCAL_CITIES = {
    "FOREST","LYNCHBURG","BEDFORD","MONETA","HUDDLESTON","GOODE","GOODVIEW",
    "THAXTON","EVINGTON","RUSTBURG","MONROE","CONCORD","AMHERST","MADISON HEIGHTS",
    "APPOMATTOX","BLUE RIDGE","MONTVALE","BIG ISLAND","HARDY","VINTON",
    "TIMBERLAKE","GLASS","LYNCH STATION","LOWRY","PITTSVILLE","BROOKNEAL",
    "GLADSTONE","PAMPLIN","SPOUT SPRING","VERA","COLEMAN FALLS","CLIFFORD",
    "MADISON HEIGHTS",
}

def classify_origin(mailstat, mailcity, mailaddr, locaddr):
    norm = lambda s: re.sub(r'[^a-z0-9]', '', str(s).lower().strip()) if s else ''
    if norm(mailaddr) and norm(mailaddr) == norm(locaddr):
        return "Unknown (mailing updated)", "Mailing address matches property"
    if not mailstat:
        return "Unknown (no mail data)", ""
    state = str(mailstat).strip().upper()
    city  = str(mailcity).strip().upper()
    if state != "VA":
        return f"Out-of-state ({state})", f"Prior address: {city}, {state}"
    if city in LOCAL_CITIES:
        return "Local", f"Prior address: {city}, VA"
    return "In-state (VA)", f"Prior address: {city}, VA"

# ── Household size ─────────────────────────────────────────────────────────────

def estimate_hh_size(sqft, price):
    if sqft and float(sqft) > 0:
        sqft = float(sqft)
        for ceiling, size in [(1000,1.8),(1500,2.3),(2000,2.7),(2500,3.0),(3000,3.2),(3500,3.4),(4000,3.5)]:
            if sqft <= ceiling:
                return size, f"sqft={int(sqft)}"
        return 3.4, f"sqft={int(sqft)}"
    p = float(price) if price else 0
    if p == 0:   return 2.4, "non-market"
    if p < 100000: return 1.9, f"price=${int(p):,}"
    if p < 200000: return 2.3, f"price=${int(p):,}"
    if p < 300000: return 2.6, f"price=${int(p):,}"
    if p < 400000: return 2.9, f"price=${int(p):,}"
    if p < 500000: return 3.1, f"price=${int(p):,}"
    if p < 750000: return 3.2, f"price=${int(p):,}"
    return 2.9, f"price=${int(p):,}"

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    cutoff = datetime.now() - timedelta(days=DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    years = range(cutoff.year, datetime.now().year + 1)

    print("=" * 60)
    print("  OIC Asian Homeowner Finder — 20-Mile Radius, 1 Year")
    print(f"  Cutoff: {cutoff_str}  |  Radius: {RADIUS_MILES} miles")
    print("=" * 60)

    frames = [
        download_bedford(cutoff_str, years),
        download_lynchburg(cutoff_str),
        download_campbell(cutoff_str),
        download_amherst(cutoff_str),
        download_appomattox(cutoff_str),
    ]
    df = pd.concat(frames, ignore_index=True)
    print(f"\n   Combined: {len(df):,} total records")

    # Date filter (Bedford uses string match already; others filtered at API)
    def parse_date(s):
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try: return datetime.strptime(str(s).strip(), fmt)
            except: pass
        return None
    df["_dt"] = df["SALE_DATE_STR"].apply(parse_date)
    df = df[df["_dt"] >= cutoff].copy()
    print(f"   After date filter: {len(df):,}")

    # Distance filter
    df = df.dropna(subset=["LAT","LON"]).copy()
    df["DISTANCE_MILES"] = df.apply(lambda r: dist_miles(r["LAT"], r["LON"]), axis=1)
    df = df[df["DISTANCE_MILES"] <= RADIUS_MILES].copy()
    print(f"   Within {RADIUS_MILES} miles: {len(df):,}")

    # Asian filter
    df = df[df["Owner1"].apply(is_asian)].copy()
    print(f"   Asian surname match: {len(df):,}")

    # Remove entities
    df = df[~df["Owner1"].apply(lambda x: bool(ENTITY_RE.search(str(x))))].copy()
    print(f"   After removing entities: {len(df):,}")

    # Dedup by owner + address (keep closest)
    df = df.sort_values("DISTANCE_MILES").drop_duplicates(subset=["Owner1","LocAddr_src"], keep="first")
    print(f"   After dedup: {len(df):,}")

    # Enrich
    origin_results = df.apply(
        lambda r: classify_origin(r["MailStat_src"], r["MailCity_src"], r["MailAddr_src"], r["LocAddr_src"]), axis=1
    )
    df["MOVE_ORIGIN"]       = origin_results.apply(lambda x: x[0])
    df["MOVE_ORIGIN_NOTES"] = origin_results.apply(lambda x: x[1])

    hh = df.apply(lambda r: estimate_hh_size(r.get("FinSqft"), r.get("SalePrice")), axis=1)
    df["EST_HOUSEHOLD_SIZE"] = hh.apply(lambda x: x[0])
    df["HH_SIZE_BASIS"]      = hh.apply(lambda x: x[1])

    # Output columns
    out = df[[
        "DISTANCE_MILES","LAT","LON","SOURCE",
        "Owner1","LocAddr_src","SALE_DATE_STR","SalePrice",
        "MOVE_ORIGIN","MOVE_ORIGIN_NOTES",
        "EST_HOUSEHOLD_SIZE","HH_SIZE_BASIS",
        "MailCity_src","MailStat_src",
    ]].copy()
    out = out.rename(columns={
        "LocAddr_src":  "LocAddr",
        "MailCity_src": "MailCity",
        "MailStat_src": "MailStat",
        "SALE_DATE_STR":"Sale1D",
    })
    out["DISTANCE_MILES"] = out["DISTANCE_MILES"].round(2)
    out["VISITED"] = ""
    out["NOTES"]   = ""
    out = out.sort_values("DISTANCE_MILES")
    out.to_csv(OUTPUT_FILE, index=False)

    print(f"\n{'='*60}")
    print(f"✅  {len(out)} Asian households saved → {OUTPUT_FILE}")
    print(f"{'='*60}\n")
    print(out[["DISTANCE_MILES","SOURCE","Owner1","LocAddr","Sale1D","MOVE_ORIGIN","EST_HOUSEHOLD_SIZE"]].to_string(index=False))

    print("\n📊 By county:")
    for src, grp in out.groupby("SOURCE"):
        print(f"   {src}: {len(grp)}")
    print("\n📊 By move origin:")
    for orig, grp in out.groupby("MOVE_ORIGIN"):
        print(f"   {orig}: {len(grp)}")

if __name__ == "__main__":
    main()
