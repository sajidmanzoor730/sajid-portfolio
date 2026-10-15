#!/usr/bin/env python3
"""Clean the raw 311 extract and add analysis columns (pandas).

    python3 clean_311.py [--raw data/nyc311_raw.csv] [--out data/nyc311_clean.csv]

Rules (every fix is counted in output/cleaning_log.json):
  - drop rows with no unique_key or unparseable created_date; keep first of duplicate unique_key
  - closed_date earlier than created_date -> blanked (flag kept)
  - zip must be 5 digits; lat/lon must fall inside the NYC bounding box, else blanked
  - borough standardised to Title Case; 'Unspecified' kept as its own label
Derived columns: response_hours, created_hour, weekday, month, is_closed, closed_within_24h, closed_within_7d
"""
import argparse, json
from pathlib import Path
import pandas as pd

NYC_LAT, NYC_LON = (40.45, 40.95), (-74.30, -73.65)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/nyc311_raw.csv"); ap.add_argument("--out", default="data/nyc311_clean.csv")
    a = ap.parse_args()
    df = pd.read_csv(a.raw, dtype=str, keep_default_na=False)
    log = {"raw_rows": len(df)}

    df["unique_key"] = df["unique_key"].str.strip()
    for c in ("created_date", "closed_date"):
        df[c] = pd.to_datetime(df[c].replace("", pd.NA), errors="coerce")

    bad = df.unique_key.eq("") | df.created_date.isna()
    log["dropped_no_key_or_created_date"] = int(bad.sum()); df = df[~bad]
    dup = df.unique_key.duplicated(keep="first")
    log["dropped_duplicate_unique_key"] = int(dup.sum()); df = df[~dup].copy()

    wrong_order = df.closed_date < df.created_date
    log["closed_before_created_blanked"] = int(wrong_order.sum())
    df["closed_date_flag"] = wrong_order
    df.loc[wrong_order, "closed_date"] = pd.NaT

    df["borough"] = df.borough.str.strip().str.title().replace("", "Unspecified")
    zip_ok = df.incident_zip.str.fullmatch(r"\d{5}")
    log["zip_blanked_not_5_digits"] = int((~zip_ok & (df.incident_zip.str.strip() != "")).sum())
    df.loc[~zip_ok, "incident_zip"] = ""

    lat = pd.to_numeric(df.latitude, errors="coerce"); lon = pd.to_numeric(df.longitude, errors="coerce")
    outside = lat.notna() & ~(lat.between(*NYC_LAT) & lon.between(*NYC_LON))
    log["lat_lon_blanked_outside_nyc"] = int(outside.sum())
    df["latitude"], df["longitude"] = lat.mask(outside), lon.mask(outside)

    hours = (df.closed_date - df.created_date).dt.total_seconds() / 3600
    df["response_hours"] = hours.round(2)
    df["created_hour"] = df.created_date.dt.hour
    df["weekday"] = df.created_date.dt.day_name()
    df["month"] = df.created_date.dt.strftime("%Y-%m")
    df["is_closed"] = (df.status == "Closed").astype(int)
    done = df.response_hours.notna()
    df["closed_within_24h"] = (df.response_hours <= 24).where(done).astype("Int64")
    df["closed_within_7d"] = (df.response_hours <= 168).where(done).astype("Int64")
    df["incident_address"] = df.incident_address.str.strip().str.upper()

    log["clean_rows"] = len(df)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path("output").mkdir(exist_ok=True)
    df.to_csv(a.out, index=False, date_format="%Y-%m-%d %H:%M:%S")
    Path("output/cleaning_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(json.dumps(log, indent=2)); print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()
