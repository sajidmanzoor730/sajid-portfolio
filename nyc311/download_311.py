#!/usr/bin/env python3
"""Download a date range of NYC 311 requests from the official NYC Open Data (Socrata) API.
Standard library only.

    python3 download_311.py --start 2026-07-01 --end 2026-08-01
    python3 download_311.py --start 2026-07-01 --end 2026-08-01 --app-token YOUR_TOKEN   # optional, avoids throttling

--end is exclusive. One month is roughly 250-350k rows. Output: data/nyc311_raw.csv
Dataset: https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9
"""
import argparse, csv, io, sys, time, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
COLUMNS = ["unique_key", "created_date", "closed_date", "agency", "agency_name",
           "complaint_type", "descriptor", "location_type", "status", "borough", "incident_zip", "incident_address",
           "open_data_channel_type", "resolution_description", "latitude", "longitude"]
PAGE = 50_000


def fetch(params, token, tries=4):
    url = BASE + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    headers = {"User-Agent": "portfolio-311-analysis/1.0"}
    if token:
        headers["X-App-Token"] = token
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # network hiccup / throttling: back off and retry
            if attempt == tries:
                raise
            print(f"  retry {attempt} after error: {e}", file=sys.stderr)
            time.sleep(3 * attempt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD (exclusive)")
    ap.add_argument("--app-token", default=None)
    ap.add_argument("--out", default="data/nyc311_raw.csv")
    a = ap.parse_args()

    where = f"created_date >= '{a.start}T00:00:00' AND created_date < '{a.end}T00:00:00'"
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    total, offset = 0, 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        while True:
            text = fetch({"$select": ",".join(COLUMNS), "$where": where, "$order": "unique_key",
                          "$limit": PAGE, "$offset": offset}, a.app_token)
            rows = list(csv.reader(io.StringIO(text)))
            header, body = rows[0], rows[1:]
            if header != COLUMNS:  # the API omits nothing we asked for; a mismatch means the schema changed
                missing = [c for c in COLUMNS if c not in header]
                raise SystemExit(f"Unexpected columns returned. Missing: {missing}")
            if not body:
                break
            w.writerows(body)
            total += len(body)
            offset += PAGE
            print(f"  downloaded {total:,} rows")
            if len(body) < PAGE:
                break
    print(f"Done: {total:,} rows -> {out}")


if __name__ == "__main__":
    main()
