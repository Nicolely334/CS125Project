-- Complete database migration
-- Run this after the base schema to add all features

begin;

-- 1) Add track metadata columns to listening_logs
alter table public.listening_logs
  add column if not exists track text,
  add column if not exists artist text,
  add column if not exists genre text;

-- 2) Add favorite column
alter table public.listening_logs
  add column if not exists favorite boolean not null default false;

create index if not exists listening_logs_user_favorite_idx 
  on public.listening_logs (user_id, favorite) 
  where favorite = true;

-- 3) Ensure tags table exists for custom tags
create table if not exists public.tags (
  id         bigserial primary key,
  user_id    uuid not null references public.profiles (id) on delete cascade,
  name       text not null,
  created_at timestamptz not null default now()
);

create unique index if not exists tags_user_lower_name_uniq
  on public.tags (user_id, lower(name));

create index if not exists tags_user_idx on public.tags (user_id);

-- 4) Add user_tag_id to log_tags for custom tags
alter table public.log_tags
  add column if not exists user_tag_id bigint references public.tags (id) on delete cascade;

-- 5) Make tag_id nullable (can use either preset or custom tag)
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='log_tags' and column_name='tag_id'
      and is_nullable='NO'
  ) then
    alter table public.log_tags
      add constraint if not exists log_tags_tag_check
      check ((tag_id is not null) or (user_tag_id is not null));
    
    alter table public.log_tags
      alter column tag_id drop not null;
  end if;
end $$;

-- 6) RLS policies for tags table
alter table public.tags enable row level security;

drop policy if exists tags_select_own on public.tags;
create policy tags_select_own on public.tags
for select using (user_id = auth.uid());

drop policy if exists tags_insert_own on public.tags;
create policy tags_insert_own on public.tags
for insert with check (user_id = auth.uid());

drop policy if exists tags_update_own on public.tags;
create policy tags_update_own on public.tags
for update using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists tags_delete_own on public.tags;
create policy tags_delete_own on public.tags
for delete using (user_id = auth.uid());

-- 7) Update log_tags insert policy to support both preset and custom tags
drop policy if exists log_tags_insert_own on public.log_tags;
create policy log_tags_insert_own on public.log_tags
for insert with check (
  exists (
    select 1 from public.listening_logs l
    where l.id = log_tags.log_id and l.user_id = auth.uid()
  )
  and (
    (log_tags.tag_id is not null)
    or
    (log_tags.user_tag_id is not null and exists (
      select 1 from public.tags t
      where t.id = log_tags.user_tag_id and t.user_id = auth.uid()
    ))
  )
);

commit;
