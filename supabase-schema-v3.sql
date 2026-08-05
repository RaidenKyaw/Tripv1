-- ============================================================================
-- FREEWHEEL: schema v3 (shape constraints)
-- Run AFTER v1 and v2. Safe to re-run.
--
-- WHAT THIS IS: cheap limits on the SHAPE of anonymous writes. A trip name can't
-- be 40KB, a member can't be nameless, an event blob can't be enormous.
--
-- WHAT THIS IS NOT: rate limiting. Anonymous insert is open by design, because
-- joining a trip without an account is the entire growth loop (HANDOFF.md 4.1).
-- Nothing here stops someone scripting 10,000 trips. The real fix is an edge
-- function or a captcha in front of trip creation, and it is written up at the
-- bottom of BACKEND.md. Do that before promoting the link widely; these
-- constraints just stop the database filling with garbage in the meantime.
-- ============================================================================

-- ---------------------------------------------------------------- trips -----
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'trips_name_len') then
    alter table public.trips
      add constraint trips_name_len
      check (char_length(name) between 1 and 60);
  end if;

  if not exists (select 1 from pg_constraint where conname = 'trips_code_shape') then
    alter table public.trips
      add constraint trips_code_shape
      check (code ~ '^[a-z0-9]{6,16}$');
  end if;

  if not exists (select 1 from pg_constraint where conname = 'trips_origin_shape') then
    alter table public.trips
      add constraint trips_origin_shape
      check (origin ~ '^[A-Z]{3}$');
  end if;

  -- a trip carries at most 12 custom date ranges; more is not a real trip
  if not exists (select 1 from pg_constraint where conname = 'trips_windows_sane') then
    alter table public.trips
      add constraint trips_windows_sane
      check (jsonb_typeof(windows) = 'array' and jsonb_array_length(windows) <= 12);
  end if;
end $$;

-- -------------------------------------------------------------- members -----
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'members_name_len') then
    alter table public.members
      add constraint members_name_len
      check (char_length(trim(name)) between 1 and 30);
  end if;

  if not exists (select 1 from pg_constraint where conname = 'members_weekends_sane') then
    alter table public.members
      add constraint members_weekends_sane
      check (jsonb_typeof(weekends) = 'array' and jsonb_array_length(weekends) <= 40);
  end if;
end $$;

-- --------------------------------------------------------------- events -----
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'events_name_len') then
    alter table public.events
      add constraint events_name_len
      check (char_length(name) between 1 and 40);
  end if;

  -- analytics props are small by design; this stops the table being used as storage
  if not exists (select 1 from pg_constraint where conname = 'events_props_small') then
    alter table public.events
      add constraint events_props_small
      check (pg_column_size(props) <= 2048);
  end if;
end $$;

-- ------------------------------------------------------------- waitlist -----
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'waitlist_email_shape') then
    alter table public.waitlist
      add constraint waitlist_email_shape
      check (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'
             and char_length(email) <= 200);
  end if;
end $$;

-- -------------------------------------------------------------- profiles ----
-- Handles appear on other people's screens, so keep them boring.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'profiles_handle_shape') then
    alter table public.profiles
      add constraint profiles_handle_shape
      check (handle is null or handle ~ '^[A-Za-z0-9_]{2,20}$');
  end if;

  if not exists (select 1 from pg_constraint where conname = 'profiles_name_len') then
    alter table public.profiles
      add constraint profiles_name_len
      check (name is null or char_length(name) between 1 and 40);
  end if;

  if not exists (select 1 from pg_constraint where conname = 'profiles_home_shape') then
    alter table public.profiles
      add constraint profiles_home_shape
      check (home is null or home ~ '^[A-Z]{3}$');
  end if;
end $$;

-- ----------------------------------------------------------------- crews ----
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'crews_code_shape') then
    alter table public.crews
      add constraint crews_code_shape
      check (code ~ '^FW-[A-Z0-9]{4,10}$');
  end if;
end $$;

-- ============================================================================
-- Housekeeping: events accumulate forever otherwise. Run occasionally, or
-- schedule it with pg_cron if your project has the extension enabled.
-- ============================================================================
-- delete from public.events where created_at < now() - interval '180 days';
