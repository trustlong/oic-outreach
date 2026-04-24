"""
Classify each new homeowner as a local, in-state, or out-of-state mover.

For Bedford County: uses MailStat + MailCity from the GIS API (true prior mailing address).
For Lynchburg/Campbell: GIS APIs only expose property address, not prior mailing address,
  so we fall back to MailZip pattern analysis + flag as lower confidence.

Local metro area = Lynchburg MSA + Bedford County lake communities (within ~35 mi):
  Forest, Lynchburg, Bedford, Moneta, Huddleston, Goode, Goodview, Thaxton,
  Evington, Rustburg, Monroe, Concord, Amherst, Madison Heights, Appomattox,
  Blue Ridge, Montvale, Big Island, Hardy, Vinton (Roanoke adjacent but close).
"""

import pandas as pd, re

MAIN_CSV      = "new_homeowners_near_oic.csv"
BEDFORD_EXTRA = "bedford_with_mailstat.csv"
OUTPUT_FILE   = "new_homeowners_near_oic.csv"

LOCAL_CITIES = {
    "FOREST", "LYNCHBURG", "BEDFORD", "MONETA", "HUDDLESTON", "GOODE",
    "GOODVIEW", "THAXTON", "EVINGTON", "RUSTBURG", "MONROE", "CONCORD",
    "AMHERST", "MADISON HEIGHTS", "APPOMATTOX", "BLUE RIDGE", "MONTVALE",
    "BIG ISLAND", "HARDY", "VINTON", "TIMBERLAKE", "GLASS", "LYNCH STATION",
    "LOWRY", "PITTSVILLE", "PERROWVILLE", "BROOKNEAL",
}

# Local VA zip codes (Bedford + Campbell + Lynchburg MSA)
LOCAL_ZIPS = {
    "24501", "24502", "24503", "24504", "24505", "24506", "24513", "24514", "24515",
    "24523", "24528", "24536", "24538", "24540", "24549", "24550", "24551", "24553",
    "24556", "24558", "24562", "24571", "24586", "24588", "24593", "24595",
    "24066", "24121", "24122", "24137", "24165", "24179", "24014",
}


def zip_root(z):
    return str(z).split("-")[0].strip() if pd.notna(z) else ""


def classify_bedford(mailstat, mailcity):
    if not mailstat or pd.isna(mailstat):
        return "Unknown", "No state on file"
    state = str(mailstat).strip().upper()
    city  = str(mailcity).strip().upper() if pd.notna(mailcity) else ""
    if state != "VA":
        return f"Out-of-state ({state})", f"Mailing address: {city}, {state}"
    if city in LOCAL_CITIES:
        return "Local", f"Prior address: {city}, VA"
    return "In-state (VA)", f"Prior address: {city}, VA"


def classify_zip_fallback(mailcity, mailzip):
    """
    Rough classification for Lynchburg/Campbell where MailCity = property city.
    These show as 'local' because we only have the property address — flag accordingly.
    """
    z = zip_root(mailzip)
    city = str(mailcity).strip().upper() if pd.notna(mailcity) else ""

    # Non-VA zips are a clear signal even in Lynchburg/Campbell data
    if z and not z.startswith("24") and len(z) == 5:
        return "Out-of-state (zip signal)", f"MailZip {z} is non-VA"

    if city and city not in LOCAL_CITIES and city not in ("", "NAN"):
        if city in {"BROOKLYN", "SMITHTOWN", "WESTBURY", "GREENSBORO",
                    "PLEASANTON", "CHESAPEAKE", "RICHMOND", "ROANOKE",
                    "CHARLOTTESVILLE", "NORFOLK", "VIRGINIA BEACH"}:
            if city in {"BROOKLYN", "SMITHTOWN", "WESTBURY"}:
                return "Out-of-state (city signal)", f"MailCity: {city}"
            return "In-state (city signal)", f"MailCity: {city}"

    # Can't tell — property address only
    return "Unknown (no prior address)", "Campbell/Lynchburg: only property address available"


