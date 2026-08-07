# Untitled Trip Planner

A membership **website**, never an app, that helps groups of young people actually take the trips
their group chat keeps talking about.

The mechanism: fuse **group availability** (which weekends everyone can do) with **cheap flight
windows** from the group's home airport. Group planners stop at coordination. Price tools don't know
who your friends are. That seam is the product.

Full strategy, research and roadmap: **[HANDOFF.md](HANDOFF.md)**. Read it before changing anything.

---

## Run it

It's static HTML. No build step, no dependencies, no framework.

```bash
python -m http.server 8000
# open http://localhost:8000
```

Every page works standalone with zero configuration. With no backend keys it runs in **demo mode**:
seeded state, nothing persists, prices are realistic placeholders. Paste Supabase keys in and the same
files become the real thing, see [BACKEND.md](BACKEND.md).

## The files

| File | What it is |
|---|---|
| `index.html` | Landing page. Hero, fare ticker, how-it-works, product showcase, pricing, FAQ |
| `onboard.html` | 4-step wizard. Shows real prices at step 1, asks for the account at step 4 |
| `login.html` | Returning users |
| `home.html` | The logged-in shell: **Deals**, **Trips**, **Friends**, trial countdown, soft paywall |
| `app.html` | The trip tool. Create → share link → friends tap dates → boarding-pass result. **No account needed to join** |
| `dashboard.html` | Founder metrics: group rate vs the 25% target, funnel, price test, trips/day |
| `og-source.html` | Source for `og.png`. Screenshot it at 1200×630 to regenerate |
| `supabase-schema.sql` | v1, trips, members, events, waitlist + RLS |
| `supabase-schema-v2.sql` | v2, profiles, crews, friendships, trips.owner + RLS. Run after v1 |
| `fetch_fares.py` | Nightly fare cache builder. Rewrites the `FARES_ALL` blob in three pages. `--sample` regenerates placeholders offline |
| `.github/workflows/refresh-fares.yml` | Runs the fetcher nightly and commits |

## Deploy

Push to GitHub → **Settings → Pages → deploy from `main`, root**. That's it. Or drag the folder onto
Netlify Drop for an instant URL.

Then work through **[CHECKLIST.md](CHECKLIST.md)**, it separates what only you can do (accounts,
money, people) from what gets built next.

---

## Onboarding is deliberately value-first

`onboard.html` shows the cheapest fares from a detected airport **before** asking for anything,
no account, no questions. Signup is the last step, once there's a saved setup worth keeping.
That ordering is the point, not an accident: it matches rule 1 below, and every step in between
changes something the user can see (crew size moves the per-person price and the pass rate;
windows rewrite a sample alert). Don't reorder it so the account comes first.

Currency is guessed from the browser's timezone, shown in a dropdown that says it guessed, and
carried to the other pages via `?cur=` and `localStorage`. Fares are cached in USD and converted
at rates `fetch_fares.py` refreshes nightly; converted prices are labelled approximate because
they are.

## Two rules that are easy to break by accident

**1. Prices are fake until the fetcher runs.** Every page ships with `SAMPLE_DATA = true` and shows a
visible warning banner while it is. `fetch_fares.py` flips it to `false` on its first successful run.
Don't remove the banner, and don't share the link before real prices exist.

**2. Joining a trip must never require an account.** `app.html` works for a stranger with a link and
no signup. That is the entire growth loop, gating it kills the product. Signup comes *after* the
value, not before it.

The rest of the principles are in [HANDOFF.md §4](HANDOFF.md).

## Design system

Warm travel, not tech gloss. Sand `#FBF5EC`, ink `#33302B`, line `#EAD9C3`, terracotta `#D96A4B`
(action), teal `#2F6D62` (trust/prices, deep panel `#24504A`), gold `#D9A441` (deals).

**Type: DM Sans throughout,** loaded from Google Fonts, set in `--display` (headlines) and `--sans`
(body). Headlines run at weight 500 with tight tracking; the size does the work, not the weight.

> **Override, Aug 2026.** HANDOFF.md 4.5 specifies Georgia serif headlines and says the design
> system stays. The founder overrode that after benchmarking against eatclub.com.au, which is a
> large geometric sans on cream. The palette, the postcard and boarding-pass motifs, and the
> honesty rules are all unchanged; only the typeface and the type scale moved. If you are weighing
> this up again, the argument for the serif was "warmth and freedom, not tech gloss", and the
> argument against was that it read older than the audience.

Motifs: boarding passes (teal strip and dashed perforation), postcards with AIR MAIL stamps,
passport-stamp step numbers, dashed flight paths. Deal cards are illustrated SVG scenes chosen by
destination type, filling the card with the crop anchored to the ground. `prefers-reduced-motion`
respected everywhere.

## A note on the JavaScript

All dynamic rendering builds DOM nodes with `textContent`, never `innerHTML` string templates. Trip
names, handles and city names are user-controlled and end up on other people's screens; this is what
keeps a trip called `<img onerror=...>` from being a stored XSS. Keep it that way when you extend it.
