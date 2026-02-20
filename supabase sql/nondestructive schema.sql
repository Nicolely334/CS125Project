-- MusicBoxd – Simple MVP schema (frontend can write directly)
-- Tables: profiles, listening_logs, tags, log_tags, user_preferences
-- No spotify_tracks, no destructive DROPs.

create extension if not exists pgcrypto;

-- -------------------------
-- 1) Profiles (auth.users -> profiles)
-- -------------------------
create table if not exists public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  avatar_url   text,
  created_at   timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', new.email),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do nothing;

  return new;
end;
$$;

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'on_auth_user_created') then
    create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();
  end if;
end $$;

-- -------------------------
-- 2) Listening logs (store ONLY spotify track_id + user feedback)
-- -------------------------
create table if not exists public.listening_logs (
  id        bigserial primary key,
  user_id   uuid not null references public.profiles (id) on delete cascade,
  track_id  text not null, -- Spotify track id (no FK so frontend can log instantly)
  rating    smallint check (rating is null or (rating between 1 and 10)),
  liked     boolean not null default false,
  notes     text,
  logged_at timestamptz not null default now()
);

create index if not exists listening_logs_user_time_idx   on public.listening_logs (user_id, logged_at desc);
create index if not exists listening_logs_user_track_idx  on public.listening_logs (user_id, track_id);
create index if not exists listening_logs_track_idx       on public.listening_logs (track_id);
create index if not exists listening_logs_user_rating_idx on public.listening_logs (user_id, rating);

-- -------------------------
-- 3) Tags (per-user) + join table
-- -------------------------
create table if not exists public.tags (
  id         bigserial primary key,
  user_id    uuid not null references public.profiles (id) on delete cascade,
  name       text not null,
  created_at timestamptz not null default now()
);

create unique index if not exists tags_user_lower_name_uniq
  on public.tags (user_id, lower(name));

create index if not exists tags_user_idx on public.tags (user_id);

create table if not exists public.log_tags (
  log_id bigint not null references public.listening_logs (id) on delete cascade,
  tag_id bigint not null references public.tags (id) on delete cascade,
  primary key (log_id, tag_id)
);

create index if not exists log_tags_tag_idx on public.log_tags (tag_id);
create index if not exists log_tags_log_idx on public.log_tags (log_id);

-- -------------------------
-- 4) Explicit preferences (optional MVP, but useful for onboarding)
-- -------------------------
create table if not exists public.user_preferences (
  id         bigserial primary key,
  user_id    uuid not null references public.profiles (id) on delete cascade,
  pref_type  text not null check (pref_type in ('artist','genre','track')),
  value      text not null,
  weight     real not null default 1.0,
  created_at timestamptz not null default now()
);

create unique index if not exists user_prefs_unique
  on public.user_preferences (user_id, pref_type, value);

create index if not exists user_prefs_user_type_idx
  on public.user_preferences (user_id, pref_type);

-- -------------------------
-- 5) Enable RLS
-- -------------------------
alter table public.profiles enable row level security;
alter table public.listening_logs enable row level security;
alter table public.tags enable row level security;
alter table public.log_tags enable row level security;
alter table public.user_preferences enable row level security;

-- -------------------------
-- 6) Policies (created only if missing)
-- -------------------------
do $$
begin
  -- profiles
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='profiles' and policyname='profiles_select_own') then
    create policy profiles_select_own on public.profiles
    for select using (id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='profiles' and policyname='profiles_update_own') then
    create policy profiles_update_own on public.profiles
    for update using (id = auth.uid()) with check (id = auth.uid());
  end if;

  -- logs
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='listening_logs' and policyname='logs_select_own') then
    create policy logs_select_own on public.listening_logs
    for select using (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='listening_logs' and policyname='logs_insert_own') then
    create policy logs_insert_own on public.listening_logs
    for insert with check (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='listening_logs' and policyname='logs_update_own') then
    create policy logs_update_own on public.listening_logs
    for update using (user_id = auth.uid()) with check (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='listening_logs' and policyname='logs_delete_own') then
    create policy logs_delete_own on public.listening_logs
    for delete using (user_id = auth.uid());
  end if;

  -- tags
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='tags' and policyname='tags_select_own') then
    create policy tags_select_own on public.tags
    for select using (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='tags' and policyname='tags_insert_own') then
    create policy tags_insert_own on public.tags
    for insert with check (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='tags' and policyname='tags_update_own') then
    create policy tags_update_own on public.tags
    for update using (user_id = auth.uid()) with check (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='tags' and policyname='tags_delete_own') then
    create policy tags_delete_own on public.tags
    for delete using (user_id = auth.uid());
  end if;

  -- log_tags (must own both log and tag)
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='log_tags' and policyname='log_tags_select_own') then
    create policy log_tags_select_own on public.log_tags
    for select using (
      exists (
        select 1
        from public.listening_logs l
        join public.tags t on t.id = log_tags.tag_id
        where l.id = log_tags.log_id
          and l.user_id = auth.uid()
          and t.user_id = auth.uid()
      )
    );
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='log_tags' and policyname='log_tags_insert_own') then
    create policy log_tags_insert_own on public.log_tags
    for insert with check (
      exists (
        select 1
        from public.listening_logs l
        join public.tags t on t.id = log_tags.tag_id
        where l.id = log_tags.log_id
          and l.user_id = auth.uid()
          and t.user_id = auth.uid()
      )
    );
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='log_tags' and policyname='log_tags_delete_own') then
    create policy log_tags_delete_own on public.log_tags
    for delete using (
      exists (
        select 1
        from public.listening_logs l
        join public.tags t on t.id = log_tags.tag_id
        where l.id = log_tags.log_id
          and l.user_id = auth.uid()
          and t.user_id = auth.uid()
      )
    );
  end if;

  -- preferences
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='user_preferences' and policyname='prefs_select_own') then
    create policy prefs_select_own on public.user_preferences
    for select using (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='user_preferences' and policyname='prefs_insert_own') then
    create policy prefs_insert_own on public.user_preferences
    for insert with check (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='user_preferences' and policyname='prefs_update_own') then
    create policy prefs_update_own on public.user_preferences
    for update using (user_id = auth.uid()) with check (user_id = auth.uid());
  end if;

  if not exists (select 1 from pg_policies where schemaname='public' and tablename='user_preferences' and policyname='prefs_delete_own') then
    create policy prefs_delete_own on public.user_preferences
    for delete using (user_id = auth.uid());
  end if;
end $$;
