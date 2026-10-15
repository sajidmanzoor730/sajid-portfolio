# Local test environment

Requires only Python 3 (no installs).

| Command | What it does |
|---|---|
| `python3 serve.py` | Serves the site at http://localhost:8000 (no caching; `python3 serve.py 9000` for another port) |
| `./run_tests.sh` | Link/asset/anchor checks + HTTP smoke test of every page and CSV |
| `./run_tests.sh --online` | Same, and also pings external URLs (GitHub, LinkedIn, Streamlit…) |

## Why serve over HTTP?
`crm-data-quality-cleanup.html` and `executive-operations-dashboard.html`
`fetch()` the CSVs in `data/`. Browsers block that on `file://`, so
double-clicking those pages shows empty charts.

## Needs internet when testing
- Chart.js from cdn.jsdelivr.net (two dashboard pages)
- Google Fonts (all pages)
- `helpdesk-dataset.html` and the Security Lab images load from raw.githubusercontent.com

## Scripts and SQL
| Command | What it does |
|---|---|
| `python3 sql/run_sql.py` | Loads the CSVs into SQLite and runs every query in `sql/queries.sql` |
| `python3 scripts/clean_crm.py` | Rule-based CRM cleanup; compares itself with the published clean file |
| `python3 scripts/validate_dataset.py <csv> --key <col>` | Data-quality report for any CSV |
| `./scripts/log_summary.sh` | Log summary on `data/sample_app.log` (generated sample) |

## Known issues found
- (fixed) `sajid.jpg` added to the project
- (fixed) `resume.pdf` added; phone menu added; unpinned Chart.js pinned
- Optional: copy `Helpdesk_Tickets_Dataset_Raw.csv` into `data/` so the dataset page does not depend on GitHub
