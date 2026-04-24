"""
Bulk surname-based ethnicity estimation using surgeo BISG (Bayesian Improved
Surname Geocoding) — more accurate than raw Census surname lookup alone.

Adds ESTIMATED_ETHNICITY, ETHNICITY_CONFIDENCE, and pct columns to the CSV.
"""

import pandas as pd
from surgeo import SurnameModel

INPUT_FILE  = "new_homeowners_near_oic.csv"
OUTPUT_FILE = "new_homeowners_near_oic.csv"

RACE_MAP = {
    "white":    "White",
    "black":    "Black",
    "api":      "Asian/PI",
    "native":   "Am.Indian",
    "multiple": "Multiracial",
    "hispanic": "Hispanic",
}
RACE_COLS = list(RACE_MAP.keys())


def extract_surname(owner1):
    if not isinstance(owner1, str) or not owner1.strip():
        return ""
    raw = owner1.strip()
    if "," in raw:
        parts = raw.split(",")[0].strip().upper().split()
        return parts[0] if parts else ""
    return raw.split()[0].upper() if raw.split() else ""


def main():
    df = pd.read_csv(INPUT_FILE, dtype=str)
    df["_surname"] = df["Owner1"].apply(extract_surname)

    model = SurnameModel()
    probs = model.get_probabilities(df["_surname"])

    has_data = probs[RACE_COLS].notna().any(axis=1)

    ethnicity     = []
    confidence    = []
    pct_asian     = []
    pct_white     = []
    pct_black     = []
    pct_hispanic  = []

    for i in range(len(df)):
        if has_data.iloc[i]:
            row = probs.iloc[i]
            top_race = row[RACE_COLS].idxmax()
            ethnicity.append(RACE_MAP[top_race])
            confidence.append(round(float(row[top_race]), 3))
            pct_asian.append(round(float(row["api"]) * 100, 1))
            pct_white.append(round(float(row["white"]) * 100, 1))
            pct_black.append(round(float(row["black"]) * 100, 1))
            pct_hispanic.append(round(float(row["hispanic"]) * 100, 1))
        else:
            ethnicity.append("Unknown")
            confidence.append(None)
            pct_asian.append(0.0)
            pct_white.append(0.0)
            pct_black.append(0.0)
            pct_hispanic.append(0.0)

    df["ESTIMATED_ETHNICITY"]  = ethnicity
    df["ETHNICITY_CONFIDENCE"] = confidence
    df["PCT_ASIAN_PI"]         = pct_asian
    df["PCT_WHITE"]            = pct_white
    df["PCT_BLACK"]            = pct_black
    df["PCT_HISPANIC"]         = pct_hispanic
    df = df.drop(columns=["_surname"])

    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\n📊 Ethnicity Estimates (surgeo BISG) — {len(df)} properties\n")
    counts = df["ESTIMATED_ETHNICITY"].value_counts()
    for eth, n in counts.items():
        pct = 100 * n / len(df)
        print(f"   {eth:<15} {n:>4}  ({pct:.1f}%)")

    asian = df[df["PCT_ASIAN_PI"].astype(float) > 80]
    print(f"\n🏠 High-confidence Asian/PI (>80%): {len(asian)}")
    print(f"\n✅ Updated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
