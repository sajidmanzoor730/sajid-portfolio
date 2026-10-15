#!/usr/bin/env python3
"""Run queries.sql against the cleaned 311 data and add medians (SQLite has no MEDIAN).

    python3 run_analysis.py [--clean data/nyc311_clean.csv]

Writes output/results/*.csv and one output/results.json that holds every result table.
"""
import argparse, json, re, sqlite3
from pathlib import Path
import pandas as pd


def queries(path):
    text = Path(path).read_text(encoding="utf-8")
    for block in re.split(r"^-- name: ", text, flags=re.M)[1:]:
        name, _, body = block.partition("\n")
        yield name.strip(), body.strip()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--clean", default="data/nyc311_clean.csv"); a = ap.parse_args()
    df = pd.read_csv(a.clean, keep_default_na=False, na_values=[""], low_memory=False)
    con = sqlite3.connect(":memory:")
    df.to_sql("r", con, index=False)

    out = Path("output/results"); out.mkdir(parents=True, exist_ok=True)
    results = {"rows_analysed": int(len(df)),
               "created_range": [str(df.created_date.min()), str(df.created_date.max())]}
    for name, sql in queries("queries.sql"):
        t = pd.read_sql_query(sql, con)
        t.to_csv(out / f"{name}.csv", index=False)
        results[name] = json.loads(t.to_json(orient="records"))
        print(f"{name:<28} {len(t):>5} rows")

    closed = df[(df.is_closed == 1) & df.response_hours.notna()]
    for key, label in (("complaint_type", "median_response_by_complaint"), ("agency", "median_response_by_agency")):
        g = closed.groupby(key).response_hours.agg(requests="size", median_hours="median")
        g = g[g.requests >= 500].sort_values("median_hours", ascending=False).head(15).round(1).reset_index()
        g.to_csv(out / f"{label}.csv", index=False)
        results[label] = json.loads(g.to_json(orient="records"))
        print(f"{label:<28} {len(g):>5} rows")

    Path("output/results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Wrote output/results.json")


if __name__ == "__main__":
    main()
