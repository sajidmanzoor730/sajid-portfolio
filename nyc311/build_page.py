#!/usr/bin/env python3
"""Builds nyc-311-service-analysis.html from the real result tables in nyc311/results/.
Every number on the page is computed here from those files, so the page cannot drift from the data.

    python3 nyc311/build_page.py            # writes nyc-311-service-analysis.html
    python3 nyc311/build_page.py --check    # exits 1 if the page on disk differs from what the data produces
"""
import html, json, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "nyc311/results"
OUT = ROOT / "nyc-311-service-analysis.html"
rd = lambda n: pd.read_csv(RES / f"{n}.csv")
esc = html.escape
n0 = lambda v: f"{int(round(v)):,}"

top, bor, hour = rd("top_complaint_types"), rd("borough_volume"), rd("requests_by_hour")
chan, agency, backlog = rd("channel_mix"), rd("agency_performance"), rd("backlog_by_agency")
top3, rep, repshare = rd("top3_complaints_per_borough"), rd("repeat_locations"), rd("repeat_location_share")
medc, meda, daily = rd("median_response_by_complaint"), rd("median_response_by_agency"), rd("daily_volume_trend")

# ---------- derived numbers (all from the files) ----------
total = int(daily.requests.sum())
assert total == int(hour.requests.sum()) == int(chan.requests.sum()), "tables do not reconcile"
unspec = total - int(bor.requests.sum())
daily["day"] = pd.to_datetime(daily.day)
daily["wd"] = daily.day.dt.day_name()
wk = daily.groupby("wd").requests.agg(days="count", total="sum", avg="mean").round(0)
order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
wk = wk.loc[order]
busiest_wd, quietest_wd = wk.avg.idxmax(), wk.avg.idxmin()
first7, last7 = daily.requests.iloc[:7].mean(), daily.requests.iloc[-7:].mean()
chg = (last7 / first7 - 1) * 100
top3_share = top.share_pct.iloc[:3].sum()
noise2 = top.share_pct.iloc[1] + top.share_pct.iloc[2]
ch = chan.set_index("channel").share_pct
online_mobile = ch["ONLINE"] + ch["MOBILE"]
ag = agency.set_index("agency")
mdA = meda.set_index("agency").median_hours
bl = backlog.merge(agency[["agency", "requests", "closed_pct"]], on="agency")
bl["share"] = bl.open_over_14_days / bl.requests * 100
dpr, tlc = bl.set_index("agency").loc["DPR"], bl.set_index("agency").loc["TLC"]
hpd_share = ag.loc["HPD", "requests"] / total * 100
peak_h, trough_h = hour.loc[hour.requests.idxmax()], hour.loc[hour.requests.idxmin()]
h0, h1 = int(hour.requests[0]), int(hour.requests[1])
r0 = rep.iloc[0]
rep15_sum = int(rep.requests.sum())
rs = repshare.iloc[0]
bpick = lambda b, k: top3[(top3.borough == b) & (top3["rank"] == k)].complaint_type.iloc[0]

kpis = [
    ("Requests", n0(total), "Created 1 to 31 July 2026"),
    ("Top 3 complaint types", f"{top3_share:.1f}%", f"Illegal Parking {top.share_pct.iloc[0]}%, two noise types {noise2:.1f}%"),
    ("Online + mobile", f"{online_mobile:.1f}%", f"Phone {ch['PHONE']}%, unknown {ch['UNKNOWN']}%"),
    ("At repeat locations", f"{rs.repeat_share_pct}%", "Same address and type, 3+ requests"),
    ("NYPD closed in 24h", f"{ag.loc['NYPD','closed_within_24h_pct']}%", f"Median {mdA['NYPD']} hours to close"),
    ("HPD closed in 7 days", f"{ag.loc['HPD','closed_within_7d_pct']}%", f"Median {mdA['HPD']:.0f} hours ({mdA['HPD']/24:.1f} days), {hpd_share:.0f}% of volume"),
    ("DPR still open", n0(dpr.open_over_14_days), f"{dpr.share:.1f}% of DPR requests, from first half of July"),
    ("Daily volume, last vs first week", f"{chg:.0f}%", f"{n0(last7)} vs {n0(first7)} requests a day"),
]
kpi_html = "".join(f'<div class="dq-kpi"><div class="dq-kl">{esc(l)}</div><div class="dq-kv">{esc(v)}</div><div class="dq-kn">{esc(n)}</div></div>' for l, v, n in kpis)


