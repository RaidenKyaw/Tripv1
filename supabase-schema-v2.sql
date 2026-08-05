-- ============================================================================
-- FREEWHEEL — schema v2 (accounts, crews, friends)
-- Run AFTER supabase-schema.sql.
--
-- v1 stays exactly as it is: anonymous trips still work, links still work,
-- joining a trip still needs no account. v2 only adds the layer on top for
-- people who sign up — profile, crew rate, friends, trial clock.
-- ============================================================================

-- ------------------------------------------------------------ profiles -----
-- One row per signed-up user, keyed to Supabase Auth.
create table if not exists public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  name        text,
  handle      text unique,                       -- @handle, how friends add you
  home        text default 'SYD',                -- home airport (IATA)
  prefs       jsonb not null default '{}'::jsonb,-- {vibes:[], budget:'', windows:[]}
  plan        text not null default 'trial',     -- trial | solo | pair | squad | crew | expired
  trial_ends  timestamptz not null default (now() + interval '7 days'),
  crew_id     uuid,                              -- FK added below, after crews exists
  created_at  timestamptz not null default now()
);
create index if not exists profiles_handle_idx on public.profiles(lower(handle));

-- --------------------------------------------------------------- crews -----
-- A crew is the billing unit. Whoever creates it is the organiser (free).
-- Friends who join with the code DURING the organiser's free week lock the
-- shared rate and share one bill date. Join later and you start your own trial.
create table if not exists public.crews (
  id           uuid primary key default gen_random_uuid(),
  code         text unique not null,             -- short human-shareable code
  owner        uuid references auth.users(id) on delete set null,
  locked_rate  text,                             -- e.g. 'crew' — the tier the crew locked
  created_at   timestamptz not null default now()
);

do $$
begin
  if not exists (
    select 1 from information_schema.table_constraints
    where constraint_name = 'profiles_crew_id_fkey'
  ) then
    alter table public.profiles
      add constraint profiles_crew_id_fkey
      foreign key (crew_id) references public.crews(id) on delete set null;
  end if;
end $$;

-- --------------------------------------------------------- friendships -----
-- One row per relationship. requester → addressee, status flips on accept.
create table if not exists public.friendships (
  id          bigint generated always as identity primary key,
  requester   uuid not null references auth.users(id) on delete cascade,
  addressee   uuid not null references auth.users(id) on delete cascade,
  status      text not null default 'pending',   -- pending | accepted
  created_at  timestamptz not null default now(),
  unique (requester, addressee),
  check (requester <> addressee)
);
create index if not exists friendships_addressee_idx on public.friendships(addressee, status);
create index if not exists friendships_requester_idx on public.friendships(requester, status);

-- ----------------------------------------------------- trips.owner (v1) -----
-- Trips created by a signed-in organiser get stamped. Anonymous trips keep
-- owner = null and behave exactly as they did in v1.
alter table public.trips add column if not exists owner uuid references auth.users(id) on delete set null;
create index if not exists trips_owner_idx on public.trips(owner, created_at desc);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================
alter table public.profiles    enable row level security;
alter table public.crews       enable row level security;
alter table public.friendships enable row level security;

-- profiles ------------------------------------------------------------------
-- Signed-in users can read all profiles: adding a friend by @handle and showing
-- crew members both need it. Visible columns are name/handle/home/plan/prefs —
-- no email (that lives in auth.users) and no payment data (none exists).
drop policy if exists "read profiles" on public.profiles;
create policy "read profiles" on public.profiles
  for select to authenticated using (true);

drop policy if exists "insert own profile" on public.profiles;
create policy "insert own profile" on public.profiles
  for insert to authenticated with check (auth.uid() = id);

drop policy if exists "update own profile" on public.profiles;
create policy "update own profile" on public.profiles
  for update to authenticated using (auth.uid() = id) with check (auth.uid() = id);

-- crews ---------------------------------------------------------------------
-- Readable by any signed-in user so a code can be redeemed. Only the owner
-- writes. NOTE: the "join only during the organiser's trial week" rule is
-- currently enforced client-side (home.html). Move it into a SECURITY DEFINER
-- redeem function before money is involved — see HANDOFF.md §3B.6.
drop policy if exists "read crews" on public.crews;
create policy "read crews" on public.crews
  for select to authenticated using (true);

drop policy if exists "insert own crew" on public.crews;
create policy "insert own crew" on public.crews
  for insert to authenticated with check (auth.uid() = owner);

drop policy if exists "update own crew" on public.crews;
create policy "update own crew" on public.crews
  for update to authenticated using (auth.uid() = owner) with check (auth.uid() = owner);

-- friendships ---------------------------------------------------------------
drop policy if exists "read own friendships" on public.friendships;
create policy "read own friendships" on public.friendships
  for select to authenticated using (auth.uid() = requester or auth.uid() = addressee);

drop policy if exists "request friendship" on public.friendships;
create policy "request friendship" on public.friendships
  for insert to authenticated with check (auth.uid() = requester);

-- only the person who received the request can accept it
drop policy if exists "accept friendship" on public.friendships;
create policy "accept friendship" on public.friendships
  for update to authenticated using (auth.uid() = addressee) with check (auth.uid() = addressee);

drop policy if exists "delete own friendship" on public.friendships;
create policy "delete own friendship" on public.friendships
  for delete to authenticated using (auth.uid() = requester or auth.uid() = addressee);

-- trips: a signed-in organiser may stamp and edit their own trip.
-- (v1's open insert/select policies still apply to anonymous trips.)
drop policy if exists "owner updates trip" on public.trips;
create policy "owner updates trip" on public.trips
  for update to authenticated using (auth.uid() = owner) with check (auth.uid() = owner);

-- ============================================================================
-- CONVENIENCE — crew fill state, used by the Friends tab (n/6)
-- ============================================================================
create or replace view public.crew_fill
with (security_invoker = on) as
  select c.id as crew_id,
         c.code,
         c.owner,
         c.locked_rate,
         count(p.id) as members
  from public.crews c
  left join public.profiles p on p.crew_id = c.id
  group by c.id, c.code, c.owner, c.locked_rate;
