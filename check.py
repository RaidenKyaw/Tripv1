#!/usr/bin/env python3
"""
Structural checks for the Untitled Trip Planner site.

    python check.py

No dependencies, no network, no browser. It doesn't test behaviour; it guards the
handful of invariants that are easy to break silently and expensive to notice late:
a page that quietly stopped shipping prices, a stray innerHTML that reopens XSS, a
sample-price banner that got deleted, an origin list that drifted between files.

Exits non-zero on any FAIL, so CI can gate on it.
"""

import glob
import json
import os
import re
import sys

PRICED_PAGES = ["index.html", "app.html", "home.html", "onboard.html"]
ALL_PAGES = PRICED_PAGES + ["login.html", "dashboard.html"]
BACKEND_PAGES = ALL_PAGES

fails, warns = [], []


def fail(where, msg):
    fails.append(f"{where}: {msg}")


def warn(where, msg):
    warns.append(f"{where}: {msg}")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def check_backend_lines():
    """Every page must carry a BACKEND line, and it must never hold a service key."""
    for p in BACKEND_PAGES:
        if not os.path.exists(p):
            fail(p, "missing")
            continue
        s = read(p)
        if not re.search(r"^const BACKEND = \{ url: \".*?\", anonKey: \".*?\" \};$", s, re.M):
            fail(p, "no BACKEND line in the expected shape")
        if "service_role" in s:
            fail(p, "contains 'service_role' - a service key must never ship to a browser")


def check_fare_blobs():
    """All priced pages must carry the same origins, or the site disagrees with itself."""
    origins = {}
    for p in PRICED_PAGES:
        s = read(p)
        m = re.search(r"^const FARES_ALL = (.*?);\r?$", s, re.M)
        if not m:
            fail(p, "no `const FARES_ALL = ...;` line (fetch_fares.py rewrites this)")
            continue
        try:
            blob = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            fail(p, f"FARES_ALL is not valid JSON ({e})")
            continue
        origins[p] = sorted(blob)
        for o, routes in blob.items():
            for code, r in routes.items():
                if not all(k in r for k in ("city", "typ", "fares")):
                    fail(p, f"{o}->{code} missing city/typ/fares")
                    break

    distinct = {tuple(v) for v in origins.values()}
    if len(distinct) > 1:
        fail("FARES_ALL", f"origins differ between pages: {origins}")


def check_sample_guard():
    """The sample-price banner is the thing standing between fake prices and a
    real user. It must exist, and only fetch_fares.py may clear the flag."""
    for p in PRICED_PAGES:
        s = read(p)
        if not re.search(r"^const SAMPLE_DATA = (true|false);\r?$", s, re.M):
            fail(p, "no SAMPLE_DATA flag")
        if "sampleFlag" not in s:
            fail(p, "SAMPLE_DATA exists but nothing renders the warning banner")


def check_currency():
    for p in PRICED_PAGES:
        s = read(p)
        if not re.search(r"^const RATES = \{.*?\};\r?$", s, re.M):
            fail(p, "no RATES line for currency conversion")
        if "CURRENCIES" not in s:
            fail(p, "no CURRENCIES table")


def check_xss_discipline():
    """All dynamic rendering builds nodes with textContent. An innerHTML fed by a
    template literal is how a trip name becomes markup on someone else's screen."""
    for p in ALL_PAGES:
        for i, line in enumerate(read(p).splitlines(), 1):
            if "innerHTML" in line and ("${" in line or "` +" in line or "+ \"" in line):
                fail(p, f"line {i}: innerHTML built from a template/concatenation")


def check_no_em_dashes():
    """House style: no em dashes. Written as an escape so this file never
    contains the character it is looking for."""
    EM_DASH = chr(0x2014)   # written as a codepoint so this file stays clean
    targets = (glob.glob("*.html") + glob.glob("*.md") + glob.glob("*.py") +
               glob.glob("*.sql") + glob.glob(".github/workflows/*.yml"))
    for p in sorted(targets):
        n = read(p).count(EM_DASH)
        if n:
            fail(p, f"{n} em dash(es) present")


def check_placeholders():
    for p in glob.glob("*.html"):
        s = read(p)
        for i, line in enumerate(s.splitlines(), 1):
            if "YOURDOMAIN" in line:
                warn(p, f"line {i}: YOURDOMAIN placeholder still present")
        if re.search(r'property="og:image" content="(?!https://)', s):
            fail(p, "og:image must be an absolute URL or chat previews break")


def check_fetcher_targets():
    """Every file fetch_fares.py claims to rewrite must actually be rewritable."""
    s = read("fetch_fares.py")
    m = re.search(r"^TARGETS = \[(.*?)\]", s, re.M | re.S)
    if not m:
        fail("fetch_fares.py", "no TARGETS list")
        return
    targets = re.findall(r'"(.*?)"', m.group(1))
    for t in targets:
        if not os.path.exists(t):
            fail("fetch_fares.py", f"TARGETS names {t}, which does not exist")
        elif not re.search(r"^const FARES_ALL = .*?;\r?$", read(t), re.M):
            fail("fetch_fares.py", f"TARGETS names {t}, which has no FARES_ALL line")


def check_weekend_parity():
    """The cache is keyed by weekend index. If the Python and JS definitions of
    'the next 12 weekends' ever drift, every price silently points at wrong dates."""
    py = read("fetch_fares.py")
    if "(4 - today.weekday() + 7) % 7 or 7" not in py:
        fail("fetch_fares.py", "next_weekends() rule changed; re-check parity with the JS")
    for p in ["app.html", "home.html"]:
        if "((5 - d.getDay() + 7) % 7 || 7)" not in read(p):
            fail(p, "nextWeekends() rule changed; re-check parity with fetch_fares.py")


def main():
    if not os.path.exists("index.html"):
        sys.exit("Run this from the repo root.")

    for fn in (check_backend_lines, check_fare_blobs, check_sample_guard, check_currency,
               check_xss_discipline, check_no_em_dashes, check_placeholders,
               check_fetcher_targets, check_weekend_parity):
        fn()

    for w in warns:
        print(f"WARN  {w}")
    for f in fails:
        print(f"FAIL  {f}")

    print()
    if fails:
        print(f"{len(fails)} failure(s), {len(warns)} warning(s)")
        sys.exit(1)
    print(f"All structural checks passed ({len(warns)} warning(s))")


if __name__ == "__main__":
    main()
