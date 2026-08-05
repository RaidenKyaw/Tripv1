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
CURRENCY = "usd"
WEEKENDS = 12
MIN_COVERAGE = 0.60          # below this we refuse to publish
REQUEST_PAUSE = 0.25         # seconds between calls — be a good citizen
RETRIES = 3

# Files that carry a `const FARES_ALL = {...};` line. All get the same blob.
TARGETS = ["app.html", "home.html", "index.html"]

# Routes we cache, per origin: destination code -> (display city, typical return fare USD).
#
# Six origins, chosen for student density rather than airport size — the product needs
# ~500 users sharing a departure airport before deal quality is credible, so a short
# list that fills is worth more than a long one that doesn't. Add origins as catchments
# fill, not before. The typical fare is only used to seed --sample data; live runs
# compute it from the median of what the API actually returns.
ROUTES = {
    "BOS": {   # Boston — highest student density per airport in the US
        "LGA": ("New York", 130), "DCA": ("Washington DC", 140), "ORD": ("Chicago", 170),
        "MIA": ("Miami", 190), "MCO": ("Orlando", 180), "ATL": ("Atlanta", 170),
        "MSY": ("New Orleans", 210), "DEN": ("Denver", 230), "LAS": ("Las Vegas", 240),
        "LAX": ("Los Angeles", 280), "SJU": ("San Juan", 300), "CUN": ("Cancún", 380),
        "NAS": ("Nassau", 370), "KEF": ("Reykjavík", 430), "DUB": ("Dublin", 540),
        "LHR": ("London", 620),
    },
    "JFK": {   # New York
        "BOS": ("Boston", 130), "DCA": ("Washington DC", 130), "ORD": ("Chicago", 160),
        "MIA": ("Miami", 180), "MCO": ("Orlando", 170), "ATL": ("Atlanta", 160),
        "MSY": ("New Orleans", 200), "DEN": ("Denver", 220), "LAS": ("Las Vegas", 230),
        "LAX": ("Los Angeles", 260), "SJU": ("San Juan", 280), "CUN": ("Cancún", 350),
        "NAS": ("Nassau", 350), "KEF": ("Reykjavík", 420), "DUB": ("Dublin", 520),
        "LHR": ("London", 580),
    },
    "ORD": {   # Chicago
        "LGA": ("New York", 160), "DCA": ("Washington DC", 150), "BOS": ("Boston", 170),
        "MIA": ("Miami", 200), "MCO": ("Orlando", 190), "ATL": ("Atlanta", 160),
        "MSY": ("New Orleans", 180), "DEN": ("Denver", 170), "LAS": ("Las Vegas", 200),
        "LAX": ("Los Angeles", 220), "SJU": ("San Juan", 380), "CUN": ("Cancún", 330),
        "NAS": ("Nassau", 400), "KEF": ("Reykjavík", 480), "DUB": ("Dublin", 580),
        "LHR": ("London", 640),
    },
    "ATL": {   # Atlanta
        "LGA": ("New York", 160), "DCA": ("Washington DC", 150), "BOS": ("Boston", 170),
        "MIA": ("Miami", 150), "MCO": ("Orlando", 140), "ORD": ("Chicago", 160),
        "MSY": ("New Orleans", 150), "DEN": ("Denver", 200), "LAS": ("Las Vegas", 230),
        "LAX": ("Los Angeles", 240), "SJU": ("San Juan", 330), "CUN": ("Cancún", 340),
        "NAS": ("Nassau", 330), "MBJ": ("Montego Bay", 360), "DUB": ("Dublin", 620),
        "LHR": ("London", 660),
    },
    "LAX": {   # Los Angeles
        "SFO": ("San Francisco", 130), "LAS": ("Las Vegas", 120), "SEA": ("Seattle", 170),
        "DEN": ("Denver", 190), "AUS": ("Austin", 220), "ORD": ("Chicago", 220),
        "JFK": ("New York", 260), "MIA": ("Miami", 280), "SJD": ("Cabo San Lucas", 320),
        "PVR": ("Puerto Vallarta", 330), "MEX": ("Mexico City", 350), "HNL": ("Honolulu", 350),
        "CUN": ("Cancún", 400), "NRT": ("Tokyo", 700), "LHR": ("London", 700),
        "CDG": ("Paris", 720),
    },
    "SFO": {   # San Francisco / Bay Area
        "LAX": ("Los Angeles", 130), "LAS": ("Las Vegas", 140), "SEA": ("Seattle", 150),
        "DEN": ("Denver", 190), "AUS": ("Austin", 230), "ORD": ("Chicago", 230),
        "JFK": ("New York", 280), "MIA": ("Miami", 300), "HNL": ("Honolulu", 330),
        "SJD": ("Cabo San Lucas", 350), "PVR": ("Puerto Vallarta", 360), "MEX": ("Mexico City", 370),
        "CUN": ("Cancún", 430), "NRT": ("Tokyo", 680), "LHR": ("London", 720),
        "CDG": ("Paris", 740),
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
        for dest, (city, _typical) in dests.items():
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


def make_sample():
    """Realistic placeholder fares, for when the route list changes and there's no
    token to hand. Deterministic (fixed seed) so the committed blob only changes when
    the routes do, not on every run.

    This does NOT clear SAMPLE_DATA — pages keep showing the "these aren't real
    prices" banner. Only a successful live fetch is allowed to clear that.
    """
    import random
    rng = random.Random(20260805)
    fares_all = {}
    for origin, dests in ROUTES.items():
        fares_all[origin] = {}
        for dest, (city, typical) in dests.items():
            prices = []
            for w in range(WEEKENDS):
                # log-ish spread around typical: mostly near it, occasional real dip
                factor = rng.choice([0.62, 0.71, 0.78, 0.85, 0.92, 1.0, 1.0, 1.08, 1.15, 1.3])
                factor *= rng.uniform(0.94, 1.06)
                prices.append({"w": w, "p": max(29, int(round(typical * factor)))})
            fares_all[origin][dest] = {
                "city": city,
                "typ": int(round(statistics.median(p["p"] for p in prices))),
                "fares": prices,
            }
    return fares_all


def previous_price(previous, origin, dest, w):
    try:
        for f in previous[origin][dest]["fares"]:
            if f["w"] == w:
                return f["p"]
    except (KeyError, TypeError):
        pass
    return None


def rewrite(path, blob, stamp, live=True):
    """Swap the cache blob in. With live=True also clear the sample-data flag and
    stamp the refresh time; with live=False the page keeps saying the prices are
    placeholders, which is the whole point of --sample."""
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # \r? on every anchor so a CRLF checkout on Windows still matches (.gitattributes
    # pins LF, but don't let the nightly job depend on that being respected).
    new_line = "const FARES_ALL = " + json.dumps(blob, separators=(",", ":")) + ";"
    src, n = re.subn(r"^const FARES_ALL = .*?;\r?$", lambda _: new_line, src, count=1, flags=re.M)
    if not n:
        raise SystemExit(f"{path}: no `const FARES_ALL = ...;` line found — did the file change shape?")

    # These two are optional per file; only app.html/home.html/index.html carry them today.
    if live:
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
    ap.add_argument("--sample", action="store_true",
                    help="write deterministic placeholder fares (no token, no network). "
                         "Leaves the sample-price banners up.")
    args = ap.parse_args()

    if args.sample:
        blob = make_sample()
        routes = sum(len(v) for v in blob.values())
        print(f"Generated placeholder fares for {routes} routes across {len(blob)} origins.\n")
        for path in TARGETS:
            if os.path.exists(path):
                rewrite(path, blob, stamp="", live=False)
        print("\nDone. These are NOT real prices — the sample banners stay up until a live run.")
        return

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
