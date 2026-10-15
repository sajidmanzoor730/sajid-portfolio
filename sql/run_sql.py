#!/usr/bin/env python3
"""Loads the project CSVs into in-memory SQLite and runs every query in
sql/queries.sql, printing each result. No installs needed.

    python3 sql/run_sql.py            # run everything
    python3 sql/run_sql.py kpi_       # only queries whose name starts with 'kpi_'
"""
import csv, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = {
    "kpi":      "data/Operational_KPI_Dataset_Clean.csv",
    "exec_ops": "data/Executive_Operations_Dataset_Clean.csv",
    "crm":      "data/CRM_Data_Quality_Dataset_Clean.csv",
    "crm_raw":  "data/CRM_Data_Quality_Dataset_Raw.csv",
    "exec_raw": "data/Executive_Operations_Dataset_Raw.csv",
    "sec":      "data/security_alerts.csv",
}
NUMERIC = {"Resolution_Minutes", "SLA_Target_Minutes", "QA_Score", "Aging_Days",
           "Resolution_Hours", "Completeness_Score", "Items_Processed", "MTTR_Minutes"}


def load(con):
    for table, rel in TABLES.items():
        with open(ROOT / rel, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())
        con.execute(f'CREATE TABLE {table} ({", ".join(chr(34)+c+chr(34) for c in cols)})')
        con.executemany(
            f'INSERT INTO {table} VALUES ({",".join("?" * len(cols))})',
            [[(float(r[c]) if c in NUMERIC and r[c] != "" else (None if c in NUMERIC else r[c])) for c in cols] for r in rows],
        )


def queries():
    text = (ROOT / "sql/queries.sql").read_text(encoding="utf-8")
    for block in re.split(r"^-- name: ", text, flags=re.M)[1:]:
        name, _, body = block.partition("\n")
        yield name.strip(), body.strip()


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    con = sqlite3.connect(":memory:")
    load(con)
    for name, sql in queries():
        if not name.startswith(prefix):
            continue
        cur = con.execute(sql)
        head = [d[0] for d in cur.description]
        rows = cur.fetchall()
        print(f"\n== {name} ==")
        print(" | ".join(head))
        for r in rows:
            print(" | ".join(str(v) for v in r))


if __name__ == "__main__":
    main()
