#!/usr/bin/env bash
# Runs all offline checks. Usage: ./run_tests.sh [--online]
set -u
cd "$(dirname "$0")"
fail=0
echo "== Static checks =="; python3 tests/check_site.py "$@" || fail=1
echo; echo "== HTTP smoke test =="; python3 tests/smoke_http.py || fail=1
echo; echo "== Findings vs data =="; python3 tests/check_findings.py || fail=1
echo; echo "== KPI reconciliation =="; python3 scripts/reconcile_kpis.py || fail=1
exit $fail
