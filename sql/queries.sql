-- Queries behind the portfolio findings. Run with:  python3 sql/run_sql.py
-- Tables are loaded from data/*.csv:  kpi, exec_ops, exec_raw, crm, crm_raw, sec
-- Dialect: SQLite (window functions); the same logic ports to SQL Server / PostgreSQL.

-- name: kpi_sla_by_priority
-- Finding: every SLA miss is a P1 record
SELECT Priority,
       COUNT(*)                                              AS records,
       SUM(SLA_Status = 'Breached')                          AS breaches,
       ROUND(100.0 * SUM(SLA_Status = 'Met') / COUNT(*), 2)  AS sla_met_pct
FROM kpi
GROUP BY Priority
ORDER BY Priority;

-- name: kpi_p1_by_complexity
-- Finding: complexity decides whether P1 work breaches
SELECT Complexity,
       COUNT(*)                                              AS p1_records,
       ROUND(100.0 * SUM(SLA_Status = 'Met') / COUNT(*), 1)  AS sla_met_pct,
       ROUND(AVG(Resolution_Minutes), 0)                     AS avg_minutes
FROM kpi
WHERE Priority = 'P1'
GROUP BY Complexity
ORDER BY sla_met_pct;

-- name: kpi_resolution_by_complexity
SELECT Complexity, ROUND(AVG(Resolution_Minutes), 0) AS avg_minutes
FROM kpi
GROUP BY Complexity
ORDER BY avg_minutes DESC;

-- name: kpi_data_quality_flags
SELECT Data_Quality_Flag,
       COUNT(*) AS records,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM kpi), 1) AS share_pct
FROM kpi
GROUP BY Data_Quality_Flag
ORDER BY records DESC;

-- name: exec_active_backlog
-- Finding: the backlog is old, and mostly late
SELECT COUNT(*)                                             AS active_records,
       SUM(Overdue_Flag = 'Yes')                            AS overdue,
       ROUND(100.0 * SUM(Overdue_Flag = 'Yes') / COUNT(*), 1) AS overdue_pct,
       SUM(Aging_Days > 90)                                 AS open_over_90_days,
       MAX(Aging_Days)                                      AS oldest_days
FROM exec_ops
WHERE Status NOT IN ('Completed', 'Closed');

-- name: exec_overdue_by_team
SELECT Team,
       COUNT(*) AS records,
       ROUND(100.0 * SUM(Overdue_Flag = 'Yes') / COUNT(*), 1) AS overdue_pct
FROM exec_ops
GROUP BY Team
ORDER BY overdue_pct DESC;

-- name: exec_overdue_by_month
SELECT Month,
       ROUND(100.0 * SUM(Overdue_Flag = 'Yes') / COUNT(*), 1) AS overdue_pct
FROM exec_ops
GROUP BY Month
ORDER BY Month;

-- name: crm_duplicates_in_raw
-- Duplicate rows = a later record that repeats an earlier email OR company name
WITH ranked AS (
  SELECT Record_ID,
         ROW_NUMBER() OVER (PARTITION BY LOWER(TRIM(Email))
                            ORDER BY Record_ID) AS email_rank
  FROM crm_raw
  WHERE TRIM(Email) <> ''
)
SELECT (SELECT COUNT(*) FROM crm_raw)                       AS raw_rows,
       (SELECT COUNT(*) FROM crm)                           AS clean_rows,
       (SELECT COUNT(*) FROM crm_raw) - (SELECT COUNT(*) FROM crm) AS rows_removed,
       (SELECT COUNT(*) FROM ranked WHERE email_rank > 1)   AS repeated_emails_in_raw;

-- name: crm_issue_resolution
SELECT Issue_Type,
       COUNT(*)                                                       AS records,
       SUM(Action_Taken IN ('Merged','Standardized','Enriched'))       AS resolved,
       SUM(Review_Status <> 'Ready')                                   AS needs_follow_up,
       ROUND(100.0 * SUM(Action_Taken IN ('Merged','Standardized','Enriched')) / COUNT(*), 1) AS resolution_pct
FROM crm
WHERE Issue_Type <> 'None'
GROUP BY Issue_Type
ORDER BY records DESC;

-- name: crm_quality_by_owner
SELECT Owner,
       COUNT(*)                                                          AS records,
       ROUND(100.0 * SUM(Issue_Type <> 'None') / COUNT(*), 1)            AS issue_rate_pct,
       ROUND(100.0 * SUM(Review_Status = 'Ready') / COUNT(*), 1)         AS ready_pct,
       ROUND(AVG(Completeness_Score), 1)                                 AS avg_completeness
FROM crm
GROUP BY Owner
ORDER BY ready_pct;

-- name: exec_dedupe_row_number
-- Technique: de-duplicate with ROW_NUMBER (keep the first row per Record_ID)
WITH ranked AS (
  SELECT Record_ID,
         ROW_NUMBER() OVER (PARTITION BY Record_ID ORDER BY Created_Date) AS rn
  FROM exec_raw
)
SELECT COUNT(*)                AS raw_rows,
       SUM(rn = 1)             AS unique_records,
       SUM(rn > 1)             AS duplicates_removed
FROM ranked;

-- name: exec_monthly_overdue_lag
-- Technique: month-over-month change with LAG
WITH m AS (
  SELECT Month,
         ROUND(100.0 * SUM(Overdue_Flag = 'Yes') / COUNT(*), 1) AS overdue_pct
  FROM exec_ops
  GROUP BY Month
)
SELECT Month,
       overdue_pct,
       ROUND(overdue_pct - LAG(overdue_pct) OVER (ORDER BY Month), 1) AS change_vs_prev_month
FROM m
ORDER BY Month;

-- name: exec_top_categories_in_team
-- Technique: rank within a group with RANK (top 2 categories by overdue count per team)
WITH c AS (
  SELECT Team, Category,
         COUNT(*)                   AS records,
         SUM(Overdue_Flag = 'Yes')  AS overdue
  FROM exec_ops
  GROUP BY Team, Category
), r AS (
  SELECT *, RANK() OVER (PARTITION BY Team ORDER BY overdue DESC) AS overdue_rank
  FROM c
)
SELECT Team, Category, records, overdue, overdue_rank
FROM r
WHERE overdue_rank <= 2
ORDER BY Team, overdue_rank;

-- name: sec_kpis
-- Reproduces the Security KPI view (12 alerts, 83.3% resolved, 25.3 min MTTR)
SELECT COUNT(*)                                                   AS total_alerts,
       SUM(Status = 'Resolved')                                   AS resolved,
       ROUND(100.0 * SUM(Status = 'Resolved') / COUNT(*), 1)      AS resolution_rate_pct,
       ROUND(AVG(MTTR_Minutes), 1)                                AS avg_mttr_minutes
FROM sec;

-- name: sec_by_severity
SELECT Severity,
       COUNT(*)                          AS alerts,
       SUM(Status = 'Resolved')          AS resolved,
       ROUND(AVG(MTTR_Minutes), 1)       AS avg_mttr_minutes
FROM sec
GROUP BY Severity
ORDER BY Severity;
