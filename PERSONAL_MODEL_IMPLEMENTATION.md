# Personal Model Implementation

## Overview

The personal model system uses user listening history to personalize search results and recommendations. It calculates preferences from:
- **Genres**: Weighted by frequency, ratings, recency, and favorites
- **Tags**: Weighted by usage frequency, associated ratings, recency, and favorites
- **Artists**: Weighted by frequency, ratings, recency, and favorites

## Database Changes

### SQL Migration: `supabase sql/personal_model_indexes.sql`

Added indexes for faster personal model queries:
- `listening_logs_user_genre_idx` - Genre-based queries
- `listening_logs_user_genre_rating_idx` - Genre + rating queries
- `listening_logs_user_favorite_genre_idx` - Favorite genres

**Run this migration:**
```sql
-- Run: supabase sql/personal_model_indexes.sql
```

## Code Structure

### 1. Enhanced User Profile (`app/services/user_profile.py`)

**New Features:**
- **Genre Preferences**: Calculated from `listening_logs.genre`, weighted by:
  - Rating (1-10 scale → 0.5-2.0x weight)
  - Recency (last 30 days: 1.5x, 31-90 days: 1.0x, 91+ days: 0.5x)
  - Favorites (1.5x boost)
- **Tag Preferences**: Calculated from `log_tags`, weighted similarly
- **Artist Preferences**: Enhanced with rating/recency/favorite weighting

**Methods:**
- `genre_score(genre: str) -> float` - Get preference score for a genre
- `tag_score(tag: str) -> float` - Get preference score for a tag
- `artist_score(artist: str) -> float` - Enhanced artist preference score

### 2. Search Enrichment (`app/services/search_enrichment.py`)

**Functions:**
- `extract_tags_from_track_info()` - Extract tags from Last.fm `track.getInfo`
- `extract_genre_from_track_info()` - Extract genre (uses first tag as proxy)
- `enrich_track_with_info()` - Enrich track with metadata from `track.getInfo`

### 3. Personal Model Scoring (`app/services/personal_model.py`)

**Functions:**
- `score_search_result()` - Score search results using:
  - Genre preference match (30%)
  - Tag alignment (25%)
  - Artist affinity (25%)
  - Liked artist boost (+10%)
  - Already logged penalty (-50%)
  
- `score_discover_item()` - Score discover recommendations using:
  - Genre preference (25%)
  - Tag alignment (25%)
  - Artist affinity (20%)
  - Last.fm match score (15%)
  - Liked artist boost (+10%)
  - Already logged penalty (-50%)

### 4. Last.fm Service (`app/services/lastfm_service.py`)

**New Function:**
- `track_get_info()` - Calls Last.fm `track.getInfo` API to get tags/genre

### 5. Search Endpoint (`app/api/routes/search.py`)

**Enhanced:**
- Accepts optional `user_id` parameter
- If `user_id` provided:
  1. Enriches results with `track.getInfo` (tags/genre)
  2. Reranks using personal model
- Returns personalized results

**Usage:**
```
GET /api/search?q=believe&user_id=<uuid>
```

### 6. Discover Recommendations (`app/services/discover_recommendations.py`)

**Enhanced:**
- After gathering candidates, reranks by personal model if `user_id` provided
- Uses `score_discover_item()` for scoring

## How It Works

### Search Reranking Flow

1. User searches for tracks
2. Get initial results from `track.search`
3. If `user_id` provided:
   - For each result, call `track.getInfo` to get tags/genre
   - Load user profile (genre/tag/artist preferences)
   - Score each result using personal model
   - Sort by score (highest first)
4. Return top N results

### Discover Reranking Flow

1. Gather candidates from:
   - User's top artists (similar artists)
   - User's top tags (tag.getTopArtists/Tracks/Albums)
   - Global charts
2. If `user_id` provided:
   - Load user profile
   - Score each candidate using personal model
   - Sort by score (highest first)
3. Return top N results

## Weighting Formula

### Preference Calculation

For each genre/tag/artist:
```
weight = recency_weight × rating_weight × favorite_boost
```

Where:
- `recency_weight`: 1.5 (recent), 1.0 (medium), 0.5 (old)
- `rating_weight`: 0.5 + (rating/10) × 1.5 (normalized 1-10 to 0.5-2.0)
- `favorite_boost`: 1.5 if favorited, 1.0 otherwise

### Scoring Formula

**Search Results:**
```
score = 0.3 × genre_match + 0.25 × tag_alignment + 0.25 × artist_affinity 
      + 0.1 × liked_artist_boost - 0.5 × already_logged_penalty
```

**Discover Items:**
```
score = 0.25 × genre_preference + 0.25 × tag_alignment + 0.2 × artist_affinity
      + 0.15 × lastfm_match_score + 0.1 × liked_artist_boost 
      - 0.5 × already_logged_penalty
```

## Environment Variables

The backend needs:
```
VITE_SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

**Note:** The service role key is different from the anon key. It's needed for backend admin access to read `listening_logs` for all users.

## Testing

1. **Run SQL migration:**
   ```sql
   -- In Supabase SQL editor, run:
   -- supabase sql/personal_model_indexes.sql
   ```

2. **Test search with personalization:**
   ```
   GET /api/search?q=believe&user_id=<your-user-id>
   ```

3. **Test discover with personalization:**
   ```
   GET /api/recommendations/discover?user_id=<your-user-id>
   ```

## Performance Considerations

- **Caching**: Consider caching `track.getInfo` results (tags don't change often)
- **Rate Limiting**: Last.fm has rate limits (~5 req/sec); implement throttling if needed
- **Async**: Could use async requests for parallel `track.getInfo` calls
- **Fallback**: If enrichment fails, uses original track data (no tags/genre)

## Future Enhancements

- Cache computed preferences in `user_preferences` table
- Add genre extraction from Last.fm wiki content
- Implement async batch enrichment
- Add preference decay over time
- Support multiple genre tags per track
