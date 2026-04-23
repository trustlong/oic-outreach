# OIC New Homeowner Outreach – Project Notes

## What This Does

Finds new homeowners near One In Christ Church (OIC) using public GIS data across 5 counties,
generates enriched CSVs for door-knocking and a Google Maps HTML file for visualization.

Each record is enriched with:
- **Estimated ethnicity** — US Census 2010 surname lookup
- **Estimated household size** — finished sqft (Lynchburg) or sale price brackets (others), ACS-calibrated
- **Christian likelihood** — Pew Research priors by ethnicity/subgroup + Muslim/Hindu name flags
- **Move origin** — prior mailing address vs. property address (local / in-state / out-of-state / unknown)

**Church:** 1595 Turkey Foot Rd, Forest, VA 24551 (37.3244, -79.2885)

---

## How to Run

### Standard outreach run (5-mile radius, 180 days)

```bash
source .venv/bin/activate

# Step 1: download + filter
python find_new_homeowners_oic.py --days 180 --miles 5

# Step 2: enrich (run in order)
python add_ethnicity.py
python add_household_size.py
python add_christian_likelihood.py
python add_move_origin.py

# Step 3: export non-local movers only
python export_non_local_movers.py
```

**Outputs:**
- `new_homeowners_near_oic.csv` — all 817 properties, fully enriched
- `new_homeowners_near_oic_map.html` — Google Maps with color-coded pins
- `non_local_movers_near_oic.csv` — confirmed non-local families only (no LLCs, no local movers)

### Asian-focused wide search (20-mile radius, 1 year, all 5 counties)

```bash
source .venv/bin/activate
python find_asian_homeowners_20mi.py
```

**Output:** `asian_homeowners_20mi.csv` — all Asian-surname households, enriched with origin + household size

---

## Data Sources

### Bedford County ✅ Working
- **API:** `https://webgis.bedfordcountyva.gov/arcgis/rest/services/OpenData/OpenDataProperty/MapServer/6/query`
- **Layer:** Parcels (Bedford County + Town of Bedford) — polygon geometry
- **Key fields:** `PIN`, `Owner1`, `LocAddr`, `MailAddr`, `MailCity`, `MailStat`, `MailZip`, `Sale1D` (string MM/DD/YYYY), `Sale1Amt`
- **Date filter:** `Sale1D LIKE '%2025' OR Sale1D LIKE '%2026'` (string field — year suffix only, precise cutoff in Python)
- **Move origin:** join on `PIN` (not LocAddr — many parcels have null address) to `bedford_with_mailstat.csv`; flag records where `MailAddr == LocAddr` as "Unknown (mailing updated)"
- **Notes:** Sale1D is a string, not a date. GeoAnalyst_2025_Reassess service has same parcel data but no sqft.

### Lynchburg City ✅ Working
- **API:** `https://mapviewer.lynchburgva.gov/ArcGIS/rest/services/OpenData/ODPDynamic/MapServer/41/query`
- **Layer:** Parcel (layer 41)
- **Key fields:** `Owner1`, `LocAddr`, `MailAddr`, `MailCity`, `MailStat`, `MailZip`, `Sale1dt` (Unix ms), `Sale1Amt`, `FinSize` (finished sqft), `YrBuilt`
- **Date filter:** `Sale1dt >= date 'YYYY-MM-DD'`
- **Notes:** `FinSize` is the best sqft source in the dataset. `MailStat` available and used for origin detection.

### Campbell County ✅ Working (partially)
- **API:** `https://gis.co.campbell.va.us/arcgis/rest/services/CommunityDevelopment/AssessorLG/MapServer/38/query`
- **Key fields:** `NAME1` (owner), `STRTNUM`, `STRTNAME`, `STRTCITY`, `STRTZIP`, `SALE1D`, `SALE1AMT`
- **Date filter:** `SALE1D >= date 'YYYY-MM-DD'`
- **Limitation:** No `MailAddr` or `MailStat` — only property address exposed. Move origin cannot be determined (all "Unknown (no mail data)").
- **Notes:** Returns recent sales. Earlier notes said this was broken — it now works as of 2025.

### Amherst County ✅ Working (discovered via Chrome DevTools)
- **API:** `https://services8.arcgis.com/TvqqWejphpVuqRec/arcgis/rest/services/Amherst_WL_P/FeatureServer/30/query`
- **Portal:** `https://experience.arcgis.com/experience/45d7ce9ea48c44cdb1e35afc94aa62e9` (Amherst MapInsights — Timmons Group)
- **Key fields:** `MLNAM` (full owner name), `ParcelAddress1`, `OwnerAddress1`, `OwnerAddress2` (format: "CITY ST ZIP"), `MSELLP` (sale price), `RecordedDate` (esriFieldTypeDate), `CNS_AREA_LIVING` (sqft), `M_BR` (bedrooms)
- **Date filter:** `RecordedDate >= DATE 'YYYY-MM-DD' AND MSELLP > 0`
- **Notes:** `OwnerAddress2` contains city+state+zip as one string ("STAUNTON VA 24401") — parse with regex to extract state. `amherstgis.timmons.com` DNS no longer resolves; use ArcGIS Experience URL instead.

