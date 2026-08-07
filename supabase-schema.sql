-- ============================================================================
-- UNTITLED TRIP PLANNER: schema v1
-- Run this FIRST, in Supabase → SQL Editor → New query → paste → Run.
-- Then run supabase-schema-v2.sql.
--
-- What v1 covers: anonymous trips. No accounts, no auth. Anyone with a link can
-- open a trip and add themselves. That is deliberate, gating the join kills the
-- viral loop (see HANDOFF.md §4.1).
-- ============================================================================

-- ---------------------------------------------------------------- trips -----
create table if not exists public.trips (
  code        text primary key,                 -- short shareable code, generated client-side
  name        text not null,
  origin      text not null default 'SYD',      -- IATA code of the departure airport
  windows     jsonb not null default '[]'::jsonb, -- custom date ranges: [{s,e,l}]
  created_at  timestamptz not null default now()
);

-- -------------------------------------------------------------- members -----
create table if not exists public.members (
  id          bigint generated always as identity primary key,
  trip_code   text not null references public.trips(code) on delete cascade,
  name        text not null,
  weekends    jsonb not null default '[]'::jsonb, -- weekend indices; >=100 means windows[n-100]
  created_at  timestamptz not null default now()
);
create index if not exists members_trip_idx on public.members(trip_code, created_at);

-- --------------------------------------------------------------- events -----
create table if not exists public.events (
  id          bigint generated always as identity primary key,
  name        text not null,
  props       jsonb not null default '{}'::jsonb,
  trip_code   text,
  created_at  timestamptz not null default now()
);
create index if not exists events_name_idx on public.events(name, created_at desc);
create index if not exists events_created_idx on public.events(created_at desc);

-- ------------------------------------------------------------- waitlist -----
create table if not exists public.waitlist (
  id          bigint generated always as identity primary key,
  email       text not null,
  variant     text,                             -- which price the person was shown
  trip_code   text,
  created_at  timestamptz not null default now()
);

-- ============================================================================
-- ROW LEVEL SECURITY
-- The site ships an anon key in client-side JS, so anon can do exactly what the
-- product needs and nothing more. Notably: waitlist is WRITE-ONLY to anon,
-- nobody can enumerate the email list with the public key.
-- ============================================================================
alter table public.trips    enable row level security;
alter table public.members  enable row level security;
alter table public.events   enable row level security;
alter table public.waitlist enable row level security;

-- trips: anyone can create one, anyone with the code can read it
drop policy if exists "anon insert trips" on public.trips;
create policy "anon insert trips" on public.trips
  for insert to anon, authenticated with check (true);

drop policy if exists "anon read trips" on public.trips;
create policy "anon read trips" on public.trips
  for select to anon, authenticated using (true);

-- members: anyone can join a trip, anyone can see who's in
drop policy if exists "anon insert members" on public.members;
create policy "anon insert members" on public.members
  for insert to anon, authenticated with check (true);

drop policy if exists "anon read members" on public.members;
create policy "anon read members" on public.members
  for select to anon, authenticated using (true);

-- events: anon can write, and can read.
-- Read is deliberate, dashboard.html and the "Popular" sort in home.html both run on
-- the anon key, and neither can invent numbers it can't see. Events carry no personal
-- data: name + a small props blob + trip_code, never an email or a person's name.
-- If you later want the funnel private, move dashboard.html behind auth and change the
-- role on this policy from `anon, authenticated` to `authenticated`.
drop policy if exists "anon insert events" on public.events;
create policy "anon insert events" on public.events
  for insert to anon, authenticated with check (true);

drop policy if exists "anon read events" on public.events;
create policy "anon read events" on public.events
  for select to anon, authenticated using (true);

-- waitlist: write-only. No read policy = the email list is not public.
drop policy if exists "anon insert waitlist" on public.waitlist;
create policy "anon insert waitlist" on public.waitlist
  for insert to anon, authenticated with check (true);

-- ============================================================================
-- REALTIME: so a trip page updates the moment someone joins,
-- instead of waiting for the 45s poll fallback.
-- ============================================================================
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and tablename = 'members'
  ) then
    alter publication supabase_realtime add table public.members;
  end if;
end $$;
