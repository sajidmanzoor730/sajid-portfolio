#!/usr/bin/env python3
"""HTTP smoke test: starts serve.py on a spare port and requests every page
and every data file, the way a browser would. No dependencies."""
import subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8765
proc = subprocess.Popen([sys.executable, str(ROOT / "serve.py"), str(PORT)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
paths = ["/"] + [f"/{p.name}" for p in sorted(ROOT.glob("*.html"))] \
        + [f"/{p.relative_to(ROOT)}" for p in sorted((ROOT / "data").glob("*.csv"))] \
        + [f"/{p.relative_to(ROOT)}" for p in sorted((ROOT / "assets").rglob("*.svg"))] \
        + ["/modern.css", "/project.css", "/modern.js"]
bad = 0
try:
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1); break
        except Exception:
            time.sleep(0.2)
    for p in paths:
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}{p}", timeout=10)
            body = r.read()
            ok = r.status == 200 and len(body) > 0
            print(("PASS" if ok else "FAIL"), r.status, p, f"{len(body):,} B")
        except urllib.error.HTTPError as e:
            ok = False; print("FAIL", e.code, p)
        bad += not ok
finally:
    proc.terminate()
print(f"\n{len(paths) - bad}/{len(paths)} requests OK")
sys.exit(1 if bad else 0)
