# NYC 311 Service Requests: Data Quality and Service Performance

An end-to-end analysis of real NYC 311 requests from the official NYC Open Data portal:
download, data-quality checks, cleaning, SQL analysis, findings and dashboard design.

Dataset: [311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9) (NYC Open Data, public).

## Status
The pipeline is written and has been dry-run on a **fake stand-in file** to check that the code works.
It has **not yet been run on a real month of data**, so this repo contains no findings yet.
`tests/make_stand_in_data.py` produces meaningless numbers; never publish anything made from it.

## Questions this answers
1. How clean is a real public service-request extract, and what had to be fixed?
2. What do New Yorkers complain about, where, and when?
3. Which agencies close requests quickly, and how much of the volume is repeat complaints about the same address?
4. Where is the backlog?

## Run it (Python 3.9+)
```bash
pip install -r requirements.txt
python3 download_311.py --start 2026-07-01 --end 2026-08-01   # one month, roughly 250-350k rows
python3 quality_checks.py      # -> output/quality_report.md / .json
python3 clean_311.py           # -> data/nyc311_clean.csv, output/cleaning_log.json
python3 run_analysis.py        # -> output/results.json, output/results/*.csv
```
Use a month that is at least two months old: requests from the last few days are mostly still open, which would make every agency look slow. (A look at the live API on 2026-10-10 showed the newest records almost all "In Progress" or "Open".) An optional free app token (`--app-token`) avoids API throttling.

## Files
| File | Purpose |
|---|---|
| `download_311.py` | Pages through the official API, keeps 16 columns |
| `quality_checks.py` | Duplicates, impossible dates, status/date conflicts, bad zips and coordinates, blanks |
| `clean_311.py` | Rule-based cleanup; every fix is counted; adds response time, 24h / 7-day flags, hour, weekday |
| `queries.sql` | The SQL analysis (window functions: RANK, LAG, moving average) |
| `run_analysis.py` | Runs the SQL and adds medians |
| `DESIGN.md` | Dashboard design and the management decision each page supports |

## Limits to state honestly
- One month is a slice, not the whole city's year; seasonality is not covered.
- Response time is created-to-closed time as recorded; agencies can close requests administratively.
- The column names were checked against a sample of live API records on 2026-10-10. Records carry no `due_date` value, so there is no "closed after due date" measure; response-time bands are used instead.
