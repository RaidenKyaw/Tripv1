# Launch checklist

Two columns: things only you can do (accounts, money, people), and things I build next.
Almost everything on my list is **blocked until your steps 1–3 are done**, I can't read data
that doesn't exist.

---

## Your side

### This week, deploy (≈40 min total)

- [ ] **1. Put it live (10 min).** Push this repo to GitHub → **Settings → Pages → deploy from `main`,
      root**. (Or drag the folder onto Netlify Drop for an instant URL.)
- [ ] **2. Supabase (15 min).** Free project → SQL Editor → run `supabase-schema.sql`, then
      `supabase-schema-v2.sql` → paste your Project URL + anon key into the `BACKEND` line in all
      **six** files: `index.html`, `app.html`, `onboard.html`, `home.html`, `login.html`,
      `dashboard.html`. Full walkthrough in `BACKEND.md`.
- [ ] **3. Real prices (10 min).** travelpayouts.com → free account → API token → add as `TP_TOKEN`
      secret in the repo → **Actions → "Refresh fares nightly" → Run workflow** once.
      **Do not share the link before this.** Every page shows a "sample prices" banner until it's done,
      which is your safety net, don't remove it, let the fetcher clear it.
- [ ] **4. Two small edits (5 min).** Set the `og:image` URL to your real domain in `index.html` and
      `app.html`; point the footer contact link at an inbox you actually read.

### This week, launch (the scary ten minutes)

- [ ] **5. One group chat.** Drop the link in a single real chat you're already in, with one line:
      "made this, tap the weekends you can do." Not a launch. One chat.
- [ ] **6. Watch three numbers** on `dashboard.html`: trips created, share that got 2+ joiners,
      pass clicks by price variant.

### This month

- [ ] **7. Name + domain.** "Freewheel" is a placeholder. Check domain availability and run a
      USPTO trademark search (TESS) before printing it anywhere.
- [ ] **8. Ten more chats, one at a time.** Clubs, teams, dorm floors and Greek houses are
      pre-formed groups, one post in a club GroupMe reaches forty people who already travel
      together. Stay inside **one metro** until that airport clears ~500 users; a thin catchment
      makes the deals look bad to everyone in it. Boston first.
- [ ] **9. Decision gate.** 25%+ of trips become groups → tell me, we scale. Below → tell me the
      *failure shape* (no opens? opens but no joins? joins but no clickouts?) and we fix that step,
      not the whole thing.

### Only when real money enters (not now)

- [ ] Legal opinion on the **US** position before taking any payment: DOT full-fare advertising
      (14 CFR 399.84) and state Seller of Travel registration (CA, FL, WA, HI, IA). Linking out
      rather than selling probably keeps you clear of the latter, confirm, don't assume. This is
      the blocker on Stripe, not the code.
- [ ] Business entity + bank account before the first charge
- [ ] Terms + privacy page before collecting emails at scale
- [ ] **Before any UK/Ireland launch, not just before money:** SI 2026/455 makes a fused
      flight+bed flow a regulated package from 6 Apr 2027, needing an ATOL bond at ~15% of
      revenue. This build fuses them today. Decouple, geo-gate, or bond, with advice.

---

## My side

*Say the word and I build these, in this order, each gated on your data.*

### Ready now, needs nothing from you

- [ ] **Abuse hardening**, rate-limit anonymous inserts (edge function or captcha on trip creation),
      handle-uniqueness errors that read like English. Worth doing before step 8, not before step 5.
- [ ] **US regulatory research**, DOT fare-advertising rules and state Seller of Travel laws,
      properly sourced. Matters before payments, but it's the long pole, so it can start any time.
- [ ] **Onboarding funnel read**, `onboard_step` fires on every step, so once there's traffic I can
      tell you exactly which step people quit on and fix that one. Needs ~50 starts to mean anything.
- [ ] **Localisation groundwork**, currency, airports and booking domains are config now, but every
      string is still hardcoded English across six files. Worth extracting before the second
      language, not before the second city.

### Needs your steps 1–3

- [ ] **Price alerts**, the promised feature that doesn't exist yet. A nightly job that emails each
      user when a route from their airport, inside one of their onboarding windows, drops more than
      20% under typical. Max twice a week. This is the retention loop for the eight silent months
      between trips, and restraint is what stops it becoming churn.
- [ ] **Supabase Realtime everywhere**, `app.html` already has it; extend to the Trips tab so a
      trip's member count updates live.

### Needs evidence groups actually form

- [ ] **Trial → paid flow**, Stripe Checkout for the four tiers plus crew-rate application.
      **Blocked on your Stripe account and the legal opinion above.**
- [ ] **A/B verdict + reprice**, at ~100 pass clicks I run the numbers and we set the real ladder.
- [ ] **Deeper fare coverage**, real pricing for custom date ranges instead of the current
      nearest-weekend approximation (the visible `~`).
- [ ] **Landing page social proof**, real numbers and real quotes once they exist. Not before.
      The site currently uses an explicitly labelled illustrative conversation; that stays until
      there's something true to replace it with.

---

**The sequencing rule behind both lists:** nothing gets built ahead of the data that justifies it.
Your steps 1–5 create the data. Everything else follows it.
