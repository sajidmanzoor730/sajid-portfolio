#!/usr/bin/env python3
"""Source-to-report reconciliation and data-quality gates (pandas + stdlib).

    python3 scripts/reconcile_kpis.py

1. Computes the same KPIs three independent ways (pandas, SQL, plain csv module) and
   requires all three to agree.
2. Compares the result with the figure published on kpi-operations-dashboard.html.
3. Runs data-quality gates. Exit code 1 if any reconciliation or gate fails, so it can
   block a report refresh.
"""
import csv
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/Operational_KPI_Dataset_Clean.csv"
PAGE = ROOT / "kpi-operations-dashboard.html"
failures = []


def check(label, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(label)


df = pd.read_csv(DATA, dtype=str, keep_default_na=False)
for c in ("Resolution_Minutes", "SLA_Target_Minutes", "QA_Score"):
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ---- 1. same KPIs, three ways ------------------------------------------------
print("1) Reconciliation: three independent calculations")
pandas_val = {"rows": len(df), "breaches": int((df.SLA_Status == "Breached").sum()),
              "p1_breaches": int(((df.SLA_Status == "Breached") & (df.Priority == "P1")).sum())}

con = sqlite3.connect(":memory:")
df.to_sql("kpi", con, index=False)
sql_val = dict(zip(("rows", "breaches", "p1_breaches"), con.execute(
    "SELECT COUNT(*), SUM(SLA_Status='Breached'), SUM(SLA_Status='Breached' AND Priority='P1') FROM kpi").fetchone()))

with open(DATA, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
py_val = {"rows": len(rows),
          "breaches": sum(r["SLA_Status"] == "Breached" for r in rows),
          "p1_breaches": sum(r["SLA_Status"] == "Breached" and r["Priority"] == "P1" for r in rows)}

for k in pandas_val:
    check(f"{k}: pandas = SQL = csv module", pandas_val[k] == sql_val[k] == py_val[k],
          f"{pandas_val[k]} / {sql_val[k]} / {py_val[k]}")

# ---- 2. compare with the published page --------------------------------------
print("\n2) Dashboard page vs data")
html = PAGE.read_text(encoding="utf-8")
m = re.search(r"(\d+) of the (\d+) SLA breaches", html)
check("page says P1 breaches", m and int(m.group(1)) == pandas_val["p1_breaches"],
      f"page {m.group(1) if m else '?'} vs data {pandas_val['p1_breaches']}")
check("page says total breaches", m and int(m.group(2)) == pandas_val["breaches"],
      f"page {m.group(2) if m else '?'} vs data {pandas_val['breaches']}")

# ---- 3. data-quality gates ---------------------------------------------------
print("\n3) Data-quality gates")
check("Record_ID is unique", df.Record_ID.is_unique)
check("Created_Date is populated", (df.Created_Date != "").all())
check("Priority is P1-P4", df.Priority.isin(["P1", "P2", "P3", "P4"]).all())
check("SLA_Status is Met or Breached", df.SLA_Status.isin(["Met", "Breached"]).all())

done = df[df.Completed_Date != ""]
created, completed = pd.to_datetime(done.Created_Date), pd.to_datetime(done.Completed_Date)
bad_order = int((completed < created).sum())
check("Completed_Date is not before Created_Date", bad_order == 0, f"{bad_order} violations")

met_calc = done.Resolution_Minutes <= done.SLA_Target_Minutes
mismatch = int((met_calc != (done.SLA_Status == "Met")).sum())
check("SLA_Status agrees with resolution time vs target", mismatch == 0, f"{mismatch} mismatches")

qa = df.QA_Score.dropna()
check("QA_Score is between 0 and 100", qa.between(0, 100).all(), f"{len(qa):,} scored rows")

print(f"\n{'ALL CHECKS PASSED' if not failures else str(len(failures)) + ' CHECK(S) FAILED'}")
sys.exit(1 if failures else 0)
