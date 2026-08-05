#!/usr/bin/env python3
"""
Nightly fare cache builder for Freewheel.

Pulls cheapest return fares for the next 12 Fri->Mon weekends, for every route we
show, from every origin we support, and rewrites the FARES_ALL blob inside each
page that carries one.

    python fetch_fares.py --token $TP_TOKEN

Why a cache and not a live call: the pages are static HTML on GitHub Pages with no
server, an API token must never ship to the browser, and fare APIs rate-limit hard.
One nightly run, committed to the repo, is the whole backend.

SAFETY RULE (HANDOFF.md §4.2 — never let a real user see sample fares):
this script only writes files if it got real prices for at least MIN_COVERAGE of
the route/weekend pairs it asked for. A partial or failed run leaves the previous
cache in place and exits non-zero, so a broken night is loud instead of silent.
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
CURRENCY = "aud"
WEEKENDS = 12
MIN_COVERAGE = 0.60          # below this we refuse to publish
REQUEST_PAUSE = 0.25         # seconds between calls — be a good citizen
RETRIES = 3

# Files that carry a `const FARES_ALL = {...};` line. All get the same blob.
TARGETS = ["app.html", "home.html", "index.html"]

# Routes we cache, per origin. Destination code -> display city.
ROUTES = {
    "SYD": {
        "MEL": "Melbourne", "OOL": "Gold Coast", "BNE": "Brisbane", "ADL": "Adelaide",
        "HBA": "Hobart", "CNS": "Cairns", "AKL": "Auckland", "ZQN": "Queenstown",
        "CHC": "Christchurch", "DPS": "Bali", "NAN": "Fiji", "SGN": "Ho Chi Minh City",
        "BKK": "Bangkok", "SIN": "Singapore", "KUL": "Kuala Lumpur", "MNL": "Manila",
    },
    "MEL": {
        "SYD": "Sydney", "OOL": "Gold Coast", "BNE": "Brisbane", "ADL": "Adelaide",
        "HBA": "Hobart", "CNS": "Cairns", "AKL": "Auckland", "ZQN": "Queenstown",
        "CHC": "Christchurch", "DPS": "Bali", "NAN": "Fiji", "SGN": "Ho Chi Minh City",
        "BKK": "Bangkok", "SIN": "Singapore", "KUL": "Kuala Lumpur", "MNL": "Manila",
    },
    "BNE": {
        "SYD": "Sydney", "MEL": "Melbourne", "OOL": "Gold Coast", "ADL": "Adelaide",
        "HBA": "Hobart", "CNS": "Cairns", "AKL": "Auckland", "ZQN": "Queenstown",
        "CHC": "Christchurch", "DPS": "Bali", "NAN": "Fiji", "SGN": "Ho Chi Minh City",
        "BKK": "Bangkok", "SIN": "Singapore", "KUL": "Kuala Lumpur", "MNL": "Manila",
    },
}


def next_weekends(n=WEEKENDS):
    """Next n Fri->Mon pairs. Must match nextWeekends() in the pages exactly,
    or weekend index w in the cache won't mean the same weekend in the UI."""
    today = date.today()
    # weekday(): Mon=0 .. Fri=4. Same "next Friday, never today" rule as the JS.
    ahead = (4 - today.weekday() + 7) % 7 or 7
    first_friday = today + timedelta(days=ahead)
    out = []
    for i in range(n):
        fri = first_friday + timedelta(days=7 * i)
        out.append((fri, fri + timedelta(days=3)))
    return out


def fetch_one(origin, dest, dep, ret, token):
    """Cheapest return fare for one route on one weekend, or None."""
    qs = urllib.parse.urlencode({
        "origin": origin,
        "destination": dest,
        "departure_at": dep.isoformat(),
        "return_at": ret.isoformat(),
        "currency": CURRENCY,
        "sorting": "price",
        "direct": "false",
        "limit": 1,
        "one_way": "false",
        "token": token,
    })
    url = f"{API}?{qs}"

    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                payload = json.load(resp)
            rows = payload.get("data") or []
            if not rows:
                return None
            price = rows[0].get("price")
            return int(round(float(price))) if price else None
        except urllib.error.HTTPError as e:
            if e.code == 429:                       # rate limited — back off and retry
                time.sleep(2 ** attempt)
                continue
            print(f"  ! {origin}->{dest} {dep}: HTTP {e.code}", file=sys.stderr)
            return None
        except Exception as e:                       # noqa: BLE001 - one bad route must not kill the run
            print(f"  ! {origin}->{dest} {dep}: {e}", file=sys.stderr)
            time.sleep(1)
    return None


