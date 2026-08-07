# Backend setup: about 15 minutes

Untitled Trip Planner runs fine with no backend at all (demo mode). This turns on the real one: saved trips,
accounts, crews, friends, and the numbers on the dashboard.

You need a free Supabase project and a free Travelpayouts token. Nothing here costs money.

---

## 1 · Create the project (3 min)

1. [supabase.com](https://supabase.com) → **New project**
2. Pick a region close to your users, **us-east-1** (N. Virginia) for a US launch
3. Save the database password somewhere; you won't need it for the site, but you'll want it later

## 2 · Run the schema (2 min)

**SQL Editor → New query.** Paste and run, in this order:

1. `supabase-schema.sql`, trips, members, events, waitlist, row-level security, realtime
2. `supabase-schema-v2.sql`, profiles, crews, friendships, `trips.owner`

Both are safe to re-run: every statement is `if not exists` or `drop policy if exists` first.

## 3 · Paste your keys (5 min)

**Project Settings → API.** Copy the **Project URL** and the **anon / public** key.

Then in each of these files, find the `BACKEND` line near the top of the `<script>` block and fill it in:

```js
const BACKEND = { url: "https://xxxxx.supabase.co", anonKey: "eyJhbGciOi..." };
```

- `index.html`
- `app.html`
- `onboard.html`
- `home.html`
- `login.html`
- `dashboard.html`

The anon key is *meant* to be public, it ships in the browser. Row-level security is what protects
your data, which is why step 2 is not optional. **Never put the `service_role` key in these files.**

## 4 · Email settings (2 min)

**Authentication → Providers → Email.** For a launch this small, turn **"Confirm email" off** so the
signup wizard flows straight through. Turn it back on before you have real users worth protecting.

Supabase's built-in SMTP is rate-limited to a handful of emails an hour, fine for testing, not for
price alerts. When you build alerts, plug in Resend or your own SMTP under **Project Settings → Auth →
SMTP**.

## 5 · Real prices (10 min)

The prices in the repo are **realistic samples, not real fares**, and every page says so in a banner
until you do this.

1. [travelpayouts.com](https://travelpayouts.com) → free account → **Developers → API tokens**
2. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `TP_TOKEN`
   - Value: your token
3. **Actions → "Refresh fares nightly" → Run workflow**

It fetches ~1,152 route/weekend prices (6 origins × 16 routes × 12 weekends), rewrites the `FARES_ALL` blob in `app.html`, `home.html` and
`index.html`, flips `SAMPLE_DATA` to `false`, stamps the refresh time, and commits.

If fewer than 60% of prices come back it **aborts without writing anything** and fails the job, a
broken night leaves yesterday's good cache in place rather than half-empty prices on a live site.

To test locally first:

```bash
python fetch_fares.py --token YOUR_TOKEN --dry-run
```

---

## Checking it worked

Open `app.html`, create a trip, then in Supabase **Table Editor → trips**, your trip should be there.
The sample-price banner should be gone from every page after step 5.

## The numbers that matter

`dashboard.html` reads all of this for you. These are the same queries if you'd rather run them raw
in the SQL editor.

**Group formation rate, the one number that gates everything.** Target: above 25%.

```sql
select
  count(*)                                             as trips,
  count(*) filter (where members >= 2)                 as groups,
  round(100.0 * count(*) filter (where members >= 2) / nullif(count(*), 0), 1) as group_pct
from (
  select t.code, count(m.id) as members
  from trips t left join members m on m.trip_code = t.code
  group by t.code
) x;
```

**The funnel, where it breaks tells you what to fix.**

```sql
select name, count(*) as n
from events
where name in ('trip_created','trip_opened','joined','clickout','clickout_beds')
group by name
order by n desc;
```

**Price test.** Decision rule: double the price whenever doubling it loses *less than half* the clicks.
Don't read it before ~100 pass clicks, below that it's noise.

```sql
select
  props->>'variant' as variant,
  count(*) filter (where name = 'pass_click')      as pass_clicks,
  count(*) filter (where name = 'waitlist_joined') as emails
from events
where props ? 'variant'
group by 1
order by 1;
```

**Founding list size** (the `waitlist` table itself is write-only to the anon key on purpose, nobody
can enumerate your emails with a key that ships in the browser):

```sql
select count(*) from waitlist;
```

**Which destinations people actually click through to:**

```sql
select props->>'d' as destination, count(*) as clicks
from events
where name in ('clickout','clickout_beds')
group by 1
order by clicks desc
limit 20;
```

---

## Security notes, honestly

- **Anonymous inserts are open.** Anyone can create trips, join trips and log events without an
  account, because that's the product. It also means anyone can spam those tables. Before you promote
  the link widely, add rate limiting, a Supabase edge function or a captcha on trip creation
  (HANDOFF.md §3B.10).
- **Events are readable** by the anon key so `dashboard.html` can read them. They contain no emails
  and no personal names. If you want the funnel private later, put the dashboard behind auth and
  change that one policy to `authenticated`.
- **Crew-week enforcement is client-side** right now, `onboard.html` checks the organiser's
  `trial_ends` before applying a crew code. That's fine while nothing costs money. Move it into a
  `security definer` function before you take a single payment.
- **No money anywhere.** The build never touches payments, and it must stay that way until the
  US regulatory position is professionally confirmed (HANDOFF.md §4.4 and the scope amendment
  at the top of that file).
- **Do not open the UK or Ireland without advice.** From 6 Apr 2027, SI 2026/455 makes a fused
  flight + accommodation flow a regulated package, which would require an ATOL bond at ~15% of
  revenue. Every deal row here shows flights and beds together and prefills dates and party size
  into the bed link, that is close to the trigger. Resolve it before any UK user sees the site.
