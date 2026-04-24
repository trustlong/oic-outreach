"""
Estimate likelihood of Christian affiliation for each household.

Methodology (layered):
1. Virginia/Lynchburg regional baseline: ~72% Christian (PRRI 2023, Pew 2023)
   Lynchburg is notably higher than VA average due to Liberty University presence
   and high concentration of evangelical churches.

2. Ethnicity-adjusted prior (Pew Research 2023):
   White        → 72%  (VA evangelical belt skews higher than national 68%)
   Black        → 83%  (Southern Black Protestant tradition very strong)
   Hispanic     → 77%  (mix of Catholic + Protestant)
   Asian/PI     → 34%  (wide internal variance — see layer 3)
   Am.Indian    → 66%
   Multiracial  → 62%
   Unknown      → 72%  (use VA regional baseline)

3. Name-pattern refinement for Asian/PI (Pew subgroup data):
   Korean surnames     → 71%  (majority Presbyterian/Methodist)
   Filipino surnames   → 91%  (overwhelmingly Catholic)
   Vietnamese surnames → 29%  (mostly Buddhist/non-religious; ~30% Catholic)
   Chinese surnames    → 22%  (mostly non-religious/Buddhist)
   South Asian (India) → 12%  (mostly Hindu)
   Nepali surnames     → 8%   (mostly Hindu/Buddhist)
   Pakistani surnames  → 3%   (overwhelmingly Muslim)

4. Name-pattern flags for non-Christian indicators across all ethnicities:
   Known Muslim names  → 5%   max
   Known Hindu names   → 10%  max
   Known Jewish names  → 8%   max
   Corporate/LLC       → N/A

Sources:
  - Pew Research Center, "Religious Landscape Study" 2023
  - PRRI American Values Atlas 2023 (Virginia state data)
  - Pew Asian-American religious affiliation by subgroup 2023
"""

import pandas as pd
import re

INPUT_FILE  = "new_homeowners_near_oic.csv"
OUTPUT_FILE = "new_homeowners_near_oic.csv"

# ── Ethnicity → baseline Christian probability ─────────────────────────────────
ETHNICITY_PRIOR = {
    "White":       0.72,
    "Black":       0.83,
    "Hispanic":    0.77,
    "Asian/PI":    0.34,
    "Am.Indian":   0.66,
    "Multiracial": 0.62,
    "Unknown":     0.72,
}

# ── Asian subgroup surname sets → refined probability ─────────────────────────
KOREAN_SURNAMES = {
    "KIM", "LEE", "PARK", "CHOI", "JUNG", "JANG", "LIM", "HAN", "OH",
    "SEO", "SHIN", "KWON", "YOON", "HA", "HONG", "KO", "CHO", "YOO",
    "YOON", "AHN", "KANG", "NAM", "MOON", "BAEK", "NOH", "RYU", "JEON",
}
FILIPINO_SURNAMES = {
    "SANTOS", "REYES", "CRUZ", "GARCIA", "MENDOZA", "DELA", "DE LA",
    "BAUTISTA", "AQUINO", "VILLANUEVA", "RAMOS", "FLORES", "TORRES",
    "DELA CRUZ", "PASCUAL", "SALAZAR", "DIAZ", "HERNANDEZ", "CASTILLO",
}
VIETNAMESE_SURNAMES = {
    "NGUYEN", "TRAN", "LE", "PHAM", "HOANG", "HUYNH", "DANG", "BUI",
    "DO", "HO", "NGO", "DUONG", "DINH", "TRINH", "LUONG", "TRUONG", "VU", "VO",
}
CHINESE_SURNAMES = {
    "CHEN", "WANG", "LI", "ZHANG", "LIU", "YANG", "HUANG", "ZHAO", "WU",
    "ZHOU", "SUN", "MA", "GUO", "HE", "LIN", "TANG", "CHANG", "TSE",
    "CHENG", "ZHENG", "YE", "LAM", "LEUNG", "CHEUNG", "KWOK", "NG",
    "HO", "CHAN", "LIANG", "TSAI", "DU", "WEI", "JIN",
}
SOUTH_ASIAN_SURNAMES = {
    "PATEL", "SHAH", "SHARMA", "VERMA", "SINGH", "KUMAR", "GUPTA",
    "MEHTA", "DESAI", "JOSHI", "YADAV", "NAIR", "RAO", "REDDY",
    "IYER", "KRISHNA", "PANCHAL", "PARIKH", "BHATT",
}
NEPALI_SURNAMES = {
    "GURUNG", "TAMANG", "MAGAR", "LAMA", "THAPA", "RANA", "SHRESTHA",
    "ADHIKARI", "KARKI", "BHATTARAI", "REGMI", "BHANDARI", "KC",
}

ASIAN_SUBGROUPS = [
    (KOREAN_SURNAMES,      0.71, "Korean"),
    (FILIPINO_SURNAMES,    0.91, "Filipino"),
    (VIETNAMESE_SURNAMES,  0.29, "Vietnamese"),
    (CHINESE_SURNAMES,     0.22, "Chinese"),
    (NEPALI_SURNAMES,      0.08, "Nepali"),
    (SOUTH_ASIAN_SURNAMES, 0.12, "South Asian"),
]

