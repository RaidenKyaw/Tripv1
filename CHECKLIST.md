# Launch checklist

Two columns: things only you can do (accounts, money, people), and things I build next.
Almost everything on my list is **blocked until your steps 1–3 are done** — I can't read data
that doesn't exist.

---

## Your side

### This week — deploy (≈40 min total)

- [ ] **1. Put it live (10 min).** Push this repo to GitHub → **Settings → Pages → deploy from `main`,
      root**. (Or drag the folder onto Netlify Drop for an instant URL.)
- [ ] **2. Supabase (15 min).** Free project → SQL Editor → run `supabase-schema.sql`, then
      `supabase-schema-v2.sql` → paste your Project URL + anon key into the `BACKEND` line in all
      **six** files: `index.html`, `app.html`, `onboard.html`, `home.html`, `login.html`,
      `dashboard.html`. Full walkthrough in `BACKEND.md`.
- [ ] **3. Real prices (10 min).** travelpayouts.com → free account → API token → add as `TP_TOKEN`
      secret in the repo → **Actions → "Refresh fares nightly" → Run workflow** once.
      **Do not share the link before this.** Every page shows a "sample prices" banner until it's done,
      which is your safety net — don't remove it, let the fetcher clear it.
- [ ] **4. Two small edits (5 min).** Set the `og:image` URL to your real domain in `index.html` and
      `app.html`; point the footer contact link at an inbox you actually read.

### This week — launch (the scary ten minutes)

- [ ] **5. One group chat.** Drop the link in a single real chat you're already in, with one line:
      "made this — tap the weekends you can do." Not a launch. One chat.
- [ ] **6. Watch three numbers** on `dashboard.html`: trips created, share that got 2+ joiners,
      pass clicks by price variant.

### This month

- [ ] **7. Name + domain.** "Freewheel" is a placeholder. Check domain availability and run an
      IP Australia trademark search before printing it anywhere.
- [ ] **8. Ten more chats, one at a time.** Societies are pre-formed groups — one committee post
      reaches forty people who already travel together.
- [ ] **9. Decision gate.** 25%+ of trips become groups → tell me, we scale. Below → tell me the
      *failure shape* (no opens? opens but no joins? joins but no clickouts?) and we fix that step,
      not the whole thing.

### Only when real money enters (not now)

- [ ] Legal opinion on the Australian regulatory position **before** taking any payment or building
      booking. This is the blocker on Stripe, not the code.
- [ ] ABN + business bank account before the first charge
- [ ] Terms + privacy page before collecting emails at scale
- [ ] Re-check UK **SI 2026/455** if you ever launch there — a fused flight+bed flow becomes a
      regulated package from 6 Apr 2027 and needs an ATOL bond at 15% of revenue

---

## My side

*Say the word and I build these — in this order, each gated on your data.*

### Ready now, needs nothing from you

- [ ] **Abuse hardening** — rate-limit anonymous inserts (edge function or captcha on trip creation),
      handle-uniqueness errors that read like English. Worth doing before step 8, not before step 5.
- [ ] **Australian regulatory research** — the AU equivalent of the UK ATOL analysis, properly sourced.
      Matters only before payments, but it's the long pole, so it can start any time.

### Needs your steps 1–3

- [ ] **Price alerts** — the promised feature that doesn't exist yet. A nightly job that emails each
      user when a route from their airport, inside one of their onboarding windows, drops more than
      20% under typical. Max twice a week. This is the retention loop for the eight silent months
      between trips, and restraint is what stops it becoming churn.
- [ ] **Supabase Realtime everywhere** — `app.html` already has it; extend to the Trips tab so a
      trip's member count updates live.

### Needs evidence groups actually form

- [ ] **Trial → paid flow** — Stripe Checkout for the four tiers plus crew-rate application.
      **Blocked on your Stripe account and the legal opinion above.**
- [ ] **A/B verdict + reprice** — at ~100 pass clicks I run the numbers and we set the real ladder.
- [ ] **Deeper fare coverage** — real pricing for custom date ranges instead of the current
      nearest-weekend approximation (the visible `~`).
- [ ] **Landing page social proof** — real numbers and real quotes once they exist. Not before.
      The site currently uses an explicitly labelled illustrative conversation; that stays until
      there's something true to replace it with.

---

**The sequencing rule behind both lists:** nothing gets built ahead of the data that justifies it.
Your steps 1–5 create the data. Everything else follows it.
