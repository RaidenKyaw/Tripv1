> ## ⚠ SCOPE AMENDMENT: Aug 2026, supersedes parts of §1 and §4
> **The target market is not Australia.** The goal is English-speaking colleges and
> universities across the West, starting with the **US**, then expanding, including
> non-English localisation later. The build now ships US defaults: USD, six origin
> airports (BOS, JFK, ORD, ATL, LAX, SFO), `skyscanner.com`, and US vocabulary
> (spring break, finals, `.edu`).
>
> **Three consequences the original brief got right and that now bite differently:**
>
> 1. **The UK is a legal problem, not just a later market.** §1 chose Australia
>    specifically to dodge SI 2026/455, from 6 Apr 2027 a fused flight + bed flow is a
>    regulated package needing an ATOL bond at ~15% of revenue. This build fuses them:
>    every deal row pairs `flights →` with `beds →` and prefills dates and party size.
>    **Do not open UK/Ireland** until that's resolved (decouple the flows, geo-gate beds,
>    or take the ATOL route). Get advice; don't read the statute yourself.
> 2. **The AU regulatory task is now a US one**, DOT full-fare advertising rules
>    (14 CFR 399.84) and state Seller of Travel registration (CA, FL, WA, HI, IA). Linking
>    out rather than selling probably keeps you clear of the latter, but confirm before money.
> 3. **Catchment density still governs sequencing.** §1's ~500 users per departure airport
>    is unchanged, and it's the reason "every Western university" is a destination, not a
>    launch. Fifty campuses across five countries is fifty airports at 10 users each,
>    which is zero working airports. One dense catchment first. Boston is the recommended
>    first target: the highest student density per airport in the US.
>
> Everything else below, the mechanism, the crew-code design, the metrics, the
> honesty principles in §4, stands unchanged.

# UNTITLED TRIP PLANNER: complete handoff brief

For any agent or developer picking this up. Everything below was produced in one working session
(Aug 2026). Read this top to bottom before writing code.

---

## 1. What Untitled Trip Planner is

**A membership website (never call it an app, no installs, no app stores) that helps groups of
young people actually take the trips their group chat keeps talking about.**

The mechanism: fuse **group availability** (which weekends/date-windows everyone can do) with
**cheap flight windows** from the group's home airport. Nobody else joins those two datasets,
group planners (Troupe, Wanderlog, TripIt) stop at coordination; price tools (Skyscanner, Google
Flights, Hopper) don't know who your friends are or when they're free. That seam is the product.

### The customer
Uni students / 18–25s in friend groups, reached **demographically** (TikTok/IG content, Reddit
usefulness, group-chat sharing), NOT campus-by-campus ambassadors. Research killed the campus
model: content isn't campus-local, friend groups cross institutions, and Fizz spent $41.5M to get
10–20% per campus. One geographic constraint survives: **catchment density**, ~500 users per
departure airport before deal quality is credible. You don't pick the city; the first users do.

### The revenue model
- **7-day free trial, no card** → annual pass (monthly-framed, billed yearly, AUD):
  | Tier | Framed | Billed each | Notes |
  |---|---|---|---|
  | Solo | $4.99/mo | $59/yr | deliberate decoy/anchor, matches Triips' $59 |
  | Pair (2) | $3.29/mo | $39/yr | |
  | Squad (4) | $2.49/mo | $29/yr | organiser free |
  | Crew (6) | $1.49/mo | $17/yr | organiser free · 71% off · "most picked" |
