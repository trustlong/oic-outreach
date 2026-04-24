"""
Campbell County new homeowner downloader via BatchData API.
Saves progress to CSV after every page — safe to re-run if interrupted.

Usage:
  python download_campbell.py [--days N]
"""

import argparse
import csv
import os
import time
import requests
from datetime import datetime, timedelta

TOKEN = "TAezPfMFy85zObtLGUsU4rlHTMHMaWiJdt25rIX5"
OUTPUT_FILE = "campbell_county_homeowners.csv"
PAGE_SIZE = 25

FIELDS = ["Owner1", "LocAddr", "City", "County", "State", "Zip",
          "LAT", "LON", "SALE_DATE_STR", "Sale1Amt", "SOURCE",
          "VISITED", "DATE_VISITED", "NOTES", "INTERESTED"]


def fetch_page(min_date, skip, retries=5):
    for attempt in range(retries):
        try:
            resp = requests.post(
                "https://api.batchdata.com/api/v1/property/search",
                headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
                json={
                    "searchCriteria": {
                        "address": {"county": {"equals": "Campbell"}, "state": {"equals": "VA"}},
                        "listing": {"soldDate": {"minDate": min_date}},
                    },
                    "options": {"skip": skip, "take": PAGE_SIZE, "dateFormat": "iso-date-time"},
                },
                timeout=60,
            )
            if resp.status_code == 429 or resp.status_code == 403:
                wait = 10 * (attempt + 1)
                print(f"  Rate limited ({resp.status_code}), waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("Max retries exceeded")


def parse_property(p):
    addr = p.get("address", {})
    owner = p.get("owner", {})
    listing = p.get("listing", {})
    names = owner.get("names", [])
    owner1 = names[0].get("full", "") if names else owner.get("fullName", "")
    sold_date = listing.get("soldDate", "")
    if sold_date:
        sold_date = sold_date[:10]  # trim to YYYY-MM-DD
    return {
        "Owner1": owner1,
        "LocAddr": addr.get("street", ""),
        "City": addr.get("city", ""),
        "County": addr.get("county", ""),
        "State": addr.get("state", ""),
        "Zip": addr.get("zip", ""),
        "LAT": addr.get("latitude", ""),
        "LON": addr.get("longitude", ""),
        "SALE_DATE_STR": sold_date,
        "Sale1Amt": listing.get("soldPrice", ""),
        "SOURCE": "Campbell",
        "VISITED": "", "DATE_VISITED": "", "NOTES": "", "INTERESTED": "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365 * 5, help="Days back (default: 5 years)")
    args = parser.parse_args()

    min_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    print(f"Downloading Campbell County sales since {min_date}...")

    # Check if resuming
    existing_rows = 0
    file_exists = os.path.exists(OUTPUT_FILE)
    if file_exists:
        with open(OUTPUT_FILE) as f:
            existing_rows = sum(1 for _ in f) - 1  # minus header
        print(f"Resuming — {existing_rows} rows already saved, skipping first {existing_rows} records.")

    skip = existing_rows
    total_found = None
    pages_fetched = 0

    with open(OUTPUT_FILE, "a" if file_exists else "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()

        while True:
            data = fetch_page(min_date, skip)
            props = data["results"]["properties"]
            meta = data["results"]["meta"]["results"]

            if total_found is None:
                total_found = meta.get("resultsFound", 0)
                pages = (total_found + PAGE_SIZE - 1) // PAGE_SIZE
                cost_est = pages * 0.01
                print(f"Total records: {total_found:,} | Est. pages: {pages} | Est. cost: ~${cost_est:.2f}")

            if not props:
                break

            for p in props:
                writer.writerow(parse_property(p))
            f.flush()

            skip += len(props)
            pages_fetched += 1
            print(f"  Saved {skip:,} / {total_found:,}...")
            time.sleep(1)

            if len(props) < PAGE_SIZE:
                break

    print(f"\nDone! {skip:,} records saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
