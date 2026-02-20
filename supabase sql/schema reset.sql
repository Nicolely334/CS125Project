-- DESTRUCTIVE: removes existing tables/policies/data for this MVP schema
-- Use only if you are OK losing existing MusicBoxd data.

drop table if exists public.log_tags cascade;
drop table if exists public.listening_logs cascade;
drop table if exists public.tags cascade;
drop table if exists public.user_preferences cascade;
drop table if exists public.spotify_tracks cascade; -- if you created it earlier
drop table if exists public.profiles cascade;

-- Also remove triggers/functions if you want a full clean slate
drop trigger if exists on_auth_user_created on auth.users;
drop function if exists public.handle_new_user();
drop function if exists public.touch_last_fetched_at();