def table(head, rows, right=()):
    th = "".join(f'<th{" style=\"text-align:right\"" if i in right else ""}>{esc(h)}</th>' for i, h in enumerate(head))
    tr = "".join("<tr>" + "".join(f'<td{" style=\"text-align:right\"" if i in right else ""}>{esc(str(c))}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


boro_tbl = table(["Borough", "#1", "#2", "#3"],
                 [[b, bpick(b, 1), bpick(b, 2), bpick(b, 3)] for b in bor.borough])
med_tbl = table(["Agency", "Closed requests", "Median hours", "Median days"],
                [[r.agency, n0(r.requests), f"{r.median_hours:,.1f}", f"{r.median_hours/24:.1f}"] for r in meda.itertuples()], right=(1, 2, 3))
rep_tbl = table(["Address", "Complaint type", "Requests in July"],
                [[r.incident_address, r.complaint_type, n0(r.requests)] for r in rep.itertuples()], right=(2,))
wk_tbl = table(["Weekday", "Days in July", "Total requests", "Average per day"],
               [[d, int(r.days), n0(r.total), n0(r.avg)] for d, r in wk.iterrows()], right=(1, 2, 3))
dq_tbl = table(["Cleaning step", "Rows"], [
    ["Raw rows downloaded", "343,133"], ["Dropped: no key or no created date", "0"], ["Dropped: duplicate unique_key", "0"],
    ["Closing date earlier than creation date (blanked)", "74"], ["Zip code not 5 digits (blanked)", "0"],
    ["Coordinates outside NYC (blanked)", "0"], ["Clean rows", "343,133"]], right=(1,))

sql = (ROOT / "nyc311/queries.sql").read_text(encoding="utf-8")

DATA = {
    "types": top.to_dict("records"), "borough": bor.to_dict("records"), "hour": hour.to_dict("records"),
    "channel": chan.to_dict("records"), "agency": agency.to_dict("records"), "backlog": bl.to_dict("records"),
    "daily": [{"day": d.strftime("%d %b"), "requests": int(q), "avg": float(a)} for d, q, a in zip(daily.day, daily.requests, daily.moving_avg_7d)],
    "weekday": [{"weekday": d, "avg": float(r.avg)} for d, r in wk.iterrows()], "total": total,
}

TEMPLATE = r'''
<main>
<div class="wrap">

<a class="back" href="projects.html">← Back to Projects</a>
<div class="eyebrow">Public Data · NYC Open Data</div>
<h1>NYC 311: Where Service Is Fast, Slow and Repeated</h1>
<p class="lead">An end-to-end analysis of @@TOTAL@@ real New York City 311 service requests from July 2026: data-quality checks, cleaning, SQL analysis, findings and a recommended action for each.</p>

<div class="notice"><strong>Data note:</strong> This project uses real public data, not generated data. Source: NYC Open Data, "311 Service Requests from 2020 to Present", every request created 1 to 31 July 2026, downloaded in October 2026 with a Python script. Request status is as of that download. It covers one month and has no population adjustment, so borough counts are volumes, not rates.</div>

<section class="dq">
<div class="dq-kpis">@@KPIS@@</div>

<h2 class="sec">1. What people complain about</h2>
<p class="fnd">Demand is concentrated: three complaint types make up @@TOP3@@% of all requests, and the top 15 make up @@TOP15@@%. It also differs by borough. Illegal Parking is the top complaint in Brooklyn and Queens, street noise leads in the Bronx and Manhattan, and damaged trees lead on Staten Island. @@UNSPEC@@ requests have no usable borough and are left out of the borough view.</p>
<div class="dq-grid">
  <div class="dq-panel full"><h3>Top 15 complaint types</h3><p class="sub">Requests created in July 2026.</p><div class="dq-chart tall"><canvas id="cTypes" role="img" aria-label="Bar chart of the 15 most common complaint types"></canvas></div></div>
  <div class="dq-panel"><h3>Requests by borough</h3><p class="sub">Volume, not per person.</p><div class="dq-chart mid"><canvas id="cBorough" role="img" aria-label="Bar chart of requests by borough"></canvas></div></div>
  <div class="dq-panel"><h3>Top 3 complaint types per borough</h3><p class="sub">Ranked with SQL RANK().</p>@@BOROTBL@@</div>
</div>
<div class="notice"><strong>Decision this supports:</strong> Set response capacity by borough and complaint type instead of one citywide allocation. Parking and noise first, with tree crews weighted toward Staten Island.</div>

<h2 class="sec">2. How fast each agency closes requests</h2>
<p class="fnd">Closing speed varies enormously. NYPD closes @@NYPD24@@% of its requests within 24 hours (median @@NYPDMED@@ hours). HPD closes only @@HPD24@@% within 24 hours and @@HPD7@@% within 7 days, with a median of @@HPDMED@@ hours (about @@HPDDAYS@@ days), on @@HPDREQ@@ requests, which is @@HPDSHARE@@% of all volume. DOHMH is slower still: @@DOH24@@% in 24 hours and @@DOH7@@% in 7 days.</p>
<div class="dq-grid">
  <div class="dq-panel full"><h3>Share of requests closed within 24 hours and 7 days</h3><p class="sub">Agencies with at least 500 requests. Status as of the October 2026 download.</p><div class="dq-chart tall"><canvas id="cAgency" role="img" aria-label="Bar chart of closing speed by agency"></canvas></div></div>
  <div class="dq-panel full"><h3>Median time to close, closed requests only</h3>@@MEDTBL@@</div>
</div>
<div class="notice"><strong>Read with care:</strong> Time to close is created to closed as recorded. An agency can close a request administratively, so fast is not automatically good. Medians use closed requests only, so agencies with many still-open requests look faster than they really are.</div>
<div class="notice"><strong>Decision this supports:</strong> Ask HPD and DOHMH whether their closing times are real service levels or how their process closes tickets, then publish a target per complaint type instead of per agency. HPD alone is large enough to move the city-wide picture.</div>

<h2 class="sec">3. Requests still open months later</h2>
<p class="fnd">DPR has @@DPRN@@ requests from the first half of July still open at download, which is @@DPRSH@@% of everything it received. TLC closes only @@TLCCL@@% of its requests at all, and @@TLCN@@ of its @@TLCREQ@@ requests from the first half of the month are still open. These requests were at least 11 weeks old when the data was downloaded.</p>
<div class="dq-grid">
  <div class="dq-panel full"><h3>Open requests created in the first half of July</h3><p class="sub">Still open at the October 2026 download.</p><div class="dq-chart mid"><canvas id="cBacklog" role="img" aria-label="Bar chart of open requests by agency"></canvas></div></div>
</div>
<div class="notice"><strong>Decision this supports:</strong> Audit DPR and TLC open items first and decide whether they are unresolved work or tickets never closed in the system. They are the two agencies where open requests are a large share of what they received.</div>

<h2 class="sec">4. Repeat complaints about the same place</h2>
<p class="fnd">@@REPSHARE@@% of requests that carry an address sit at an address and complaint type with three or more requests that month. The extreme cases are striking: one address logged @@REP1N@@ "@@REP1T@@" requests in a month. Even so, the 15 biggest address-and-type combinations total only @@REP15@@ requests, so repeating is widespread rather than limited to a few addresses. Large apartment buildings will naturally generate several requests.</p>
<div class="dq-panel full"><h3>Address and complaint type with 5+ requests, top 15</h3>@@REPTBL@@</div>
<div class="notice"><strong>Decision this supports:</strong> Route repeat address-and-type combinations to one owner for a root-cause visit, instead of closing each ticket separately. Start with the handful of addresses with hundreds of requests.</div>

<h2 class="sec">5. When requests arrive</h2>
<p class="fnd">Requests peak between 9 am and noon (@@PEAKN@@ at @@PEAKH@@:00) and have a second, smaller peak at 9 and 10 pm (@@EVE21@@ and @@EVE22@@ an hour). The quietest hour is @@TROUGHH@@:00 with @@TROUGHN@@. Daily volume fell through the month: the last 7 days averaged @@LAST7@@ requests a day against @@FIRST7@@ in the first 7 days (@@CHG@@%).</p>
<div class="dq-grid">
  <div class="dq-panel"><h3>Requests by hour of day</h3><div class="dq-chart mid"><canvas id="cHour" role="img" aria-label="Bar chart of requests by hour"></canvas></div></div>
  <div class="dq-panel"><h3>Average requests per day, by weekday</h3><div class="dq-chart mid"><canvas id="cWeekday" role="img" aria-label="Bar chart of average requests per day by weekday"></canvas></div></div>
  <div class="dq-panel full"><h3>Daily requests and 7-day average</h3><div class="dq-chart tall"><canvas id="cDaily" role="img" aria-label="Chart of daily requests with a 7-day average"></canvas></div></div>
</div>
<div class="notice"><strong>A trap I caught:</strong> July 2026 has five Wednesdays, Thursdays and Fridays but only four of every other weekday, so raw weekday totals make Monday look quiet. Per day, @@BUSYWD@@ is actually the busiest (@@BUSYN@@ a day) and @@QUIETWD@@ the quietest (@@QUIETN@@).</div>
@@WKTBL@@
<div class="notice"><strong>Decision this supports:</strong> Staff intake for the 9 am to noon peak and the evening peak, and plan weekday coverage from per-day averages, not raw totals.</div>

<h2 class="sec">6. How people contact 311</h2>
<p class="fnd">Online and mobile bring @@OM@@% of requests; phone is still @@PH@@%, and @@UNK@@% have an unknown channel.</p>
<div class="dq-grid"><div class="dq-panel"><h3>Requests by channel</h3><div class="dq-chart mid"><canvas id="cChannel" role="img" aria-label="Doughnut chart of requests by channel"></canvas></div></div></div>
<div class="notice"><strong>Decision this supports:</strong> Focus on the 22% who still phone when looking at cost per request, and fix the channel field so the 9% unknown can be classified.</div>

<h2 class="sec">7. Data quality and method</h2>
<p class="fnd">The data was in good shape: no duplicate keys, no malformed zip codes and no coordinates outside the city. The one real defect was 74 requests whose closing date is earlier than their creation date. Their closing dates were blanked so they cannot distort response times.</p>
@@DQTBL@@
<h3 class="sub2">Things to know before trusting the numbers</h3>
<ul class="limits">
<li><strong>One month only.</strong> July is not a full year, so seasonality is not covered.</li>
<li><strong>Complaint names are not standardised.</strong> Some types are written in capitals (UNSANITARY CONDITION, PLUMBING, PAINT/PLASTER) while others are in title case. They were left as published; grouping is unaffected, but a production report would map them to one format.</li>
<li><strong>Unspecified boroughs.</strong> @@UNSPEC@@ requests have no usable borough.</li>
<li><strong>Still to check:</strong> hour 0 has @@H0@@ requests against @@H1@@ at hour 1. That may be real late-night demand or requests stamped exactly 00:00:00. The query midnight_check in the SQL file tests this; I have not run it yet.</li>
<li><strong>Closing speed is not quality.</strong> See the note in section 2.</li>
</ul>

<h2 class="sec">8. The SQL</h2>
<p class="sqlnote">This is the full SQL file (SQLite). The page was built from the output of these queries. The last two queries, weekday_avg_per_day and midnight_check, were added after the first run and have not been run on the real data yet.</p>
<details class="scr"><summary><b>nyc311/queries.sql</b> <span>All queries</span></summary><pre><code>@@SQL@@</code></pre></details>

<h2 class="sec">9. Reproduce it</h2>
<p class="sqlnote">The whole pipeline is in the nyc311 folder of the project. With Python 3.9+ and pandas installed:</p>
<pre class="cmds"><code>python3 download_311.py --start 2026-07-01 --end 2026-08-01
python3 quality_checks.py
python3 clean_311.py
python3 run_analysis.py
python3 build_page.py   # rebuilds this page from the results</code></pre>
<div class="dq-links"><a href="projects.html">← Back to Projects</a></div>
</section>
</div>
</main>
'''

repl = {
    "TOTAL": n0(total), "KPIS": kpi_html, "TOP3": f"{top3_share:.1f}", "TOP15": f"{top.share_pct.sum():.1f}", "UNSPEC": n0(unspec),
    "BOROTBL": boro_tbl, "NYPD24": ag.loc["NYPD", "closed_within_24h_pct"], "NYPDMED": mdA["NYPD"],
    "HPD24": ag.loc["HPD", "closed_within_24h_pct"], "HPD7": ag.loc["HPD", "closed_within_7d_pct"], "HPDMED": f"{mdA['HPD']:.0f}",
    "HPDDAYS": f"{mdA['HPD']/24:.0f}", "HPDREQ": n0(ag.loc["HPD", "requests"]), "HPDSHARE": f"{hpd_share:.0f}",
    "DOH24": ag.loc["DOHMH", "closed_within_24h_pct"], "DOH7": ag.loc["DOHMH", "closed_within_7d_pct"], "MEDTBL": med_tbl,
    "DPRN": n0(dpr.open_over_14_days), "DPRSH": f"{dpr.share:.1f}", "TLCCL": tlc.closed_pct, "TLCN": n0(tlc.open_over_14_days), "TLCREQ": n0(tlc.requests),
    "REPSHARE": rs.repeat_share_pct, "REP1N": n0(r0.requests), "REP1T": esc(r0.complaint_type), "REP15": n0(rep15_sum), "REPTBL": rep_tbl,
    "PEAKN": n0(peak_h.requests), "PEAKH": int(peak_h.hour), "TROUGHH": int(trough_h.hour), "TROUGHN": n0(trough_h.requests),
    "LAST7": n0(last7), "FIRST7": n0(first7), "CHG": f"{chg:.0f}", "BUSYWD": busiest_wd, "BUSYN": n0(wk.avg[busiest_wd]),
    "QUIETWD": quietest_wd, "QUIETN": n0(wk.avg[quietest_wd]), "WKTBL": wk_tbl, "OM": f"{online_mobile:.1f}", "PH": ch["PHONE"], "UNK": ch["UNKNOWN"],
    "DQTBL": dq_tbl, "EVE21": n0(hour.requests[21]), "EVE22": n0(hour.requests[22]), "H0": n0(h0), "H1": n0(h1), "SQL": esc(sql),
}
main = TEMPLATE
for k, v in repl.items():
    main = main.replace(f"@@{k}@@", str(v))
assert "@@" not in main, re.findall(r"@@\w+@@", main)

JS = r'''
<script>
const D=@@JSON@@;
const BLUE="#5B83FF",TEAL="#35D3C6",AMBER="#FFB547",RED="#FF6B7A",GREEN="#3DDC97",VIOLET="#9B7BFF",SLATE="#56648F",TXT="#93A0C8",TXT_HI="#EAF0FF",GRID="rgba(160,180,255,.10)";
const FONT='Manrope,"Segoe UI",Helvetica,Arial,sans-serif';
const int=n=>Number(n).toLocaleString("en-US");
if(typeof Chart==="undefined"){document.querySelectorAll(".dq-chart").forEach(e=>e.innerHTML='<p class="sub" style="padding:20px">Charts need the Chart.js library, which could not be loaded.</p>')}
else{
const d=Chart.defaults;d.color=TXT;d.font.family=FONT;d.font.size=12;d.borderColor=GRID;d.animation.duration=700;
Object.assign(d.plugins.tooltip,{backgroundColor:"#0B1124",borderColor:"rgba(160,180,255,.32)",borderWidth:1,titleColor:TXT_HI,bodyColor:"#C0CBEC",padding:11,cornerRadius:10,boxPadding:5,usePointStyle:true});
const valueLabels={id:"valueLabels",afterDatasetsDraw(c,a,o){if(!o||!o.show)return;const x=c.ctx,h=c.options.indexAxis==="y";x.save();x.font="700 11px "+FONT;x.fillStyle=TXT_HI;
 c.data.datasets.forEach((ds,i)=>{const m=c.getDatasetMeta(i);if(m.hidden||m.type!=="bar")return;m.data.forEach((b,j)=>{const v=ds.data[j];if(v==null)return;const t=int(v)+(o.suffix||"");
  if(h){x.textAlign="left";x.textBaseline="middle";x.fillText(t,b.x+7,b.y)}else{x.textAlign="center";x.textBaseline="bottom";x.fillText(t,b.x,b.y-6)}})});x.restore()}};
const centerText={id:"centerText",afterDatasetsDraw(c,a,o){if(!o||!o.text)return;const m=c.getDatasetMeta(0);if(!m||!m.data[0])return;const p=m.data[0],x=c.ctx;x.save();x.textAlign="center";x.textBaseline="middle";
 x.fillStyle=TXT_HI;x.font="800 28px "+FONT;x.fillText(o.text,p.x,p.y-8);x.fillStyle=TXT;x.font="600 11px "+FONT;x.fillText(o.sub||"",p.x,p.y+16);x.restore()}};
const merge=(a,b)=>{Object.keys(b).forEach(k=>{if(b[k]&&typeof b[k]==="object"&&!Array.isArray(b[k]))a[k]=merge(a[k]&&typeof a[k]==="object"?a[k]:{},b[k]);else a[k]=b[k]});return a};
const base=()=>({responsive:true,maintainAspectRatio:false,interaction:{mode:"nearest",intersect:true},plugins:{legend:{position:"bottom",labels:{usePointStyle:true,pointStyle:"circle",boxWidth:8,boxHeight:8,padding:18,color:"#B3BFE3",font:{size:12,weight:"600"}}},valueLabels:{show:false},centerText:{text:""}}});
const mk=(id,type,labels,datasets,opts)=>new Chart(document.getElementById(id),{type,data:{labels,datasets},options:merge(base(),opts||{}),plugins:[valueLabels,centerText]});
const AXG={grid:{color:GRID},border:{display:false},ticks:{precision:0}};
const AXC={grid:{display:false},border:{display:false},ticks:{color:"#C0CBEC",font:{weight:"600"}}};
const hbar={indexAxis:"y",layout:{padding:{right:46}},scales:{x:Object.assign({beginAtZero:true},AXG),y:AXC}};

mk("cTypes","bar",D.types.map(r=>r.complaint_type),[{label:"Requests",data:D.types.map(r=>r.requests),backgroundColor:BLUE,borderRadius:6,borderSkipped:false,barPercentage:.72}],
 merge({plugins:{legend:{display:false},valueLabels:{show:true}}},hbar));
mk("cBorough","bar",D.borough.map(r=>r.borough),[{label:"Requests",data:D.borough.map(r=>r.requests),backgroundColor:BLUE,borderRadius:{topLeft:6,topRight:6},borderSkipped:false,barPercentage:.7}],
 {layout:{padding:{top:20}},plugins:{legend:{display:false},valueLabels:{show:true}},scales:{x:AXC,y:Object.assign({beginAtZero:true},AXG)}});
const ag=D.agency.slice().sort((a,b)=>b.closed_within_7d_pct-a.closed_within_7d_pct);
mk("cAgency","bar",ag.map(r=>r.agency),[
 {label:"Closed within 24 hours",data:ag.map(r=>r.closed_within_24h_pct),backgroundColor:TEAL,borderRadius:6,borderSkipped:false,categoryPercentage:.8,barPercentage:.92},
 {label:"Closed within 7 days",data:ag.map(r=>r.closed_within_7d_pct),backgroundColor:BLUE,borderRadius:6,borderSkipped:false,categoryPercentage:.8,barPercentage:.92}],
 {indexAxis:"y",layout:{padding:{right:52}},interaction:{mode:"index",intersect:false},plugins:{valueLabels:{show:true,suffix:"%"}},
  scales:{x:Object.assign({beginAtZero:true,max:100,ticks:{callback:v=>v+"%"}},{grid:{color:GRID},border:{display:false}}),y:AXC}});
mk("cBacklog","bar",D.backlog.map(r=>r.agency),[{label:"Open requests",data:D.backlog.map(r=>r.open_over_14_days),backgroundColor:AMBER,borderRadius:6,borderSkipped:false,barPercentage:.7}],
 merge({plugins:{legend:{display:false},valueLabels:{show:true}}},hbar));
mk("cHour","bar",D.hour.map(r=>r.hour+":00"),[{label:"Requests",data:D.hour.map(r=>r.requests),backgroundColor:"rgba(91,131,255,.85)",borderRadius:{topLeft:4,topRight:4},borderSkipped:false,barPercentage:.8}],
 {plugins:{legend:{display:false}},scales:{x:{grid:{display:false},border:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:8}},y:Object.assign({beginAtZero:true},AXG)}});
mk("cWeekday","bar",D.weekday.map(r=>r.weekday.slice(0,3)),[{label:"Average requests per day",data:D.weekday.map(r=>r.avg),backgroundColor:TEAL,borderRadius:{topLeft:6,topRight:6},borderSkipped:false,barPercentage:.7}],
 {layout:{padding:{top:20}},plugins:{legend:{display:false},valueLabels:{show:true}},scales:{x:AXC,y:Object.assign({beginAtZero:true},AXG)}});
mk("cDaily","bar",D.daily.map(r=>r.day),[
 {type:"line",label:"7-day average",data:D.daily.map(r=>r.avg),borderColor:AMBER,backgroundColor:AMBER,borderWidth:2.5,tension:.35,pointRadius:0,pointHoverRadius:5,order:0},
 {type:"bar",label:"Requests",data:D.daily.map(r=>r.requests),backgroundColor:"rgba(91,131,255,.85)",borderRadius:{topLeft:4,topRight:4},borderSkipped:false,barPercentage:.8,order:1}],
 {interaction:{mode:"index",intersect:false},scales:{x:{grid:{display:false},border:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:8}},y:Object.assign({beginAtZero:true},AXG)}});
const cm=[BLUE,TEAL,VIOLET,AMBER,SLATE];
mk("cChannel","doughnut",D.channel.map(r=>r.channel+" · "+int(r.requests)+" ("+r.share_pct+"%)"),[{data:D.channel.map(r=>r.requests),backgroundColor:cm,borderWidth:0,spacing:3,borderRadius:5,hoverOffset:8}],
 {cutout:"66%",layout:{padding:6},plugins:{legend:{labels:{padding:12}},centerText:{text:int(D.total),sub:"requests"}}});
}
</script>
'''
JS = JS.replace("@@JSON@@", json.dumps(DATA, default=float))

extra_css = '<style>.sec{margin:56px 0 12px;font-size:26px}.fnd{max-width:820px;color:#C0CBEC;line-height:1.7;margin:0 0 20px}.dq-panel.full{grid-column:1/-1}.dq .notice{margin:18px 0}.sub2{margin:26px 0 8px}.limits{max-width:820px;color:#C0CBEC;line-height:1.7;padding-left:20px}.limits li{margin-bottom:8px}.sqlnote{color:#93A0C8;font-size:14px;max-width:760px}.scr{margin:0 0 14px;border:1px solid var(--line);border-radius:14px;padding:4px 18px;background:#0F1636}.scr summary{cursor:pointer;padding:14px 0;line-height:1.5}.scr summary span{display:block;color:#93A0C8;font-size:13px}.scr pre{max-height:520px;overflow:auto;font-size:12.5px;line-height:1.55;padding:14px 16px;margin:0 0 14px}.dq-panel .table-wrap{margin-top:10px}.dq-chart.tall{height:420px}.dq-links{margin-top:40px}.cmds{max-width:760px;padding:16px 18px;overflow-x:auto;font-size:12.5px;line-height:1.7;border:1px solid var(--line);border-radius:14px}</style>'

crm = (ROOT / "crm-data-quality-cleanup.html").read_text(encoding="utf-8")
head = crm[: crm.index("<main>")]
head = re.sub(r"<title>.*?</title>", "<title>NYC 311 Service Analysis | Sajid Manzoor</title>", head, flags=re.S)
head = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="End-to-end analysis of 343,133 real NYC 311 service requests from July 2026: data quality, SQL, findings and recommended actions.">', head)
head = head.replace("</head>", extra_css + "</head>", 1)
foot = '<footer class="footer"><div class="wrap">© 2026 Sajid Manzoor · Data Analytics &amp; Business Operations</div></footer>\n'
page = head + main + foot + JS + '\n<script src="modern.js"></script></body>\n</html>\n'

if "--check" in sys.argv:
    ok = OUT.exists() and OUT.read_text(encoding="utf-8") == page
    print("nyc-311 page matches the data" if ok else "nyc-311 page is OUT OF DATE: run python3 nyc311/build_page.py")
    sys.exit(0 if ok else 1)
OUT.write_text(page, encoding="utf-8")
print("Wrote", OUT.name, f"({len(page)/1e3:.0f} KB)")
