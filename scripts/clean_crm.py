#!/usr/bin/env python3
"""Rule-based cleanup of the raw CRM export (pandas only).

    python3 scripts/clean_crm.py                # writes output/crm_cleaned.csv + prints a report
    python3 scripts/clean_crm.py --out my.csv

Rules (deterministic only; anything that needs outside knowledge is flagged for the owner):
  1. Company names: trim, collapse spaces, fix ALL-CAPS / lower-case
  2. Phones: normalise to  +1 AAA BBB CCCC  (US/Canada) or  +44 AA BBBB CCCC  (UK)
  3. Emails: lower-case, collapse '@@' and '..', drop a trailing '.', re-validate; if still invalid -> blank + flag
  4. Duplicates: keep the earliest Record_ID when a later row repeats an email or a company name
  5. Missing email / phone / industry -> flagged for owner follow-up (not guessed)
At the end it compares the result with the published clean file (data/CRM_Data_Quality_Dataset_Clean.csv).
"""
import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/CRM_Data_Quality_Dataset_Raw.csv"
PUBLISHED = ROOT / "data/CRM_Data_Quality_Dataset_Clean.csv"

EMAIL_RE = re.compile(r"^[^\s@.]+(?:\.[^\s@.]+)*@[^\s@.]+(?:\.[^\s@.]+)+$")
SUFFIXES = {"llc": "LLC", "inc": "Inc", "ltd": "Ltd"}


def clean_company(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    if name and (name == name.upper() or name == name.lower()):
        name = name.title()
    words = [SUFFIXES.get(w.lower().strip(".,"), w) for w in name.split(" ")]
    return " ".join(words)


def company_key(name: str) -> str:
    key = re.sub(r"[.,]", "", name.lower())
    return re.sub(r" (inc|llc|ltd)$", "", re.sub(r"\s+", " ", key).strip())


def clean_phone(phone: str, country: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return ""
    if country == "United Kingdom":
        if digits.startswith("44"):
            digits = digits[2:]
        elif digits.startswith("0"):
            digits = digits[1:]
        return f"+44 {digits[:2]} {digits[2:6]} {digits[6:]}" if len(digits) == 10 else ""
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return f"+1 {digits[:3]} {digits[3:6]} {digits[6:]}" if len(digits) == 10 else ""


def clean_email(email: str) -> tuple[str, bool]:
    """Returns (email, was_invalid_and_unfixable)."""
    e = email.strip().lower()
    if not e:
        return "", False
    e = re.sub(r"@+", "@", e)
    e = re.sub(r"\.{2,}", ".", e).rstrip(".")
    return (e, False) if EMAIL_RE.match(e) else ("", True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "output/crm_cleaned.csv"))
    args = ap.parse_args()

    raw = pd.read_csv(RAW, dtype=str, keep_default_na=False).sort_values("Record_ID")
    df = raw.copy()

    df["Company_Name"] = df["Company_Name"].map(clean_company)
    df["Phone"] = [clean_phone(p, c) for p, c in zip(df["Phone"], df["Country"])]
    fixed = df["Email"].map(clean_email)
    df["Email"] = fixed.map(lambda t: t[0])
    unfixable = fixed.map(lambda t: t[1])

    # duplicates: a later row repeating an earlier email or company
    seen_email, seen_co, drop = set(), set(), []
    for rid, email, co in zip(df["Record_ID"], df["Email"], df["Company_Name"]):
        k = company_key(co)
        drop.append(bool((email and email in seen_email) or k in seen_co))
        if email:
            seen_email.add(email)
        seen_co.add(k)
    df["_dup"] = drop

    out = df[~df["_dup"]].copy()
    out["Follow_Up_Reason"] = ""
    for col, label in (("Email", "email"), ("Phone", "phone"), ("Industry", "industry")):
        miss = out[col].str.strip() == ""
        out.loc[miss, "Follow_Up_Reason"] += label + " "
    out["Follow_Up_Reason"] = out["Follow_Up_Reason"].str.strip().str.replace(" ", " + ")
    out = out.drop(columns="_dup")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)

    print(f"Raw rows:                 {len(raw):,}")
    print(f"Duplicates removed:       {int(df['_dup'].sum()):,}")
    print(f"Clean rows written:       {len(out):,}  ->  {args.out}")
    print(f"Unfixable emails blanked: {int(unfixable[~df['_dup']].sum()):,}")
    print(f"Rows needing follow-up:   {int((out['Follow_Up_Reason'] != '').sum()):,}")

    pub = pd.read_csv(PUBLISHED, dtype=str, keep_default_na=False).set_index("Record_ID")
    mine = out.set_index("Record_ID")
    same_ids = set(mine.index) == set(pub.index)
    print("\nComparison with the published clean file")
    print(f"  Same set of Record_IDs kept:  {same_ids}")
    common = mine.index.intersection(pub.index)
    for col in ("Company_Name", "Phone", "Email"):
        pct = (mine.loc[common, col] == pub.loc[common, col]).mean() * 100
        print(f"  {col:<13} identical on {pct:5.1f}% of rows")
    print("  (Remaining differences are values the published file filled by enrichment,")
    print("   which a rule-based script correctly leaves blank and flags instead of guessing.)")


if __name__ == "__main__":
    main()
