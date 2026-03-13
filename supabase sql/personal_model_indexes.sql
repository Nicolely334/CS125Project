-- Indexes for personal model queries
-- Run after complete_migration.sql

begin;

-- Index for genre-based queries (for genre preference calculation)
create index if not exists listening_logs_user_genre_idx 
  on public.listening_logs (user_id, genre) 
  where genre is not null;

-- Index for genre + rating queries (weighted genre preferences)
create index if not exists listening_logs_user_genre_rating_idx 
  on public.listening_logs (user_id, genre, rating) 
  where genre is not null and rating is not null;

-- Index for favorite + genre (boost favorite genres)
create index if not exists listening_logs_user_favorite_genre_idx 
  on public.listening_logs (user_id, favorite, genre) 
  where favorite = true and genre is not null;

-- Composite index for recency-weighted queries (logged_at desc)
-- Already exists: listening_logs_user_time_idx, but ensure it's optimal
-- No need to recreate, just documenting it's used for recency weighting

commit;
