-- Artist logs schema aligned with existing song log structure.
-- Mirrors:
-- - listening_logs ownership via public.profiles(id)
-- - log_tags style (preset tag_id + custom user_tag_id)
-- - RLS policy pattern
-- Safe to run multiple times.

begin;

-- =========================
-- 1) artist_logs (same pattern as listening_logs)
-- =========================
create table if not exists public.artist_logs (
  id          bigserial primary key,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  artist_id   text not null,
  artist_name text not null,
  genre       text,
  genres      text[] not null default '{}'::text[],
  liked       boolean not null default false,
  favorite    boolean not null default false,
  notes       text,
  source      text not null default 'lastfm',
  logged_at   timestamptz not null default now(),
  created_at  timestamptz not null default now()
);

-- Patch existing table if earlier version differs
alter table public.artist_logs
  add column if not exists artist_id text,
  add column if not exists artist_name text,
  add column if not exists genre text,
  add column if not exists genres text[] default '{}'::text[],
  add column if not exists liked boolean not null default false,
  add column if not exists favorite boolean not null default false,
  add column if not exists notes text,
  add column if not exists source text not null default 'lastfm',
  add column if not exists logged_at timestamptz not null default now(),
  add column if not exists created_at timestamptz not null default now();

create index if not exists artist_logs_user_time_idx on public.artist_logs (user_id, logged_at desc);
create index if not exists artist_logs_user_artist_idx on public.artist_logs (user_id, artist_id);
create index if not exists artist_logs_artist_idx on public.artist_logs (artist_id);
create index if not exists artist_logs_user_favorite_idx
  on public.artist_logs (user_id, favorite)
  where favorite = true;

-- =========================
-- 2) artist_log_tags (same structure as log_tags: log_id, tag_id, user_tag_id)
-- =========================
create table if not exists public.artist_log_tags (
  log_id bigint not null references public.artist_logs (id) on delete cascade,
  tag_id bigint references public.preset_tags (id) on delete cascade,
  user_tag_id bigint references public.tags (id) on delete cascade
);

-- If old schema used artist_log_id, rename it to log_id
do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='artist_log_tags' and column_name='artist_log_id'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='artist_log_tags' and column_name='log_id'
  ) then
    alter table public.artist_log_tags rename column artist_log_id to log_id;
  end if;
end $$;

alter table public.artist_log_tags
  add column if not exists log_id bigint references public.artist_logs (id) on delete cascade;

-- Ensure custom-tag support + check constraint (same style as complete_migration.sql)
alter table public.artist_log_tags
  add column if not exists user_tag_id bigint references public.tags (id) on delete cascade;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'artist_log_tags_tag_check'
      and conrelid = 'public.artist_log_tags'::regclass
  ) then
    alter table public.artist_log_tags
      add constraint artist_log_tags_tag_check
      check ((tag_id is not null) or (user_tag_id is not null));
  end if;
end $$;

create index if not exists artist_log_tags_tag_idx on public.artist_log_tags (tag_id);
create index if not exists artist_log_tags_user_tag_idx on public.artist_log_tags (user_tag_id);
create index if not exists artist_log_tags_log_idx on public.artist_log_tags (log_id);

-- Prevent duplicate preset/custom tag attachments per artist log
create unique index if not exists artist_log_tags_artist_tag_uniq
  on public.artist_log_tags (log_id, tag_id)
  where tag_id is not null;
create unique index if not exists artist_log_tags_artist_user_tag_uniq
  on public.artist_log_tags (log_id, user_tag_id)
  where user_tag_id is not null;

-- =========================
-- 3) RLS (mirrors listening_logs + log_tags policy style)
-- =========================
alter table public.artist_logs enable row level security;
alter table public.artist_log_tags enable row level security;

drop policy if exists artist_logs_select_own on public.artist_logs;
create policy artist_logs_select_own on public.artist_logs
for select using (user_id = auth.uid());

drop policy if exists artist_logs_insert_own on public.artist_logs;
create policy artist_logs_insert_own on public.artist_logs
for insert with check (user_id = auth.uid());

drop policy if exists artist_logs_update_own on public.artist_logs;
create policy artist_logs_update_own on public.artist_logs
for update using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists artist_logs_delete_own on public.artist_logs;
create policy artist_logs_delete_own on public.artist_logs
for delete using (user_id = auth.uid());

drop policy if exists artist_log_tags_select_own on public.artist_log_tags;
create policy artist_log_tags_select_own on public.artist_log_tags
for select using (
  exists (
    select 1
    from public.artist_logs al
    where al.id = artist_log_tags.log_id
      and al.user_id = auth.uid()
  )
);

drop policy if exists artist_log_tags_insert_own on public.artist_log_tags;
create policy artist_log_tags_insert_own on public.artist_log_tags
for insert with check (
  exists (
    select 1
    from public.artist_logs al
    where al.id = artist_log_tags.log_id
      and al.user_id = auth.uid()
  )
  and (
    (artist_log_tags.tag_id is not null)
    or
    (artist_log_tags.user_tag_id is not null and exists (
      select 1 from public.tags t
      where t.id = artist_log_tags.user_tag_id
        and t.user_id = auth.uid()
    ))
  )
);

drop policy if exists artist_log_tags_delete_own on public.artist_log_tags;
create policy artist_log_tags_delete_own on public.artist_log_tags
for delete using (
  exists (
    select 1
    from public.artist_logs al
    where al.id = artist_log_tags.log_id
      and al.user_id = auth.uid()
  )
);

commit;
