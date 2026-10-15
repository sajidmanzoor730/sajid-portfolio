#!/usr/bin/env bash
# Summarise an application log: volume by level, top error messages, busiest hour.
# Usage: ./scripts/log_summary.sh [logfile]      (default: data/sample_app.log)
# Expected line format:  2026-09-14T08:15:02Z LEVEL service: message
set -euo pipefail
LOG="${1:-$(dirname "$0")/../data/sample_app.log}"
[[ -r "$LOG" ]] || { echo "Cannot read $LOG" >&2; exit 1; }

echo "== Lines by level =="
awk '{print $2}' "$LOG" | sort | uniq -c | sort -rn

echo; echo "== Top 5 error messages =="
awk '$2=="ERROR"{ $1=$2=""; print substr($0,3) }' "$LOG" | sort | uniq -c | sort -rn | head -5

echo; echo "== Busiest hours (UTC) =="
cut -c12-13 "$LOG" | sort | uniq -c | sort -rn | head -3

echo; echo "== Error rate =="
awk '{n++} $2=="ERROR"{e++} END{printf "%d errors in %d lines (%.2f%%)\n", e, n, 100*e/n}' "$LOG"
