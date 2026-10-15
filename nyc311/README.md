# NYC 311 Service Requests: Data Quality and Service Performance

An end-to-end analysis using real public service-request records from NYC Open Data. The project covers extraction, data-quality checks, cleaning, SQL analysis and dashboard design.

**Official source:** [NYC 311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9)  
**API dataset ID:** `erm2-nwe9`  
**Unit of analysis:** one NYC 311 service request  
**Data freshness:** NYC Open Data updates this dataset daily. The API can return different results on later runs as records are updated.

## Data provenance and status

The analysis should be run on an actual dated extract from the official API. No stand-in or synthetic records should be presented as real findings. The checked-in `nyc311/results/*.csv` files must not be treated as verified official-data findings unless they were regenerated from a real download and the provenance report confirms that run.

**Latest verified execution:** GitHub Actions completed a live download and analysis for 1–31 July 2026 (end date exclusive). The run analyzed 343,133 records, with 0 duplicate unique keys and 0 missing/unparseable creation timestamps. Quality checks flagged 74 `closed_date < created_date` anomalies (0.02%), corrected by blanking those closure timestamps, and 460 records with unspecified/blank borough (0.13%). The run generated cleaning logs, quality reports and SQL result tables. [View the successful workflow run](https://github.com/sajidmanzoor730/sajid-portfolio/actions/runs/38719065382). The extract is a dated snapshot: the NYC Open Data source changes over time, so reruns may yield different values.

## Questions

1. Which problem types and boroughs generate the most requests in the selected period?
2. What share of records have missing or inconsistent fields?
3. How does recorded time-to-close vary by agency and problem type?
4. Which agencies have the largest older-open-request backlog in this extract?
5. How frequently do multiple records share the same normalized address and problem type?

## Run the analysis (Python 3.9+)

Use a completed historical month to reduce right-censoring from newly opened requests. The following example analyses July 2026; the end date is exclusive.

```bash
cd nyc311
python3 -m pip install -r requirements.txt
python3 download_311.py --start 2026-07-01 --end 2026-08-01
python3 quality_checks.py
python3 clean_311.py
python3 run_analysis.py
```

To choose a different completed month, change the dates. You can pass `--app-token YOUR_TOKEN` to the downloader if NYC Open Data throttles requests.

### Outputs

- `data/nyc311_raw.csv`: the direct API extract for the selected date range.
- `data/nyc311_clean.csv`: cleaned request records plus derived analysis fields.
- `output/quality_report.md` and `output/quality_report.json`: measured data-quality checks.
- `output/cleaning_log.json`: counted cleaning actions.
- `output/results.json` and `output/results/*.csv`: query results generated from the cleaned extract.

A successful run should be accompanied by the selected date range and the reported row counts. The latest successful run reported 343,133 raw rows and 343,133 cleaned rows; 74 invalid closure-before-creation timestamps were blanked and no rows were dropped for missing keys/creation dates or duplicate unique keys. Re-run the analysis after any data or code changes; do not hand-edit result counts to match the website.

## Methods

| File | Purpose |
|---|---|
| `download_311.py` | Retrieves a bounded date range from the official NYC Open Data API |
| `quality_checks.py` | Measures duplicate identifiers, date conflicts, missing values and invalid geographic fields |
| `clean_311.py` | Applies documented cleanup rules and creates time-based fields |
| `queries.sql` | Aggregations, window functions, volume trends and repeat-address analysis |
| `run_analysis.py` | Executes SQL against the cleaned extract and exports result tables |
| `DESIGN.md` | Dashboard structure and decisions supported by each view |

## Interpretation and limitations

- This is a period-specific extract, not a census of every NYC request across all years.
- The source is updated daily; counts can change after records are updated or recategorized.
- Recorded elapsed time is the difference between creation and closure timestamps. It is not automatically an official SLA metric and may reflect administrative closure practices.
- Requests that are still open do not have an observed closure duration. Treat their duration as censored, not as zero.
- Address-based repeat-request counts are indicators for investigation, not proof that the underlying issue persisted.
- Do not infer causation from descriptive comparisons between boroughs, agencies or complaint types.
- The public dataset documentation notes that it contains service requests directed to agencies and does not expose personally identifying information about the customer who made the request.

## Source

NYC Open Data, *311 Service Requests from 2020 to Present*:  
https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9

Built by Sajid Manzoor.
