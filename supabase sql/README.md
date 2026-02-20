# Database Migration Files

## Setup Order

1. **Base Schema** - Run first:
   - `nondestructive schema.sql` - Creates all base tables, RLS policies, and triggers

2. **Preset Tags** - Run second:
   - `enable row level security and grant global read on preset tags.sql` - Sets up preset_tags table

3. **Complete Migration** - Run third:
   - `complete_migration.sql` - Adds all features:
     - Track metadata (track, artist, genre columns)
     - Favorite column
     - Custom tags support
     - Updated RLS policies

## Optional Files

- `schema reset.sql` - Drops all tables (use with caution!)
- `trigger existence.sql` - Ensures trigger exists
- `default tags for auth users.sql` - Seeds default tags for users

## Notes

- All migrations use `if not exists` / `if exists` checks - safe to run multiple times
- RLS policies are automatically enforced
- Custom tags are per-user and isolated via RLS
