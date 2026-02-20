-- Auto-seed default tags for each new user profile
-- Safe to run multiple times

create or replace function public.seed_default_tags_for_user(p_user_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.tags (user_id, name)
  select p_user_id, v.name
  from (
    values
      -- Mood
      ('happy'),
      ('sad'),
      ('chill'),
      ('calm'),
      ('upbeat'),
      ('emotional'),
      ('dreamy'),
      ('nostalgic'),
      ('dark'),

      -- Activity
      ('study'),
      ('gym'),
      ('work'),
      ('commute'),
      ('sleep'),
      ('party'),
      ('driving'),
      ('walking'),

      -- Energy
      ('low-energy'),
      ('medium-energy'),
      ('high-energy')
  ) as v(name)
  on conflict (user_id, lower(name)) do nothing;
end;
$$;

create or replace function public.after_profile_insert_seed_tags()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.seed_default_tags_for_user(new.id);
  return new;
end;
$$;

do $$
begin
  if not exists (
    select 1
    from pg_trigger
    where tgname = 'profiles_seed_default_tags'
  ) then
    create trigger profiles_seed_default_tags
    after insert on public.profiles
    for each row execute procedure public.after_profile_insert_seed_tags();
  end if;
end $$;
