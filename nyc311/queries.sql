-- SQL analysis of the cleaned 311 extract. Table: r  (one row per service request). SQLite dialect.
-- Run with: python3 run_analysis.py

-- name: top_complaint_types
SELECT complaint_type,
       COUNT(*) AS requests,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM r), 1) AS share_pct
FROM r
GROUP BY complaint_type
ORDER BY requests DESC
LIMIT 15;

-- name: borough_volume
SELECT borough,
       COUNT(*) AS requests,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM r WHERE borough <> 'Unspecified'), 1) AS share_pct
FROM r
WHERE borough <> 'Unspecified'
GROUP BY borough
ORDER BY requests DESC;

-- name: requests_by_hour
SELECT created_hour AS hour, COUNT(*) AS requests
FROM r
GROUP BY created_hour
ORDER BY created_hour;

-- name: weekday_pattern
SELECT weekday, COUNT(*) AS requests
FROM r
GROUP BY weekday
ORDER BY requests DESC;

-- name: channel_mix
SELECT open_data_channel_type AS channel,
       COUNT(*) AS requests,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM r), 1) AS share_pct
FROM r
GROUP BY open_data_channel_type
ORDER BY requests DESC;

-- name: agency_performance
-- Closure rate, share of closed requests finished within 24 hours / 7 days, average hours to close
SELECT agency,
       COUNT(*)                                                    AS requests,
       ROUND(100.0 * SUM(is_closed) / COUNT(*), 1)                 AS closed_pct,
       ROUND(100.0 * SUM(closed_within_24h = 1)
             / NULLIF(SUM(closed_within_24h IS NOT NULL), 0), 1)   AS closed_within_24h_pct,
       ROUND(100.0 * SUM(closed_within_7d = 1)
             / NULLIF(SUM(closed_within_7d IS NOT NULL), 0), 1)    AS closed_within_7d_pct,
       ROUND(AVG(response_hours), 1)                               AS avg_response_hours
FROM r
GROUP BY agency
HAVING COUNT(*) >= 500
ORDER BY requests DESC;

-- name: backlog_by_agency
-- Requests still open at download time that were created more than 14 days before the extract's last day
-- (roughly the first half of the month). Their real age at download is much larger than 14 days.
SELECT agency,
       COUNT(*) AS open_over_14_days
FROM r
WHERE is_closed = 0
  AND julianday((SELECT MAX(created_date) FROM r)) - julianday(created_date) > 14
GROUP BY agency
ORDER BY open_over_14_days DESC
LIMIT 10;

-- name: top3_complaints_per_borough
-- RANK within each borough
WITH c AS (
  SELECT borough, complaint_type, COUNT(*) AS requests
  FROM r
  WHERE borough <> 'Unspecified'
  GROUP BY borough, complaint_type
), ranked AS (
  SELECT *, RANK() OVER (PARTITION BY borough ORDER BY requests DESC) AS rnk
  FROM c
)
SELECT borough, rnk AS rank, complaint_type, requests
FROM ranked
WHERE rnk <= 3
ORDER BY borough, rnk;

-- name: daily_volume_trend
-- Day-over-day change (LAG) and 7-day moving average (window frame)
WITH d AS (
  SELECT substr(created_date, 1, 10) AS day, COUNT(*) AS requests
  FROM r
  GROUP BY day
)
SELECT day,
       requests,
       requests - LAG(requests) OVER (ORDER BY day)                              AS change_vs_prev_day,
       ROUND(AVG(requests) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0) AS moving_avg_7d
FROM d
ORDER BY day;

-- name: repeat_locations
-- Same address, same complaint type, five or more requests in the extract
SELECT incident_address, complaint_type, COUNT(*) AS requests
FROM r
WHERE incident_address IS NOT NULL
GROUP BY incident_address, complaint_type
HAVING COUNT(*) >= 5
ORDER BY requests DESC
LIMIT 15;

-- name: repeat_location_share
-- How much of the volume is repeat complaints about the same address and type?
WITH g AS (
  SELECT incident_address, complaint_type, COUNT(*) AS n
  FROM r
  WHERE incident_address IS NOT NULL
  GROUP BY incident_address, complaint_type
)
SELECT SUM(n)                                                        AS requests_with_address,
       SUM(CASE WHEN n >= 3 THEN n ELSE 0 END)                       AS requests_at_repeat_locations,
       ROUND(100.0 * SUM(CASE WHEN n >= 3 THEN n ELSE 0 END) / SUM(n), 1) AS repeat_share_pct
FROM g;

-- name: weekday_avg_per_day
-- Weekday totals mislead when a month has 5 of some weekdays and 4 of others; average per calendar day instead
WITH d AS (
  SELECT substr(created_date, 1, 10) AS day, weekday, COUNT(*) AS n
  FROM r
  GROUP BY day, weekday
)
SELECT weekday,
       COUNT(*)                         AS days_in_extract,
       SUM(n)                           AS requests,
       ROUND(1.0 * SUM(n) / COUNT(*), 0) AS avg_requests_per_day
FROM d
GROUP BY weekday
ORDER BY avg_requests_per_day DESC;

-- name: midnight_check
-- Hour 0 is much busier than hour 1. Are many requests stamped exactly 00:00:00 (a placeholder time)?
SELECT SUM(created_hour = 0)                              AS hour_0_requests,
       SUM(substr(created_date, 12, 8) = '00:00:00')      AS stamped_exactly_midnight
FROM r;
