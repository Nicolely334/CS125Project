"""Build a personal model from the user's listening_logs in Supabase."""
from collections import Counter, defaultdict
from typing import Any, Dict
from datetime import datetime, timezone
import logging

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def _normalize_artist(s: str) -> str:
    return (s or "").strip().lower()


def _normalize_genre(s: str) -> str:
    return (s or "").strip().lower()


def _normalize_tag(s: str) -> str:
    return (s or "").strip().lower()


def _track_id(artist: str, track: str) -> str:
    return f"{_normalize_artist(artist)}_{(track or '').strip().lower()}".replace(" ", "_").replace("/", "_")


def _calculate_recency_weight(logged_at_str: str) -> float:
    """Calculate recency weight: more recent logs have higher weight."""
    try:
        logged_at = datetime.fromisoformat(logged_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        days_ago = (now - logged_at).days
        
        # Recent (last 30 days): 1.5x weight
        if days_ago <= 30:
            return 1.5
        # Medium (31-90 days): 1.0x weight
        elif days_ago <= 90:
            return 1.0
        # Old (91+ days): 0.5x weight
        else:
            return 0.5
    except Exception:
        return 1.0  # Default weight if parsing fails


def _calculate_rating_weight(rating: int | None) -> float:
    """Calculate weight based on rating (1-10 scale)."""
    if rating is None:
        return 1.0
    # Normalize 1-10 to 0.5-2.0 weight range
    return 0.5 + (rating / 10.0) * 1.5


class UserProfile:
    """Enhanced personal model with genre/tag preferences weighted by rating, recency, and favorites."""

    def __init__(
        self,
        top_artists: list[tuple[str, float]],  # (artist_name, weighted_score)
        top_tracks: list[tuple[str, str, float]],  # (track, artist, weighted_score)
        logged_track_ids: set[str],
        liked_artists: set[str],
        top_tags: list[tuple[str, float]] | None = None,  # (tag_name, weighted_score)
        genre_preferences: Dict[str, float] | None = None,  # genre -> weighted_score
    ):
        self.top_artists = top_artists
        self.top_tracks = top_tracks
        self.logged_track_ids = logged_track_ids
        self.liked_artists = liked_artists
        self.top_tags = top_tags or []
        self.genre_preferences = genre_preferences or {}
        
        # Build lookup dictionaries
        self._artist_weights = {_normalize_artist(a): (name, score) for name, score in top_artists for a in [name]}
        self._artist_set = set(self._artist_weights.keys())
        self._liked_artist_set = {_normalize_artist(a) for a in (liked_artists or set())}
        self._genre_weights = {_normalize_genre(g): score for g, score in self.genre_preferences.items()}
        self._tag_weights = {_normalize_tag(t): score for t, score in self.top_tags}

    def artist_score(self, artist: str) -> float:
        """Weight for a candidate artist (higher if user listens to this artist)."""
        key = _normalize_artist(artist)
        if key not in self._artist_weights:
            return 0.0
        _, score = self._artist_weights[key]
        # Normalize to 0-1.0 range (score is typically 1-20 range)
        return min(1.0, score / 20.0)

    def genre_score(self, genre: str) -> float:
        """Weight for a candidate genre (higher if user listens to this genre)."""
        if not genre:
            return 0.0
        key = _normalize_genre(genre)
        score = self._genre_weights.get(key, 0.0)
        # Normalize to 0-1.0 range (score is typically 1-20 range)
        return min(1.0, score / 20.0)

    def tag_score(self, tag: str) -> float:
        """Weight for a candidate tag (higher if user uses this tag)."""
        if not tag:
            return 0.0
        key = _normalize_tag(tag)
        score = self._tag_weights.get(key, 0.0)
        # Normalize to 0-1.0 range
        return min(1.0, score / 20.0)

    def is_logged(self, track_id: str) -> bool:
        return (track_id or "").strip().lower() in self.logged_track_ids

    def is_liked_artist(self, artist: str) -> bool:
        return _normalize_artist(artist) in self._liked_artist_set


def get_user_profile(user_id: str) -> UserProfile | None:
    """
    Load listening_logs for user_id from Supabase and build an enhanced personal model.
    Calculates preferences weighted by rating, recency, and favorites.
    Returns None if Supabase is not configured or user has no logs.
    """
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase client not available")
        return None

    try:
        r = (
            supabase.table("listening_logs")
            .select("id, track_id, track, artist, genre, rating, liked, favorite, logged_at")
            .eq("user_id", user_id)
            .order("logged_at", desc=True)
            .limit(500)
            .execute()
        )
    except Exception as e:
        logger.error(f"Failed to fetch listening_logs: {e}")
        return None

    rows = (r.data or [])
    if not rows:
        logger.warning(f"No listening logs found for user {user_id}")
        return None

    logger.info(f"Loaded {len(rows)} listening logs for user {user_id}")

    log_ids = [row["id"] for row in rows if row.get("id")]

    # Fetch tags for these logs
    tag_counts: Counter = Counter()
    if log_ids:
        try:
            lt = supabase.table("log_tags").select("log_id, tag_id, user_tag_id").in_("log_id", log_ids).execute()
            
            # Map log_id to its tags for weighted calculation
            log_tag_map: Dict[int, list[tuple[str, int]]] = defaultdict(list)
            preset_tag_ids = set()
            user_tag_ids = set()
            
            for lt_row in (lt.data or []):
                log_id = lt_row.get("log_id")
                if lt_row.get("tag_id"):
                    preset_tag_ids.add(lt_row["tag_id"])
                    log_tag_map[log_id].append(("preset", lt_row["tag_id"]))
                if lt_row.get("user_tag_id"):
                    user_tag_ids.add(lt_row["user_tag_id"])
                    log_tag_map[log_id].append(("user", lt_row["user_tag_id"]))
            
            # Fetch preset tag names
            preset_tag_map: Dict[int, str] = {}
            if preset_tag_ids:
                pt = supabase.table("preset_tags").select("id, name").in_("id", list(preset_tag_ids)).execute()
                for pt_row in (pt.data or []):
                    preset_tag_map[pt_row["id"]] = (pt_row.get("name") or "").strip()
            
            # Fetch user tag names
            user_tag_map: Dict[int, str] = {}
            if user_tag_ids:
                ut = supabase.table("tags").select("id, name").in_("id", list(user_tag_ids)).execute()
                for ut_row in (ut.data or []):
                    user_tag_map[ut_row["id"]] = (ut_row.get("name") or "").strip()
            
            # Calculate weighted tag counts
            for row in rows:
                log_id = row.get("id")
                if not log_id:
                    continue
                
                rating = row.get("rating")
                favorite = row.get("favorite", False)
                logged_at = row.get("logged_at", "")
                
                recency_weight = _calculate_recency_weight(logged_at)
                rating_weight = _calculate_rating_weight(rating)
                favorite_boost = 1.5 if favorite else 1.0
                
                total_weight = recency_weight * rating_weight * favorite_boost
                
                for tag_type, tag_id in log_tag_map.get(log_id, []):
                    if tag_type == "preset":
                        tag_name = preset_tag_map.get(tag_id)
                    else:
                        tag_name = user_tag_map.get(tag_id)
                    
                    if tag_name:
                        tag_counts[tag_name] += total_weight
        except Exception as e:
            logger.error(f"Failed to fetch tags: {e}")

    # Calculate weighted preferences
    artist_scores: Dict[str, float] = defaultdict(float)
    track_scores: Dict[tuple[str, str], float] = defaultdict(float)
    genre_scores: Dict[str, float] = defaultdict(float)
    logged_ids: set[str] = set()
    liked_artists: set[str] = set()

    for row in rows:
        artist = (row.get("artist") or "").strip()
        track = (row.get("track") or "").strip()
        genre = (row.get("genre") or "").strip()
        rating = row.get("rating")
        liked = row.get("liked", False)
        favorite = row.get("favorite", False)
        logged_at = row.get("logged_at", "")
        tid = (row.get("track_id") or _track_id(artist, track)).strip().lower()

        # Calculate weights
        recency_weight = _calculate_recency_weight(logged_at)
        rating_weight = _calculate_rating_weight(rating)
        favorite_boost = 1.5 if favorite else 1.0
        total_weight = recency_weight * rating_weight * favorite_boost

        if artist:
            artist_scores[artist] += total_weight
        if track and artist:
            track_scores[(track, artist)] += total_weight
        if genre:
            genre_scores[genre] += total_weight
        if tid:
            logged_ids.add(tid)
        if liked and artist:
            liked_artists.add(artist)

    # Sort and normalize
    top_artists = sorted(artist_scores.items(), key=lambda x: x[1], reverse=True)[:30]
    top_tracks = [
        (t, a, score) for (t, a), score in sorted(track_scores.items(), key=lambda x: x[1], reverse=True)[:50]
    ]
    top_tags_list = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    genre_prefs = dict(sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)[:20])

    logger.info(f"Profile: {len(top_tags_list)} tags, {len(genre_prefs)} genres, {len(top_artists)} artists")
    if top_tags_list:
        logger.info(f"Top tags: {top_tags_list[:5]}")
    if genre_prefs:
        logger.info(f"Top genres: {list(genre_prefs.keys())[:5]}")

    return UserProfile(
        top_artists=top_artists,
        top_tracks=top_tracks,
        logged_track_ids=logged_ids,
        liked_artists=liked_artists,
        top_tags=top_tags_list,
        genre_preferences=genre_prefs,
    )