def load_previous(path="app.html"):
    """Last good cache, so a route that fails tonight keeps yesterday's price
    instead of vanishing from the site."""
    try:
        with open(path, encoding="utf-8") as f:
            m = re.search(r"^const FARES_ALL = (.*?);\r?$", f.read(), re.M)
        return json.loads(m.group(1)) if m else {}
    except Exception:                                # noqa: BLE001
        return {}


def build(token, previous):
    weekends = next_weekends()
    print(f"Weekends: {weekends[0][0]} .. {weekends[-1][0]}")

    fares_all = {}
    asked = got = reused = 0

    for origin, dests in ROUTES.items():
        fares_all[origin] = {}
        for dest, city in dests.items():
            prices = []
            for w, (dep, ret) in enumerate(weekends):
                asked += 1
                price = fetch_one(origin, dest, dep, ret, token)
                time.sleep(REQUEST_PAUSE)
                if price:
                    got += 1
                else:
                    price = previous_price(previous, origin, dest, w)
                    if price:
                        reused += 1
                if price:
                    prices.append({"w": w, "p": price})

            if not prices:
                print(f"  - {origin}->{dest}: no prices at all, dropping route")
                continue

            # "typical" = median of what we saw. A fare beats it by >20% to earn a DEAL stamp.
            typical = int(round(statistics.median(p["p"] for p in prices)))
            fares_all[origin][dest] = {"city": city, "typ": typical, "fares": prices}
            cheapest = min(p["p"] for p in prices)
            print(f"  {origin}->{dest:4s} {len(prices):2d} weekends · low ${cheapest} · typical ${typical}")

    coverage = got / asked if asked else 0
    print(f"\nCoverage: {got}/{asked} live ({coverage:.0%}) · {reused} reused from last run")
    return fares_all, coverage


def previous_price(previous, origin, dest, w):
    try:
        for f in previous[origin][dest]["fares"]:
            if f["w"] == w:
                return f["p"]
    except (KeyError, TypeError):
        pass
    return None


def rewrite(path, blob, stamp):
    """Swap the cache blob, clear the sample-data flag, stamp the refresh time."""
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # \r? on every anchor so a CRLF checkout on Windows still matches (.gitattributes
    # pins LF, but don't let the nightly job depend on that being respected).
    new_line = "const FARES_ALL = " + json.dumps(blob, separators=(",", ":")) + ";"
    src, n = re.subn(r"^const FARES_ALL = .*?;\r?$", lambda _: new_line, src, count=1, flags=re.M)
    if not n:
        raise SystemExit(f"{path}: no `const FARES_ALL = ...;` line found — did the file change shape?")

    # These two are optional per file; only app.html/home.html/index.html carry them today.
    src = re.sub(r"^const SAMPLE_DATA = .*?;\r?$", "const SAMPLE_DATA = false;", src, count=1, flags=re.M)
    src = re.sub(r'^const FARES_STAMP = ".*?";\r?$', f'const FARES_STAMP = "{stamp}";', src, count=1, flags=re.M)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print(f"  wrote {path}")


def main():
    ap = argparse.ArgumentParser(description="Rebuild the Freewheel fare cache.")
    ap.add_argument("--token", default=os.environ.get("TP_TOKEN"),
                    help="Travelpayouts API token (or set TP_TOKEN)")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, but don't touch any file")
    args = ap.parse_args()

    if not args.token:
        raise SystemExit("No API token. Pass --token or set TP_TOKEN.\n"
                         "Get one free at travelpayouts.com → Developers → API tokens.")

    previous = load_previous()
    if previous:
        print(f"Loaded previous cache: {sum(len(v) for v in previous.values())} routes\n")

    blob, coverage = build(args.token, previous)

    if coverage < MIN_COVERAGE:
        raise SystemExit(
            f"\nABORTED: only {coverage:.0%} of fares came back live, below the {MIN_COVERAGE:.0%} floor.\n"
            "Nothing was written — the site keeps the last good cache rather than showing\n"
            "a half-empty one. Check the token and the API status, then run again."
        )

    if args.dry_run:
        print("\nDry run — no files written.")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    print()
    for path in TARGETS:
        if os.path.exists(path):
            rewrite(path, blob, stamp)
        else:
            print(f"  skipped {path} (not found)")
    print(f"\nDone. Cache stamped {stamp} UTC.")


if __name__ == "__main__":
    main()