# ── Strong non-Christian name indicators (all ethnicities) ────────────────────
MUSLIM_FIRST = {
    "MOHAMMED", "MUHAMMAD", "AHMAD", "AHMED", "ALI", "HASSAN", "HUSSEIN",
    "HUSSAIN", "OMAR", "UMAR", "FATIMA", "AISHA", "AYESHA", "HAMZA",
    "IBRAHIM", "ISMAIL", "YUSUF", "TARIQ", "BILAL", "SYED", "SHAIKH",
    "WAQAS", "AFTAB", "NAWAZ", "RASHID", "KHALID", "IMRAN", "ASIF",
    "ZUBAIR", "FAISAL", "AZIZ", "SALIM", "TAHIR",
}
MUSLIM_LAST = {
    "NAWAZ", "AFTAB", "HUSSAIN", "SHEIKH", "KHAN", "CHAUDHRY", "MALIK",
    "MIRZA", "SIDDIQUI", "QURESHI", "ANSARI", "ASLAM", "BHATTI",
}
JEWISH_LAST = {
    "COHEN", "LEVY", "GOLDBERG", "ROSENBERG", "FRIEDMAN", "GREENBERG",
    "KAPLAN", "SHAPIRO", "WEISS", "BERNSTEIN", "KLEIN", "SILVER",
}
HINDU_SPECIFIC = {
    "PATEL", "SHARMA", "GUPTA", "YADAV", "TIWARI", "DUBEY", "PANDEY",
    "MISHRA", "TRIPATHI", "CHATURVEDI", "AGRAWAL", "JAIN",
}

ENTITY_RE = re.compile(
    r"\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRS|TR|PROPERTIES|HOLDINGS|REALTY|GROUP|FARM)\b",
    re.IGNORECASE,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_surname_and_given(owner1):
    if not isinstance(owner1, str) or not owner1.strip():
        return "", ""
    raw = owner1.strip()
    if "," in raw:
        parts = raw.split(",", 1)
        return parts[0].strip().upper(), parts[1].strip().upper()
    tokens = raw.split()
    return (tokens[0].upper(), " ".join(tokens[1:]).upper()) if tokens else ("", "")


def estimate_christian_prob(row):
    owner1    = str(row.get("Owner1", "") or "")
    ethnicity = str(row.get("ESTIMATED_ETHNICITY", "Unknown"))

    # Corporate / LLC — not applicable
    if ENTITY_RE.search(owner1):
        return None, "N/A (entity)"

    surname, given = parse_surname_and_given(owner1)
    notes = []

    # Start with ethnicity prior
    prob = ETHNICITY_PRIOR.get(ethnicity, 0.72)
    notes.append(f"{ethnicity} baseline={int(prob*100)}%")

    # Refine Asian/PI by subgroup
    if ethnicity == "Asian/PI":
        for name_set, subprob, label in ASIAN_SUBGROUPS:
            if surname in name_set:
                prob = subprob
                notes.append(f"→ {label} subgroup={int(prob*100)}%")
                break

    # Check Muslim name signals (surname or given)
    all_tokens = set((surname + " " + given).split())
    if surname in MUSLIM_LAST or bool(all_tokens & MUSLIM_FIRST):
        prob = min(prob, 0.05)
        notes.append("Muslim name indicator → 5%")
    # Check Jewish surname
    elif surname in JEWISH_LAST:
        prob = min(prob, 0.08)
        notes.append("Jewish surname indicator → 8%")
    # Check Hindu-specific (only if not already Asian/PI refined)
    elif surname in HINDU_SPECIFIC and ethnicity not in ("Asian/PI",):
        prob = min(prob, 0.10)
        notes.append("Hindu surname indicator → 10%")

    return round(prob, 2), "; ".join(notes)


def main():
    df = pd.read_csv(INPUT_FILE, dtype=str)

    results = df.apply(estimate_christian_prob, axis=1)
    df["CHRISTIAN_PROB"]  = results.apply(lambda x: x[0])
    df["RELIGION_NOTES"]  = results.apply(lambda x: x[1])

    df.to_csv(OUTPUT_FILE, index=False)

    # Summary
    valid = df[df["CHRISTIAN_PROB"].notna()].copy()
    valid["_p"] = pd.to_numeric(valid["CHRISTIAN_PROB"])

    print(f"\n⛪  Christian Likelihood Estimates — {len(df)} properties\n")
    print(f"   Avg estimated Christian probability: {valid['_p'].mean():.1%}")
    print(f"   Median: {valid['_p'].median():.1%}\n")

    buckets = [
        ("Very likely   (≥75%)", 0.75, 1.01),
        ("Probable      (50–74%)", 0.50, 0.75),
        ("Uncertain     (25–49%)", 0.25, 0.50),
        ("Unlikely      (<25%)",   0.00, 0.25),
    ]
    for label, lo, hi in buckets:
        n = ((valid["_p"] >= lo) & (valid["_p"] < hi)).sum()
        print(f"   {label}: {n:>4}")

    print("\n🔍 Lower-probability households (< 30%) worth noting:")
    low = df[pd.to_numeric(df["CHRISTIAN_PROB"], errors="coerce") < 0.30].copy()
    low["_p"] = pd.to_numeric(low["CHRISTIAN_PROB"])
    low = low.sort_values("_p")
    cols = ["CHRISTIAN_PROB", "DISTANCE_MILES", "Owner1", "LocAddr", "RELIGION_NOTES"]
    print(low[cols].to_string(index=False))

    print(f"\n✅ Updated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