- **The crew-code mechanic (founder's design, keep it):** during any member's free week, friends
  who join with their crew code lock the shared crew rate, one bill date for the whole group.
  Join later → you start your own trial instead. This solves rate-sync ("Dave joined 4 months
  late at a different price") and weaponises the trial week as the recruitment window.
- **Affiliate on top:** flights pay ~nothing (Booking £2 flat, Skyscanner ~£0.20/click, Ryanair
  zero), beds ~€2.70/booking via Hostelworld or 4% Booking.com, activities 8% (Viator/GYG),
  ~£9–23 per 6-person trip realistically. Garnish, not the business.
- **Live price experiment already wired:** fake-door Pass card rotates $1.49 vs $2.49/mo by trip
  hash, variant logged with every `pass_click`. Decision rule: raise price whenever doubling it
  loses less than half the clicks.

### The numbers that decide everything
- **Individual→group conversion >25%** (share of signups that end up inside a group), THE metric
- CAC per **group** under ~$90 (group worth ~$130/yr incl. affiliate; solo signups have k=0)
- Catchment ≥500 users per airport before scaling content spend there
- Trial→paid conversion (no benchmark yet, the trial mechanic is untested)

### Strategic context (from the research phase, full decks exist)
- Original idea (flight+hotel deal-alert sub like Triips) was **no-go'd**: Thrifty Traveler shipped
  it in 2024, Google does both free, hotels don't crash 50–90% (avg drop ~15%), Travelzoo pays $62
  CAC for a $50 sub, and cheap flight-data APIs closed (Amadeus self-service shut Jul 2026).
- UK version dies on **SI 2026/455** (from 6 Apr 2027 a fused flight+bed flow = regulated package
  → ATOL bond at 15% of revenue). Australia launch avoids this but **AU regulatory research is
  still an open task**, must be done BEFORE taking any payment or booking money. Current build
  never touches money and only links out = clean.
- Ceiling honesty: comparable businesses (Jack's Flight Club $5.4M rev, sold 60% for $12M) are
  $1–5M/yr lifestyle businesses unless the friends/social layer creates something bigger.

---

## 2. Everything already built (state: WORKING, demo-mode, tested via Playwright)

All in `trip-planner-site/`. Every page runs standalone with no backend (demo mode) and upgrades
itself when Supabase keys are pasted into the `BACKEND = { url, anonKey }` line each file carries.

| File | What it is | State |
|---|---|---|
| `index.html` | Landing. Warm travel theme (sand/terracotta/teal, Georgia serif), animated drifting clouds + plane on a dashed flight path, fare ticker, how-it-works (passport stamps), **Inside the planner** showcase (Deals/Trips/Friends), group-chat-bubble proof section, postcard deal cards, boarding-pass pricing tiers + guarantees, FAQ, honest footer. CTAs → `onboard.html` | ✅ tested |
| `onboard.html` | 5-step wizard: account (Supabase email/pw or demo-explore) → name/handle/home airport → trip vibes + budget → usual windows → "here's the deal" pricing explainer + crew-code entry → `home.html`. Progress bar, every step tracked | ✅ tested |
| `home.html` | Logged-in shell. Side panel (bottom bar on mobile): **Deals** (16 routes/origin, sort by cheapest/discount/soonest/popular/recently-updated, flights+beds linkouts), **Trips** (list + new trip + plan-with-friends), **Friends** (crew-code share card, add-by-handle, requests/accept, friends list). Trial banner with days left. Demo seeds: 2 trips, 2 friends, 1 pending request | ✅ tested, one known bug below |
| `app.html` | The trip tool (reachable from Trips; old shared links still work). Create trip → share link → friends tap weekends AND custom date ranges (mid-sem break) → boarding-pass result card → weekend-comparison chips with availability counts → 8 destinations with flights + beds (dates+group size prefilled) → fake-door Pass with price A/B → inline waitlist email capture. **No account needed to join a trip, this is the viral loop, never gate it** | ✅ tested |
| `dashboard.html` | Founder metrics (warm theme, single-hue bars): trips, groups, **group rate vs 25% target**, waitlist; funnel created→opened→joined→clickout; A/B table with decision rule; trips/day; latest trips. Demo data until keys | ✅ tested |
| `supabase-schema.sql` | v1: trips (+windows jsonb), members, events, waitlist. RLS: anon insert/select where needed, waitlist write-only. Realtime enabled on members | ✅ |
| `supabase-schema-v2.sql` | v2 (run after v1): profiles (handle, home, prefs, plan, trial_ends, crew_id), crews (code, locked_rate), friendships (request/accept), trips.owner. RLS done. Crew-week enforcement is client-side only for now | ✅ untested against live |
| `fetch_fares.py` | Nightly cache builder, multi-origin (SYD/MEL/BNE), Travelpayouts data API, rewrites `FARES_ALL` inside app.html (**note: home.html now also carries a FARES_ALL blob, script must be extended to write both, see §3**) | ⚠️ needs that one edit |
| `.github/workflows/refresh-fares.yml` | Runs fetcher 03:30 Sydney nightly, commits | ✅ |
| `og.png` | Chat link-preview card (boarding-pass design) | ✅ |
| `README.md` / `BACKEND.md` / `CHECKLIST.md` | Deploy, backend setup (15 min), metrics SQL, launch checklist | ✅ |

Also produced earlier (outputs/, separate from the site): two consulting decks
(`Project_Tailwind_Go_No_Go.pptx`, the original idea's no-go; `Project_Untitled Trip Planner_Student_Group_Travel.pptx`),
`Untitled Trip Planner_validation_playbook.md` (3 tests: legal, willingness-to-pay, content→group ignition),
`Untitled Trip Planner_validation_tracker.xlsx` (assumptions, trip log, groups test, catchment, pricing model, ATOL exposure).

**Data reality:** every price on every page is **generated sample data** (`fares.json`, seeded
random around realistic route baselines). Real prices only exist after the founder's Travelpayouts
token + one Action run. NEVER let a real user see sample fares.

**Design system (keep consistent):** bg `#FBF5EC`, card white, line `#EAD9C3`, ink `#33302B`,
terracotta `#D96A4B` (action), teal `#2F6D62` (trust/prices/deep panel `#24504A`), gold `#D9A441`
(deals), Georgia serif headlines + system sans body. Motifs: boarding passes (teal strip + dashed
perforation), postcards ("AIR MAIL" stamps), passport-stamp numbers, dashed flight paths. No neon,
no dark-tech. `prefers-reduced-motion` respected.

**Known bug (fix first):** on mobile (<820px) `home.html`'s bottom nav bar can cover tappable
elements at the viewport's bottom edge. Fix: in the mobile media query, raise `.main` bottom
padding to ~130px and add `scroll-margin-bottom:130px` to `.fr,.card,.deal,.trip`. (The fix was
written but its commit was interrupted, re-apply and re-test.)

**Analytics events already emitted everywhere** (`track()`): trip_created, trip_opened, joined,
share_click, weekend_switch, window_added, clickout, clickout_beds, pass_click(+variant),
waitlist_joined, onboard_step, onboard_complete, signup, tab_*, deals_sorted, friend_request,
friend_accept, crew_code_copied, home_opened. They log to console in demo, persist to `events`
with keys.

---

## 3. What the next agent must build (priority order)

### A. Finish what's started (hours)
1. Apply the mobile padding fix above; re-run the Playwright suite (test scripts pattern is in
   session history, create/join/chips/beds/A-B/waitlist + onboard→home + friends accept).
2. Extend `fetch_fares.py` to rewrite `FARES_ALL` in **both** `app.html` and `home.html` (same
   blob, two files). Update the workflow to commit both.
3. Rebuild the deliverable zip (last one predates onboard/home/landing-v3).
4. `login.html` (returning users: email/pw → home) + sign-out in the side panel `me` card.
5. Session-aware pages: when Supabase auth session exists, home.html loads profile (name,
   handle, home, real trial_ends countdown, crew code from crews table) instead of URL params;
   app.html pre-fills the organiser's name and sets `trips.owner`; trip page skips name entry.

### B. Close the product loop (days)
6. **Crew codes for real:** create a `crews` row (+code) at onboarding completion for every new
   user; redeem = set `profiles.crew_id` only while owner's `trial_ends > now()`; show crew
   members + fill state (n/6) in Friends tab; crew fill events tracked.
7. **Plan-with-friends for real:** select friends → create trip → seed `members` rows /
   notify, invitees still join by link without accounts.
8. **Trial expiry states:** countdown from `profiles.trial_ends`; on expiry, plan='expired' →
   soft paywall (deals blur/limit, trips stay accessible, never hold a group's plan hostage),
   pick-a-tier screen reusing the boarding-pass tier design.
9. **Alerts (the promised feature that doesn't exist):** nightly job (extend the GitHub Action or
   a Supabase edge function) that emails each user when a route from their home airport, matching
   their onboarding prefs/windows, drops >20% below typical. Resend or Supabase SMTP. This is the
   retention loop for the 8 silent months between trips, the research says alert *restraint*
   (≤2/week) is what prevents churn.
10. **Abuse hardening:** rate-limit anon inserts (edge function or captcha on create), handle
    uniqueness checks with friendly errors, input sanitisation review (all rendering is
    innerHTML-templated, audit for XSS via trip/handle names; escape user strings).

### C. Only after real users exist
11. Payments: Stripe Checkout for the four tiers + crew-rate application. **Blocked on: founder's
    Stripe account + the Australian regulatory research (open task), the current build never
    touches money and must stay that way until that research clears.**
12. Reviews section on the landing page, real quotes only, never fabricated (current build uses
    an illustrative chat-bubble conversation instead; keep that honesty).
13. A/B verdict + repricing at ~100 pass_clicks (decision rule above).
14. Deeper fare coverage / real custom-range pricing (currently nearest-weekend approximation
    with a visible `~`).

### D. What the founder (Raiden, Sydney) must do himself, no agent can
GitHub repo + Pages deploy · Supabase project (run schema v1 then v2, paste keys into the 5
`BACKEND` lines: index/app/onboard/home/dashboard) · Travelpayouts token as `TP_TOKEN` secret +
one manual Action run · domain + og:image URLs + real contact email · name/trademark check
("Untitled Trip Planner" is a placeholder) · then put the link in front of real people and read the dashboard.

---

## 4. Principles the next agent must not break

1. **It's a website.** Links in chats. No accounts required to *join* a trip, signup comes after
   the value, at trip-join → "save this trip / get alerts". Gating the join kills the k-loop.
2. **Never fake anything user-facing:** no invented reviews, no fake counters (social proof
   appears only past 20 real trips), no sample prices in front of real users, no fake urgency,
   the founding-rate lock is real urgency, keep it honourable.
3. **Nothing ahead of the data that justifies it.** The dashboard's group-rate number (>25%)
   gates all scaling work. Build in this order: fix → loop-close → users → then payments/scale.
4. **Money = legal first.** No payment, package assembly, or holding client funds until the AU
   regulatory position is professionally confirmed (and re-check SI 2026/455 if UK ever happens).
5. **Design system stays** (§2 palette/motifs). The brand bet is "travel = warmth and freedom",
   not tech gloss.
