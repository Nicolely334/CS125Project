"""Build a personal model from the user's listening_logs in Supabase."""
from collections import Counter
from typing import Any

from app.db.supabase_client import get_supabase


def _normalize_artist(s: str) -> str:
    return (s or "").strip().lower()


def _track_id(artist: str, track: str) -> str:
    return f"{_normalize_artist(artist)}_{(track or '').strip().lower()}".replace(" ", "_").replace("/", "_")


class UserProfile:
    """Personal model: top artists, top tracks, top tags (for seeding), and logged track ids (for reranking)."""

    def __init__(
        self,
        top_artists: list[tuple[str, int]],  # (artist_name, count)
        top_tracks: list[tuple[str, str, int]],  # (track, artist, count)
        logged_track_ids: set[str],
        liked_artists: set[str],
        top_tags: list[tuple[str, int]] | None = None,  # (tag_name, count)
    ):
        self.top_artists = top_artists
        self.top_tracks = top_tracks
        self.logged_track_ids = logged_track_ids
        self.liked_artists = liked_artists
        self.top_tags = top_tags or []
        self._artist_weights = {_normalize_artist(a): (name, c) for name, c in top_artists for a in [name]}
        self._artist_set = set(self._artist_weights.keys())
        self._liked_artist_set = {_normalize_artist(a) for a in (liked_artists or set())}

    def artist_score(self, artist: str) -> float:
        """Weight for a candidate artist (higher if user listens to this artist)."""
        key = _normalize_artist(artist)
        if key not in self._artist_weights:
            return 0.0
        _, count = self._artist_weights[key]
        return min(1.0, count * 0.2)

    def is_logged(self, track_id: str) -> bool:
        return (track_id or "").strip().lower() in self.logged_track_ids

    def is_liked_artist(self, artist: str) -> bool:
        return _normalize_artist(artist) in self._liked_artist_set


def get_user_profile(user_id: str) -> UserProfile | None:
    """
    Load listening_logs for user_id from Supabase and build a personal model.
    Returns None if Supabase is not configured or user has no logs.
    """
    supabase = get_supabase()
    if not supabase:
        return None

    try:
        r = (
            supabase.table("listening_logs")
            .select("id, track_id, track, artist, liked")
            .eq("user_id", user_id)
            .order("logged_at", desc=True)
            .limit(500)
            .execute()
        )
    except Exception:
        return None

    rows = (r.data or [])
    if not rows:
        return None

    log_ids = [row["id"] for row in rows if row.get("id")]

    tag_counts: Counter = Counter()
    if log_ids:
        try:
            lt = supabase.table("log_tags").select("tag_id, user_tag_id").in_("log_id", log_ids).execute()
            preset_counts: Counter = Counter()
            user_tag_id_counts: Counter = Counter()
            for lt_row in (lt.data or []):
                if lt_row.get("tag_id"):
                    preset_counts[lt_row["tag_id"]] += 1
                if lt_row.get("user_tag_id"):
                    user_tag_id_counts[lt_row["user_tag_id"]] += 1
            if preset_counts:
                pt = supabase.table("preset_tags").select("id, name").in_("id", list(preset_counts.keys())).execute()
                for pt_row in (pt.data or []):
                    name = (pt_row.get("name") or "").strip()
                    if name:
                        tag_counts[name] += preset_counts.get(pt_row.get("id"), 0)
            if user_tag_id_counts:
                ut = supabase.table("tags").select("id, name").in_("id", list(user_tag_id_counts.keys())).execute()
                for ut_row in (ut.data or []):
                    name = (ut_row.get("name") or "").strip()
                    if name:
                        tag_counts[name] += user_tag_id_counts.get(ut_row.get("id"), 0)
        except Exception:
            pass

    artist_counts: Counter = Counter()
    track_counts: Counter = Counter()
    logged_ids: set[str] = set()
    liked_artists: set[str] = set()

    for row in rows:
        artist = (row.get("artist") or "").strip()
        track = (row.get("track") or "").strip()
        tid = (row.get("track_id") or _track_id(artist, track)).strip().lower()
        if artist:
            artist_counts[artist] += 1
        if track and artist:
            track_counts[(track, artist)] += 1
        if tid:
            logged_ids.add(tid)
        if row.get("liked") and artist:
            liked_artists.add(artist)

    top_artists = artist_counts.most_common(30)
    top_tracks = [
        (t, a, c) for (t, a), c in track_counts.most_common(50)
    ]
    top_tags_list = [(name, c) for name, c in tag_counts.most_common(20) if name]

    return UserProfile(
        top_artists=top_artists,
        top_tracks=top_tracks,
        logged_track_ids=logged_ids,
        liked_artists=liked_artists,
        top_tags=top_tags_list,
    )
