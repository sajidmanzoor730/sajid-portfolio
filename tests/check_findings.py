import sys
#!/usr/bin/env python3
"""Recomputes every number quoted in the 'Key findings' text from the CSVs
and fails if the page text and the data disagree. Needs pandas."""
import re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
k = pd.read_csv(ROOT / "data/Operational_KPI_Dataset_Clean.csv")
kraw = pd.read_csv(ROOT / "data/Operational_KPI_Dataset_Raw.csv")
e = pd.read_csv(ROOT / "data/Executive_Operations_Dataset_Clean.csv")
fails = []

def need(page, text, actual, label):
    """`text` must appear verbatim on the page, and `actual` must be the computed value."""
    html = (ROOT / page).read_text(encoding="utf-8")
    if text not in html:
        fails.append(f"{page}: text not found: {text!r}  ({label}; data says {actual})")

def pct(a, b, d=1): return f"{100*a/b:.{d}f}%"

# ---- KPI dataset
met = k.SLA_Status == "Met"; br = k.SLA_Status == "Breached"; p1 = k.Priority == "P1"
P = "kpi-operations-dashboard.html"
need(P, f"{(br&p1).sum()} of the {br.sum()} SLA breaches ({pct((br&p1).sum(),br.sum())})", 0, "p1 share of breaches")
need(P, f"{pct((met&p1).sum(),p1.sum())} of the time ({(met&p1).sum()} of {p1.sum()})", 0, "p1 sla")
need(P, f"{pct((met&~p1).sum(),(~p1).sum(),2)}", 0, "non-p1 sla")
hi = k[p1 & (k.Complexity=="High")]; me = k[p1 & (k.Complexity=="Medium")]
need(P, f"{pct((hi.SLA_Status=='Met').sum(),len(hi))} of the time ({(hi.SLA_Status=='Met').sum()} of {len(hi)}", 0, "p1 high")
need(P, f"averaging {hi.Resolution_Minutes.mean():.0f} minutes", 0, "p1 high res")
need(P, f"{pct((me.SLA_Status=='Met').sum(),len(me))} of the time", 0, "p1 medium")
assert (k[p1 & (k.Complexity=="Low")].SLA_Status == "Met").all() and k[p1].SLA_Target_Minutes.eq(60).all()
c = k.groupby("Complexity").Resolution_Minutes.mean()
need(P, f"{c['High']:.0f} minutes on average against {c['Low']:.0f} minutes", 0, "complexity res")
need(P, f"about {c['High']/c['Low']:.1f} times longer", 0, "ratio")
for col, lo_hi in (("Team", None), ("Region", None)):
    s = (k.SLA_Status=="Met").groupby(k[col]).mean()*100
    need(P, f"{s.min():.1f}% to {s.max():.1f}%", 0, col+" range")
v = k.Data_Quality_Flag; bad = v != "Valid"
need(P, f"{pct((v=='Valid').sum(),len(k))} of records pass validation. Of the {bad.sum()} flagged, {(v=='Missing Field').sum()} have a missing field ({pct((v=='Missing Field').sum(),bad.sum(),0)}), {(v=='Format Issue').sum()} a format issue and {(v=='Duplicate Candidate').sum()} are duplicate", 0, "dq")
na = k.QA_Result == "Not Assessed"; asd = k[~na]
need(P, f"{na.sum()} records ({pct(na.sum(),len(k))}) were not assessed. Of the {len(asd):,} assessed, {(asd.QA_Result=='Review').sum()} ({pct((asd.QA_Result=='Review').sum(),len(asd))}) went to review and none scored below 90", 0, "qa")
assert k.QA_Score.min() >= 90
need(P, f"the {k.QA_Score.mean():.1f}% average", 0, "qa avg")
need(P, f"{pct(len(asd),len(k))}", 0, "qa coverage")
need(P, f"{len(k):,} records covering January–September 2026", 0, "rows")
need(P, f"The raw file ({len(kraw):,} rows)", 0, "raw rows")

# ---- Executive dataset
E = "executive-operations-dashboard.html"
act = e[~e.Status.isin(["Completed","Closed"])]; od = e.Overdue_Flag == "Yes"
aod = act[act.Overdue_Flag=="Yes"]
need(E, f"{len(act)} records are still active; {len(aod)} of them ({pct(len(aod),len(act))}) are past their due date", 0, "backlog")
old = (act.Aging_Days > 90).sum()
need(E, f"{old} ({pct(old,len(act))}) have been open for more than 90 days, and the oldest is {act.Aging_Days.max()} days old", 0, "old")
m = od.groupby(e.Month).mean()*100
need(E, f"between {m.iloc[:6].min():.1f}% and {m.iloc[:6].max():.1f}% from January to June, then rose to {m.iloc[6]:.1f}% in July, {m.iloc[7]:.1f}% in August and {m.iloc[8]:.1f}% in September", 0, "trend")
ev = e[e.SLA_Status.isin(["Met","Breached"])]
b = (ev.SLA_Status=="Breached").groupby(ev.Complexity).mean()*100
need(E, f"{b['High']:.1f}% of the time against {b['Low']:.1f}% for low complexity, about {b['High']/b['Low']:.1f} times", 0, "complexity")
bt = (ev.SLA_Status=="Breached").groupby(ev.Team).mean()*100; ot = od.groupby(e.Team).mean()*100
need(E, f"Back Office breaches SLA {bt['Back Office']:.1f}% of the time against {bt['Operations']:.1f}% for Operations", 0, "team breach")
assert ot.idxmax()=="Back Office" and ot.idxmin()=="Customer Success"
need(E, f"{ot['Back Office']:.1f}%, against {ot['Customer Success']:.1f}% for Customer Success", 0, "team overdue")
a1 = act[act.Priority=="P1"]; a4 = act[act.Priority=="P4"]
need(E, f"{(a1.Overdue_Flag=='Yes').sum()} of the {len(a1)} active P1 records ({pct((a1.Overdue_Flag=='Yes').sum(),len(a1))}) are overdue", 0, "p1 overdue")
need(E, f"active P4 records ({pct((a4.Overdue_Flag=='Yes').sum(),len(a4))})", 0, "p4 overdue")
assert bt.idxmax()=="Back Office"
need(E, f"{len(e):,} records covering January–September 2026", 0, "rows")

# ---- Security lab: summary must match the alert table
sec = pd.read_csv(ROOT / "data/security_alerts.csv")
S = "microsoft-security-lab.html"
need(S, f"<strong>{(sec.Severity=='High').sum()}</strong><span>High-severity alerts", 0, "high count")
need(S, f"<span>High</span><div class=\"bar\"><i style=\"width:{100*(sec.Severity=='High').mean():.1f}%\"></i></div><strong>{(sec.Severity=='High').sum()}</strong>", 0, "severity mix high")
need(S, f"<strong>{(sec.Status=='Resolved').sum()}</strong><span>Resolved investigations", 0, "resolved")
need(S, f"{sec.MTTR_Minutes.mean():.1f} min", 0, "mttr")

# ---- NYC 311 page must be rebuilt from its result tables
import subprocess
r = subprocess.run([sys.executable, str(ROOT / "nyc311/build_page.py"), "--check"], capture_output=True, text=True)
if r.returncode != 0:
    fails.append("nyc-311-service-analysis.html is out of date with nyc311/results (run python3 nyc311/build_page.py)")

if fails:
    print("\n".join("FAIL "+f for f in fails)); sys.exit(1)
print("All finding figures match the data.")
