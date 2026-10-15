#!/usr/bin/env python3
"""Data-quality checks on the raw 311 extract (pandas).

    python3 quality_checks.py [--raw data/nyc311_raw.csv]

Writes output/quality_report.json and output/quality_report.md. Nothing is changed here.
"""
import argparse, json
from pathlib import Path
import pandas as pd

EXPECTED = ["unique_key", "created_date", "closed_date", "agency", "complaint_type",
            "status", "borough", "incident_zip", "open_data_channel_type", "latitude", "longitude"]
NYC_LAT, NYC_LON = (40.45, 40.95), (-74.30, -73.65)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--raw", default="data/nyc311_raw.csv"); a = ap.parse_args()
    df = pd.read_csv(a.raw, dtype=str, keep_default_na=False)
    miss_cols = [c for c in EXPECTED if c not in df.columns]
    if miss_cols:
        raise SystemExit(f"Raw file is missing expected columns: {miss_cols}")

    n = len(df)
    blank = lambda s: s.str.strip() == ""
    created = pd.to_datetime(df.created_date, errors="coerce")
    closed = pd.to_datetime(df.closed_date, errors="coerce")
    lat = pd.to_numeric(df.latitude, errors="coerce"); lon = pd.to_numeric(df.longitude, errors="coerce")
    has_geo = lat.notna() & lon.notna()
    maxdate = created.max()

    checks = {
        "rows": n,
        "duplicate_unique_key": int(df.unique_key.duplicated().sum()),
        "created_date_missing_or_unparseable": int(created.isna().sum()),
        "created_date_range": [str(created.min()), str(created.max())],
        "closed_before_created": int((closed < created).sum()),
        "status_closed_but_no_closed_date": int(((df.status == "Closed") & blank(df.closed_date)).sum()),
        "closed_date_present_but_status_not_closed": int(((df.status != "Closed") & ~blank(df.closed_date)).sum()),
        "closed_date_in_future_of_extract": int((closed > pd.Timestamp.now()).sum()),
        "borough_unspecified_or_blank": int((df.borough.str.strip().str.lower().isin(["unspecified", ""])).sum()),
        "zip_not_5_digits": int((~blank(df.incident_zip) & ~df.incident_zip.str.fullmatch(r"\d{5}")).sum()),
        "lat_lon_outside_nyc": int((has_geo & ~(lat.between(*NYC_LAT) & lon.between(*NYC_LON))).sum()),
    }
    checks["missing_by_column_pct"] = {c: round(float(blank(df[c]).mean() * 100), 2) for c in df.columns}
    checks["status_counts"] = df.status.value_counts().to_dict()
    checks["distinct_complaint_types"] = int(df.complaint_type.nunique())

    Path("output").mkdir(exist_ok=True)
    Path("output/quality_report.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")

    lines = ["# 311 raw extract: data-quality report", "",
             f"Rows: **{n:,}**   Created range: {checks['created_date_range'][0]} to {checks['created_date_range'][1]}", "",
             "| Check | Rows | % of rows |", "|---|---:|---:|"]
    for k, v in checks.items():
        if isinstance(v, int) and k != "rows" and k != "distinct_complaint_types":
            lines.append(f"| {k.replace('_', ' ')} | {v:,} | {v / n * 100:.2f}% |")
    lines += ["", "## Blank share by column", "", "| Column | % blank |", "|---|---:|"]
    lines += [f"| {c} | {p}% |" for c, p in checks["missing_by_column_pct"].items()]
    Path("output/quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:22]))
    print("\nWrote output/quality_report.md and output/quality_report.json")


if __name__ == "__main__":
    main()