### Appomattox County ✅ Working (discovered via Chrome DevTools)
- **API:** `https://services6.arcgis.com/wnL4os9xzGCi48td/arcgis/rest/services/Appomattox_WL_D/FeatureServer/12/query`
- **Portal:** `https://experience.arcgis.com/experience/dc7e850b09a64019a04398dadaba2729` (Appomattox MapInsights — Timmons Group)
- **Key fields:** `Owner1`, `ParcelAddress1`, `OwnerAddress1`, `OwnerAddress2` (format: "CITY ST ZIP"), `AMCAMT` (sale price, string), `AMCDAT` (sale date, esriFieldTypeDate), `AMINYR` (sale year)
- **Date filter:** `AMCDAT >= DATE 'YYYY-MM-DD' AND Owner1 IS NOT NULL`
- **Notes:** `AMCAMT` is a string — cast to float. `appomattoxgis.timmons.com` DNS no longer resolves; use ArcGIS Experience URL. No sqft field available.

---

## Enrichment Scripts

| Script | Input | What it adds |
|---|---|---|
| `add_ethnicity.py` | `new_homeowners_near_oic.csv` + `Names_2010Census.csv` | `ESTIMATED_ETHNICITY`, pct columns |
| `add_household_size.py` | above | `EST_HOUSEHOLD_SIZE`, `HH_SIZE_CONFIDENCE`, `HH_SIZE_BASIS` |
| `add_christian_likelihood.py` | above | `CHRISTIAN_PROB`, `RELIGION_NOTES` |
| `add_move_origin.py` | above + `bedford_with_mailstat.csv` | `MOVE_ORIGIN`, `MOVE_ORIGIN_NOTES` |
| `export_non_local_movers.py` | above | `non_local_movers_near_oic.csv` |

---

## Map Details

- Uses **Google Maps JavaScript API** (key stored in script — rotate if sharing publicly)
- Pins color-coded by distance: red < 1 mi, orange 1–2 mi, blue > 2 mi
- Church shown as green marker, circle = search radius
- Click any pin for owner name, address, sale date, price, distance, and source county

---

## Diversity Snapshot (180 days, 5-mile radius, 817 properties — April 2026)

| Group | Count |
|---|---|
| White | 506 (62%) |
| Black | 31 (4%) |
| Hispanic | 16 (2%) |
| Asian/PI | 16 (2%) |
| Unknown (no surname match) | 247 (30%) |

**20-mile radius, 1 year, Asian-only search:** 88 Asian households across 5 counties.
**Chinese specifically (non-local, full-name verified):** 10 households → `chinese_nonlocal_20mi.csv`

---

## Known Limitations

- **Household size is systematically underestimated for large families.** ACS averages don't capture immigrant families with 4+ children. Validated against owner's actual household (estimated 3.1, actual 6).
- **Move origin is unreliable when mailing address has been updated** to the new home. Bedford: 62/279 records already updated. Campbell: no mailing address at all.
- **Chinese Christian probability (22% national) is too low for this area.** Chinese families near OIC self-select toward Christian community. Local prior is likely much higher.
- **"LEE" as Chinese surname is ambiguous** — also Korean/Western. Check given names (e.g., "You-Wen", "Mu-Tien" = Taiwanese romanization) to confirm.
- **CAO TAM THANH** — Cao is Chinese but "Tam Thanh" is Vietnamese. May not be Chinese.
- Sale amounts of $0 are family/estate transfers, not market purchases.
- Parcel centroids approximated by averaging polygon ring vertices — not exact lot centers.
- Data refreshed from GIS on each script run — no local cache.

---

## Contact for Data Issues

**Campbell County** (if API breaks again):
- Real Estate dept: **434-332-9568**
- Commissioner of the Revenue: **434-332-9518**
- Mailing: 47 Courthouse Lane, Suite 1, Rustburg, VA 24588

**Amherst / Appomattox** (if ArcGIS Online URLs change):
- Both hosted by Timmons Group on ArcGIS Online (org: `timmons-group.maps.arcgis.com`)
- Find updated URLs by opening the Experience portals in Chrome and checking Network tab for `FeatureServer` requests
