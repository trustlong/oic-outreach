"""
Monthly Top-10 Outreach Prioritizer for OIC.

Scoring:
  Ethnicity:  Asian/PI=3, Hispanic/Black=2, other=1
  Origin:     Out-of-state=2, In-state/Unknown=1
  Distance:   ≤5 mi=2, 5–10 mi=1, >10 mi=0
  Recency:    Sold in past 30 days=1

Usage:
  python top10_this_month.py
"""

import re
import pandas as pd
from datetime import datetime, timedelta

INPUT_FILE  = "all_homeowners_20mi.csv"
OUTPUT_FILE = "top10_outreach.csv"

ENTITY_RE = re.compile(
    r"\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRS|PROPERTIES|HOLDINGS|REALTY|"
    r"GROUP|FUND|FOUNDATION|SERIES|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS|"
    r"VENTURES|CAPITAL|INVESTMENTS|ESTATE|MORTGAGE|TITLE|ABSTRACT)\b",
    re.IGNORECASE,
)

def parse_date(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(str(s).strip(), fmt)
        except: pass
    return None

def score_row(row, cutoff_30):
    eth = str(row.get("ESTIMATED_ETHNICITY", ""))
    origin = str(row.get("MOVE_ORIGIN", ""))
    dist = float(row.get("DISTANCE_MILES", 99))
    dt = row.get("_dt")

    eth_score = {"Asian/PI": 3, "Hispanic": 2, "Black": 2}.get(eth, 1)
    ori_score = 2 if origin.startswith("Out-of-state") else 1
    dis_score = 2 if dist <= 5 else (1 if dist <= 10 else 0)
    rec_score = 1 if dt and dt >= cutoff_30 else 0

    return eth_score + ori_score + dis_score + rec_score

def main():
    df = pd.read_csv(INPUT_FILE, dtype=str)
    df["_dt"] = df["Sale1D"].apply(parse_date)
    df = df[df["_dt"].notna()].copy()
    df = df[~df["Owner1"].apply(lambda x: bool(ENTITY_RE.search(str(x))))].copy()
    df = df[~df["MOVE_ORIGIN"].isin(["Local"])].copy()

    cutoff_30 = datetime.now() - timedelta(days=30)
    df["SCORE"] = df.apply(lambda r: score_row(r, cutoff_30), axis=1)

    top10 = (df.sort_values(["SCORE", "DISTANCE_MILES"], ascending=[False, True])
               .head(10)
               .drop(columns=["_dt"]))

    keep = ["SCORE", "DISTANCE_MILES", "LAT", "LON", "SOURCE",
            "Owner1", "LocAddr", "Sale1D", "SalePrice",
            "ESTIMATED_ETHNICITY", "MOVE_ORIGIN", "MOVE_ORIGIN_NOTES",
            "EST_HOUSEHOLD_SIZE", "VISITED", "NOTES"]
    keep = [c for c in keep if c in top10.columns]
    top10 = top10[keep]
    top10.to_csv(OUTPUT_FILE, index=False)

    print(f"📋 Top 10 Outreach — {datetime.now().strftime('%B %Y')}\n")
    print(top10[["SCORE","DISTANCE_MILES","SOURCE","Owner1","LocAddr",
                 "Sale1D","ESTIMATED_ETHNICITY","MOVE_ORIGIN"]].to_string(index=False))
    print(f"\n✅ Saved → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
