#!/usr/bin/env python3
"""Static checks for the portfolio. No dependencies, works offline.

Checks every .html file for:
  - broken local links / images / CSS / JS (href, src)
  - broken #anchors (same-page and cross-page)
  - local data files requested by fetch() / *_URL constants
  - duplicate ids, missing <title>, missing alt on <img>
  - external URLs (listed only; pass --online to actually ping them)

Exit code 1 if any ERROR is found. WARNINGs don't fail the run.
"""
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

ROOT = Path(__file__).resolve().parent.parent
ONLINE = "--online" in sys.argv
OPTIONAL_DATA = {"data/Helpdesk_Tickets_Dataset_Raw.csv"}  # local copy preferred, GitHub copy is the fallback


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.imgs_no_alt = [], [], 0
        self.title, self._in_title = "", False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "img" and not a.get("alt"):
            self.imgs_no_alt += 1
        if tag == "title":
            self._in_title = True
        for k in ("href", "src"):
            if k in a and a[k]:
                self.refs.append((tag, a[k]))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


errors, warnings, external = [], [], {}
pages = {p.name: p for p in sorted(ROOT.glob("*.html"))}
parsed = {}

for name, path in pages.items():
    pg = Page()
    pg.feed(path.read_text(encoding="utf-8", errors="replace"))
    parsed[name] = pg

for name, pg in parsed.items():
    if not pg.title.strip():
        errors.append(f"{name}: missing <title>")
    dupes = {i for i in pg.ids if pg.ids.count(i) > 1}
    for d in dupes:
        warnings.append(f"{name}: duplicate id '{d}'")
    if pg.imgs_no_alt:
        warnings.append(f"{name}: {pg.imgs_no_alt} <img> without alt text")

    for tag, ref in pg.refs:
        if ref.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue
        if ref.startswith(("http://", "https://", "//")):
            external.setdefault(ref, set()).add(name)
            continue
        target, frag = urldefrag(ref)
        if not target:  # same-page anchor
            if frag and frag != "top" and frag not in pg.ids:
                errors.append(f"{name}: anchor #{frag} not found on this page")
            continue
        f = (ROOT / unquote(urlparse(target).path)).resolve()
        if not f.exists():
            errors.append(f"{name}: missing local file '{ref}' ({tag})")
        elif frag and f.suffix == ".html" and f.name in parsed:
            if frag not in parsed[f.name].ids:
                errors.append(f"{name}: anchor '{ref}' not found in {f.name}")

    # data files fetched from JS, e.g. const DATA_URL="data/x.csv"
    text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
    for m in set(re.findall(r"""["']((?:\./)?[\w./-]+\.(?:csv|json))["']""", text)):
        if m.startswith(("http", "//")):
            continue
        if not (ROOT / m).exists():
            if m in OPTIONAL_DATA:
                warnings.append(f"{name}: optional data file '{m}' not present (page falls back to the remote copy)")
            else:
                errors.append(f"{name}: JS references missing data file '{m}'")

# Pages nothing links to
linked = {urldefrag(r)[0] for pg in parsed.values() for _, r in pg.refs}
for name in pages:
    if name != "index.html" and name not in linked:
        warnings.append(f"{name}: not linked from any page")

# External links
if ONLINE:
    for url, where in sorted(external.items()):
        if "fonts.g" in url:
            continue
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "Mozilla/5.0"})
            code = urllib.request.urlopen(req, timeout=10).status
        except Exception as e:  # noqa
            code = getattr(e, "code", str(e))
        if code != 200:
            warnings.append(f"external {url} -> {code} (used in {', '.join(sorted(where))})")

print(f"Checked {len(pages)} pages, {len(external)} unique external URLs"
      f"{'' if ONLINE else ' (not pinged; use --online)'}")
for w in warnings:
    print("WARNING", w)
for e in errors:
    print("ERROR  ", e)
print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(1 if errors else 0)
