"""
Estimate household size using finished sqft when available (Lynchburg only),
falling back to sale price for Bedford and Campbell.

Sqft brackets — ACS B25021/B25030, Virginia calibration:
  < 1,000      → 1.8
  1,000–1,499  → 2.3
  1,500–1,999  → 2.7
  2,000–2,499  → 3.0
  2,500–2,999  → 3.2
  3,000–3,499  → 3.4
  3,500–3,999  → 3.5
  4,000+       → 3.4  (luxury/empty-nester trend down)

Price brackets (fallback) — ACS B25119, Bedford/Campbell area:
  $0 (non-market transfer) → 2.4, Low confidence
  < $100K      → 1.9
  $100K–$200K  → 2.3
  $200K–$300K  → 2.6
  $300K–$400K  → 2.9
  $400K–$500K  → 3.1
  $500K–$750K  → 3.2
  > $750K      → 2.9

Note: both models underestimate large families (4+ children). They reflect
population averages and individual variance is high.
"""

import pandas as pd

INPUT_FILE  = "new_homeowners_near_oic.csv"
OUTPUT_FILE = "new_homeowners_near_oic.csv"

SQFT_BRACKETS = [
    (1000, 1.8),
    (1500, 2.3),
    (2000, 2.7),
    (2500, 3.0),
    (3000, 3.2),
    (3500, 3.4),
    (4000, 3.5),
    (float("inf"), 3.4),
]

PRICE_BRACKETS = [
    (0,           2.4, "Low"),
    (100_000,     1.9, "Med"),
    (200_000,     2.3, "Med"),
    (300_000,     2.6, "High"),
    (400_000,     2.9, "High"),
    (500_000,     3.1, "High"),
    (750_000,     3.2, "Med"),
    (float("inf"), 2.9, "Med"),
]


def from_sqft(sqft):
    for ceiling, size in SQFT_BRACKETS:
        if sqft <= ceiling:
            return size, "High", f"sqft={int(sqft)}"
    return 3.4, "High", f"sqft={int(sqft)}"


def from_price(sale_amt):
    if sale_amt == 0:
        return 2.4, "Low", "non-market transfer"
    for ceiling, size, conf in PRICE_BRACKETS[1:]:
        if sale_amt <= ceiling:
            return size, conf, f"price=${int(sale_amt):,}"
    return 2.9, "Med", f"price=${int(sale_amt):,}"


def estimate(row):
    sqft = pd.to_numeric(row.get("FinSize", None), errors="coerce")
    if pd.notna(sqft) and sqft > 0:
        return from_sqft(sqft)
    amt = pd.to_numeric(row.get("Sale1Amt", 0), errors="coerce") or 0
    return from_price(amt)


def main():
    df = pd.read_csv(INPUT_FILE, dtype=str)

    results = df.apply(estimate, axis=1)
    df["EST_HOUSEHOLD_SIZE"] = results.apply(lambda x: x[0])
    df["HH_SIZE_CONFIDENCE"]  = results.apply(lambda x: x[1])
    df["HH_SIZE_BASIS"]       = results.apply(lambda x: x[2])

    df.to_csv(OUTPUT_FILE, index=False)

    sqft_count  = df["HH_SIZE_BASIS"].str.startswith("sqft").sum()
    price_count = df["HH_SIZE_BASIS"].str.startswith("price").sum()
    xfer_count  = (df["HH_SIZE_BASIS"] == "non-market transfer").sum()

    print(f"\n📐 Household Size Estimates — {len(df)} properties")
    print(f"   Based on sqft:  {sqft_count} (Lynchburg)")
    print(f"   Based on price: {price_count}")
    print(f"   Non-market:     {xfer_count}")
    print()
    print(f"   {'Size':<8} {'Count':>6}")
    print(f"   {'-'*16}")
    for size, grp in df.groupby("EST_HOUSEHOLD_SIZE"):
        print(f"   {size:<8} {len(grp):>6}")
    print(f"\n✅ Updated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
