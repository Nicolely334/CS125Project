-- 2) Global preset tags (available to pick from)
create table if not exists public.preset_tags (
  id         bigserial primary key,
  name       text not null unique,
  category   text not null default 'general', -- e.g., mood/activity/energy
  created_at timestamptz not null default now()
);

insert into public.preset_tags (name, category)
values
  -- Mood
  ('happy','mood'),
  ('sad','mood'),
  ('chill','mood'),
  ('calm','mood'),
  ('upbeat','mood'),
  ('emotional','mood'),
  ('dreamy','mood'),
  ('nostalgic','mood'),
  ('dark','mood'),

  -- Activity
  ('study','activity'),
  ('gym','activity'),
  ('work','activity'),
  ('commute','activity'),
  ('sleep','activity'),
  ('party','activity'),
  ('driving','activity'),
  ('walking','activity'),

  -- Energy
  ('low-energy','energy'),
  ('medium-energy','energy'),
  ('high-energy','energy')
on conflict (name) do nothing;
