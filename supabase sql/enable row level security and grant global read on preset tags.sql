begin;

-- ------------------------------------------------------------
-- 0) Remove old log_tags policies (they depend on old tag_id -> tags)
-- ------------------------------------------------------------
drop policy if exists log_tags_select_own on public.log_tags;
drop policy if exists log_tags_insert_own on public.log_tags;
drop policy if exists log_tags_delete_own on public.log_tags;

-- ------------------------------------------------------------
-- 1) Create global preset_tags + seed defaults
-- ------------------------------------------------------------
create table if not exists public.preset_tags (
  id         bigserial primary key,
  name       text not null unique,
  category   text not null default 'general',
  created_at timestamptz not null default now()
);

insert into public.preset_tags (name, category)
values
  -- Mood
  ('happy','mood'), ('sad','mood'), ('chill','mood'), ('calm','mood'), ('upbeat','mood'),
  ('emotional','mood'), ('dreamy','mood'), ('nostalgic','mood'), ('dark','mood'),
  -- Activity
  ('study','activity'), ('gym','activity'), ('work','activity'), ('commute','activity'),
  ('sleep','activity'), ('party','activity'), ('driving','activity'), ('walking','activity'),
  -- Energy
  ('low-energy','energy'), ('medium-energy','energy'), ('high-energy','energy')
on conflict (name) do nothing;

-- preset_tags is safe to read publicly
alter table public.preset_tags enable row level security;
drop policy if exists preset_tags_read_all on public.preset_tags;
create policy preset_tags_read_all
on public.preset_tags for select
using (true);

-- ------------------------------------------------------------
-- 2) Convert log_tags to point to preset_tags
-- ------------------------------------------------------------

-- Add new column for preset reference
alter table public.log_tags
  add column if not exists preset_tag_id bigint;

-- Add FK to preset_tags (if not already there)
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'log_tags_preset_tag_id_fkey'
      and conrelid = 'public.log_tags'::regclass
  ) then
    alter table public.log_tags
      add constraint log_tags_preset_tag_id_fkey
      foreign key (preset_tag_id) references public.preset_tags(id)
      on delete cascade;
  end if;
end $$;

-- If old tags table + old log_tags.tag_id exist, migrate by tag name
do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='log_tags' and column_name='tag_id'
  ) and exists (
    select 1
    from information_schema.tables
    where table_schema='public' and table_name='tags'
  ) then
    update public.log_tags lt
    set preset_tag_id = pt.id
    from public.tags t
    join public.preset_tags pt on lower(pt.name) = lower(t.name)
    where lt.tag_id = t.id
      and lt.preset_tag_id is null;
  end if;
end $$;

-- Drop old FK constraints that reference public.tags, then drop old tag_id column
do $$
declare
  cname text;
begin
  for cname in
    select conname
    from pg_constraint
    where conrelid = 'public.log_tags'::regclass
      and contype = 'f'
      and pg_get_constraintdef(oid) ilike '%references public.tags%'
  loop
    execute format('alter table public.log_tags drop constraint if exists %I;', cname);
  end loop;

  if exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='log_tags' and column_name='tag_id'
  ) then
    alter table public.log_tags drop column tag_id;
  end if;
end $$;

-- Require preset_tag_id (OK since you said the DB is empty)
alter table public.log_tags
  alter column preset_tag_id set not null;

-- Rename preset_tag_id -> tag_id (so your app still uses log_tags.tag_id)
do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='log_tags' and column_name='preset_tag_id'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema='public' and table_name='log_tags' and column_name='tag_id'
  ) then
    alter table public.log_tags rename column preset_tag_id to tag_id;
  end if;
end $$;

-- ------------------------------------------------------------
-- 3) Recreate NEW log_tags policies (only depend on listening_logs ownership)
-- ------------------------------------------------------------
alter table public.log_tags enable row level security;

create policy log_tags_select_own
on public.log_tags for select
using (
  exists (
    select 1
    from public.listening_logs l
    where l.id = log_tags.log_id
      and l.user_id = auth.uid()
  )
);

create policy log_tags_insert_own
on public.log_tags for insert
with check (
  exists (
    select 1
    from public.listening_logs l
    where l.id = log_tags.log_id
      and l.user_id = auth.uid()
  )
);

create policy log_tags_delete_own
on public.log_tags for delete
using (
  exists (
    select 1
    from public.listening_logs l
    where l.id = log_tags.log_id
      and l.user_id = auth.uid()
  )
);

-- ------------------------------------------------------------
-- 4) Drop the old per-user tags table (not needed anymore)
-- ------------------------------------------------------------
drop table if exists public.tags cascade;

commit;
