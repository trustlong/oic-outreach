"""
Export a clean list of non-local new homeowners (in-state + out-of-state movers)
with ethnicity, household size, and Christian likelihood estimates.

Filters:
  - Excludes local movers and unknown-origin records
  - Excludes clear corporate / investor entities (LLC, INC, CORP, bulk buyers)
  - Keeps family trusts (TR/TRS suffix = real families, not corporations)
  - Deduplicates same owner buying multiple lots — keeps closest property only
"""

import pandas as pd, re

INPUT_FILE  = "new_homeowners_near_oic.csv"
OUTPUT_FILE = "non_local_movers_near_oic.csv"

CORPORATE_RE = re.compile(
    r"\b(LLC|INC|CORP|LTD|LP|LLP|PROPERTIES|HOLDINGS|REALTY|FUND|FOUNDATION|"
    r"SERIES|PENNYMAC|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS|BUILDINGS)\b"
    r"|PROPERTY OWN",   # catches "PROPERTY OWNER" HOA-type names
    re.IGNORECASE,
)

# Numbered/anonymous trusts with no real person name (e.g. "UNA3481 TRUST")
ANON_TRUST_RE = re.compile(r"^\w*\d+\w*\s+TRUST$", re.IGNORECASE)

MUSLIM_NAMES = {
    "NAWAZ", "AFTAB", "HUSSAIN", "SHEIKH", "KHAN", "CHAUDHRY", "MALIK",
    "MIRZA", "SIDDIQUI", "QURESHI", "ANSARI", "ASLAM", "BHATTI",
    "MOHAMMED", "MUHAMMAD", "AHMAD", "AHMED", "ALI", "HASSAN", "HUSSEIN",
    "OMAR", "IBRAHIM", "ISMAIL", "YUSUF", "TARIQ", "BILAL", "WAQAS",
    "RASHID", "KHALID", "IMRAN", "ASIF", "ZUBAIR", "FAISAL",
}

KEEP_COLS = [
    "DISTANCE_MILES",
    "LAT",
    "LON",
    "SOURCE",
    "Owner1",
    "LocAddr",
    "MOVE_ORIGIN",
    "MOVE_ORIGIN_NOTES",
    "ESTIMATED_ETHNICITY",
    "EST_HOUSEHOLD_SIZE",
    "HH_SIZE_CONFIDENCE",
    "CHRISTIAN_PROB",
    "Sale1D",
    "Sale1Amt",
    "VISITED",
    "DATE_VISITED",
    "NOTES",
    "INTERESTED",
]


def main():
    df = pd.read_csv(INPUT_FILE, dtype=str)

    # 1. Non-local movers only
    non_local = df[df["MOVE_ORIGIN"].str.startswith(("In-state", "Out-of-state"))].copy()

    # 2. Remove corporate / investor entities; keep named family trusts
    def is_excluded(name):
        s = str(name)
        if CORPORATE_RE.search(s):
            return True
        if ANON_TRUST_RE.match(s.strip()):  # e.g. "UNA3481 TRUST"
            return True
        return False
    individuals = non_local[~non_local["Owner1"].apply(is_excluded)].copy()

    # Fix CHRISTIAN_PROB for rows that were wrongly marked N/A (entity) due to TR suffix
    def fix_christian_prob(row):
        prob = row["CHRISTIAN_PROB"]
        if pd.notna(prob) and str(prob) not in ("", "nan", "None"):
            return prob
        tokens = set(str(row.get("Owner1", "")).upper().split())
        if tokens & MUSLIM_NAMES:
            return "0.05"
        eth = str(row.get("ESTIMATED_ETHNICITY", "Unknown"))
        defaults = {"White": "0.72", "Black": "0.83", "Hispanic": "0.77",
                    "Asian/PI": "0.34", "Am.Indian": "0.66"}
        return defaults.get(eth, "0.72")
    individuals["CHRISTIAN_PROB"] = individuals.apply(fix_christian_prob, axis=1)

    # 3. Deduplicate: same owner → keep the one closest to OIC
    individuals["_dist"] = pd.to_numeric(individuals["DISTANCE_MILES"], errors="coerce")
    individuals = (individuals
                   .sort_values("_dist")
                   .drop_duplicates(subset=["Owner1"], keep="first")
                   .drop(columns=["_dist"]))

    # 4. Sort: out-of-state first (highest priority), then in-state; within each by distance
    def origin_rank(o):
        if o.startswith("Out-of-state"):
            return 0
        return 1
    individuals["_rank"] = individuals["MOVE_ORIGIN"].apply(origin_rank)
    individuals = individuals.sort_values(["_rank", "DISTANCE_MILES"]).drop(columns=["_rank"])

    # 5. Keep only useful columns
    out_cols = [c for c in KEEP_COLS if c in individuals.columns]
    result = individuals[out_cols].copy()

    result.to_csv(OUTPUT_FILE, index=False)

    # ── Print summary ──────────────────────────────────────────────────────────
    total = len(result)
    oos   = result[result["MOVE_ORIGIN"].str.startswith("Out-of-state")]
    ins   = result[result["MOVE_ORIGIN"].str.startswith("In-state")]

    print(f"\n📋 Non-Local Movers Export — {OUTPUT_FILE}")
    print(f"   Total households: {total}")
    print(f"   Out-of-state:     {len(oos)}")
    print(f"   In-state VA:      {len(ins)}")
    print()
    print(result[[
        "DISTANCE_MILES", "SOURCE", "Owner1",
        "MOVE_ORIGIN", "ESTIMATED_ETHNICITY",
        "EST_HOUSEHOLD_SIZE", "CHRISTIAN_PROB"
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
