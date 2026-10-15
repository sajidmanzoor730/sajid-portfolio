#!/usr/bin/env python3
"""Reusable data-quality report for any CSV (pandas only).

    python3 scripts/validate_dataset.py data/CRM_Data_Quality_Dataset_Raw.csv --key Record_ID
    python3 scripts/validate_dataset.py data/CRM_Data_Quality_Dataset_Clean.csv --key Record_ID

Checks: row count, duplicate keys, blank cells per column, and obviously malformed
emails/phones when those columns exist. Exit code 1 if the key column has duplicates,
so it can gate a pipeline step.
"""
import argparse
import re
import sys

import pandas as pd

EMAIL_RE = re.compile(r"^[^\s@.]+(?:\.[^\s@.]+)*@[^\s@.]+(?:\.[^\s@.]+)+$")
PHONE_RE = re.compile(r"^\+\d{1,3}( \d{2,4}){2,3}$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--key", required=True, help="column that must be unique")
    a = ap.parse_args()

    df = pd.read_csv(a.csv, dtype=str, keep_default_na=False)
    print(f"File: {a.csv}\nRows: {len(df):,}   Columns: {len(df.columns)}")

    dup = df[a.key].duplicated().sum()
    print(f"Duplicate {a.key}: {dup}")

    blanks = (df.apply(lambda s: s.str.strip() == "")).sum()
    blanks = blanks[blanks > 0].sort_values(ascending=False)
    print("\nBlank cells by column:" if len(blanks) else "\nNo blank cells.")
    for col, n in blanks.items():
        print(f"  {col:<22}{n:>6}  ({n / len(df) * 100:.1f}%)")

    if "Email" in df:
        e = df["Email"][df["Email"].str.strip() != ""]
        print(f"\nMalformed emails: {(~e.str.match(EMAIL_RE)).sum()}")
    if "Phone" in df:
        p = df["Phone"][df["Phone"].str.strip() != ""]
        print(f"Non-standard phones: {(~p.str.match(PHONE_RE)).sum()}")

    return 1 if dup else 0


if __name__ == "__main__":
    sys.exit(main())
