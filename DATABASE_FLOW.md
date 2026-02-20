# Database Interaction Flow

## How Profiles Are Stored

### Automatic Profile Creation

When a user signs up through Supabase Auth:

1. **User signs up** → Supabase creates a record in `auth.users` table
2. **Database trigger fires** → The `on_auth_user_created` trigger automatically executes
3. **Profile created** → A corresponding record is inserted into `public.profiles` table

```sql
-- This trigger runs automatically when a new user is created
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();
```

The trigger function (`handle_new_user()`) does:
- Extracts user info from `auth.users` (email, full_name, avatar_url)
- Inserts into `public.profiles` with the same `id` (UUID from auth.users)
- Uses `on conflict do nothing` to prevent duplicates

**Profile Table Structure:**
```sql
create table public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  avatar_url   text,
  created_at   timestamptz not null default now()
);
```

**Key Point:** The profile `id` is the same UUID as the `auth.users.id`, creating a 1:1 relationship.

---

## How Songs Are Logged

### Frontend Flow

1. **User searches for a song** → SearchPage calls the Last.fm API via backend
2. **User clicks ➕ button** → `handleLogSong()` function is called
3. **Frontend calls Supabase directly** → Uses the authenticated Supabase client

### Code Flow:

```typescript
// In SearchPage.tsx
async function handleLogSong(track: Track) {
  await logSong({
    track_id: track.id,      // e.g., "artist_track_name" or Last.fm mbid
    track: track.track,      // Track name
    artist: track.artist,     // Artist name
    liked: false,
  });
}
```

```typescript
// In logs.ts service
export async function logSong(params: LogSongParams) {
  const { data, error } = await supabase
    .from('listening_logs')
    .insert({
      track_id: params.track_id,
      rating: params.rating,
      liked: params.liked ?? false,
      notes: params.notes,
    })
    .select()
    .single();
  
  return data;
}
```

### Database Insert

The Supabase client (with user's JWT token) inserts into `listening_logs`:

```sql
INSERT INTO public.listening_logs (
  user_id,      -- Automatically set by RLS from auth.uid()
  track_id,     -- The track identifier (e.g., Last.fm mbid)
  rating,       -- Optional 1-10 rating
  liked,        -- Boolean
  notes,        -- Optional text notes
  logged_at     -- Automatically set to now()
)
VALUES (...)
```

**Listening Logs Table Structure:**
```sql
create table public.listening_logs (
  id        bigserial primary key,
  user_id   uuid not null references public.profiles (id) on delete cascade,
  track_id  text not null,
  rating    smallint check (rating is null or (rating between 1 and 10)),
  liked     boolean not null default false,
  notes     text,
  logged_at timestamptz not null default now()
);
```

---

## Security: Row Level Security (RLS)

### How RLS Works

Supabase uses **Row Level Security (RLS)** to ensure users can only access their own data.

### For Listening Logs:

**Insert Policy:**
```sql
create policy logs_insert_own on public.listening_logs
for insert with check (user_id = auth.uid());
```
- When inserting, Supabase automatically sets `user_id = auth.uid()` (current user's ID)
- Users can ONLY insert logs with their own user_id

**Select Policy:**
```sql
create policy logs_select_own on public.listening_logs
for select using (user_id = auth.uid());
```
- Users can ONLY see logs where `user_id` matches their authenticated user ID
- Other users' logs are invisible

**Update/Delete Policies:**
- Similar restrictions - users can only modify/delete their own logs

### How It Works in Practice:

1. **User authenticates** → Supabase client gets a JWT token with `user_id`
2. **Frontend makes request** → JWT token is automatically included in headers
3. **Supabase checks RLS** → Before returning data, filters by `auth.uid()`
4. **User only sees their data** → Even if they try to query all logs, RLS filters results

**Example:**
```typescript
// User A queries logs
const logs = await supabase.from('listening_logs').select('*');
// Returns: Only User A's logs (RLS automatically filters)

// User B queries logs  
const logs = await supabase.from('listening_logs').select('*');
// Returns: Only User B's logs (different user, different results)
```

---

## Complete Flow Diagram

```
┌─────────────────┐
│  User Signs Up  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Supabase Auth.users    │
│  (auth schema)          │
└────────┬────────────────┘
         │
         │ Trigger fires
         ▼
┌─────────────────────────┐
│  public.profiles        │
│  id = auth.users.id     │
│  display_name, etc.     │
└─────────────────────────┘

┌─────────────────┐
│  User Searches  │
│  for Song       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Backend API            │
│  /api/search            │
│  (Last.fm API)         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Search Results         │
│  Displayed in UI        │
└────────┬────────────────┘
         │
         │ User clicks ➕
         ▼
┌─────────────────────────┐
│  Frontend: logSong()    │
│  Supabase Client       │
│  (with JWT token)       │
└────────┬────────────────┘
         │
         │ INSERT with RLS
         ▼
┌─────────────────────────┐
│  public.listening_logs  │
│  user_id = auth.uid()   │
│  track_id, rating, etc. │
└─────────────────────────┘
```

---

## Key Points

1. **Profiles are automatic** - No manual profile creation needed
2. **Direct database access** - Frontend calls Supabase directly (no backend proxy needed)
3. **RLS handles security** - Users can't see or modify other users' data
4. **JWT tokens** - Supabase client automatically includes auth tokens
5. **Cascade deletes** - If a user is deleted, their profile and logs are automatically deleted

---

## Tags System

### Preset Tags
- Global tags available to all users (mood, activity, energy)
- Stored in `preset_tags` table
- Read-only for users (RLS allows SELECT only)

### Custom Tags
- User-created tags stored in `tags` table
- Each user can create their own tags
- RLS policies ensure users can only access their own tags

### Tagging Songs
- `log_tags` table links songs to tags
- Supports both preset tags (`tag_id`) and custom tags (`user_tag_id`)
- Users can add multiple tags to each logged song

---

## Environment Variables Required

For the frontend to connect to Supabase:
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

The anon key is safe to expose in frontend code - RLS policies prevent unauthorized access.