def normalize_addr(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower().strip()) if s and str(s) != "nan" else ""


def main():
    main_df    = pd.read_csv(MAIN_CSV, dtype=str)
    bedford_df = pd.read_csv(BEDFORD_EXTRA, dtype=str)

    bedford_df["_loc_n"]     = bedford_df["LocAddr"].apply(normalize_addr)
    bedford_df["_mail_n"]    = bedford_df["MailAddr"].apply(normalize_addr)
    bedford_df["_addr_match"] = (
        (bedford_df["_loc_n"] == bedford_df["_mail_n"])
        & bedford_df["_loc_n"].ne("")   # null==null doesn't count
    )
    bedford_df["_pin"] = bedford_df["PIN"].apply(lambda x: str(x).strip())

    # Build PIN-keyed lookup (unique parcel ID — no collision risk)
    pin_lookup = {}
    for _, row in bedford_df.iterrows():
        pin = row["_pin"]
        if pin and pin != "nan":
            pin_lookup[pin] = (
                row.get("MailStat", ""),
                row.get("MailCity", ""),
                bool(row.get("_addr_match", False)),
            )

    origins = []
    notes   = []
    for _, row in main_df.iterrows():
        source   = str(row.get("SOURCE", "")).strip()
        pin      = str(row.get("PIN", "")).strip() if "PIN" in main_df.columns else ""
        mailcity = row.get("MailCity", "")
        mailzip  = row.get("MailZip", "")

        mailstat = str(row.get("MailStat", "") or "").strip()
        mailaddr = str(row.get("MailAddr", "") or "").strip()
        locaddr  = str(row.get("LocAddr",  "") or "").strip()

        if source == "Bedford" and pin and pin != "nan" and pin in pin_lookup:
            ms, mc, addr_match = pin_lookup[pin]
            if addr_match:
                origin = "Unknown (mailing updated to property)"
                note   = "Mailing address already changed to new home — prior location unknown"
            else:
                origin, note = classify_bedford(ms, mc)
        elif source == "Lynchburg" and mailstat:
            # Lynchburg now provides real MailStat — use it directly
            addr_match = (
                normalize_addr(mailaddr) == normalize_addr(locaddr)
                and normalize_addr(mailaddr) != ""
            )
            if addr_match:
                origin = "Unknown (mailing updated to property)"
                note   = "Mailing address already changed to new home — prior location unknown"
            else:
                origin, note = classify_bedford(mailstat, mailcity)
        else:
            origin, note = classify_zip_fallback(mailcity, mailzip)

        origins.append(origin)
        notes.append(note)

    main_df["MOVE_ORIGIN"]       = origins
    main_df["MOVE_ORIGIN_NOTES"] = notes
    main_df.to_csv(OUTPUT_FILE, index=False)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n🚚 Move Origin — {len(main_df)} properties\n")
    vc = main_df["MOVE_ORIGIN"].value_counts()
    for val, n in vc.items():
        pct = 100 * n / len(main_df)
        print(f"   {val:<40} {n:>4}  ({pct:.1f}%)")

    print("\n📍 Bedford County breakdown (high confidence):")
    bed = main_df[main_df["SOURCE"] == "Bedford"]
    vc2 = bed["MOVE_ORIGIN"].value_counts()
    for val, n in vc2.items():
        pct = 100 * n / len(bed)
        print(f"   {val:<40} {n:>4}  ({pct:.1f}%)")

    print("\n✈️  Out-of-state movers (highest outreach priority):")
    oos = main_df[main_df["MOVE_ORIGIN"].str.startswith("Out-of-state")].copy()
    oos = oos.sort_values("DISTANCE_MILES")
    cols = ["DISTANCE_MILES", "SOURCE", "Owner1", "LocAddr", "MOVE_ORIGIN_NOTES"]
    print(oos[cols].to_string(index=False))

    print(f"\n✅ Updated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
