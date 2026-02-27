"""Personal recommendations: seed from user's listening_logs, fetch candidates from Last.fm, rerank by personal model."""
from typing import Any, Dict, List, Optional

from app.services.user_profile import UserProfile, get_user_profile, _track_id
from app.services.lastfm_service import track_get_similar, artist_get_similar


def _extract_string(field_value: Any) -> str:
    if isinstance(field_value, dict):
        return str(field_value.get("name", field_value.get("#text", ""))).strip()
    return str(field_value).strip() if field_value else ""


def _normalize_track(track_data: Dict[str, Any], reason: str, match_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
    track_name = _extract_string(track_data.get("name", ""))
    artist_name = _extract_string(track_data.get("artist", ""))
    if not track_name or not artist_name:
        return None
    mbid = _extract_string(track_data.get("mbid", ""))
    tid = mbid if mbid else _track_id(artist_name, track_name)
    return {
        "track": track_name,
        "artist": artist_name,
        "id": tid,
        "reason": reason,
        "match_score": match_score,
    }


def _normalize_artist_placeholder(artist_data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
    artist_name = _extract_string(artist_data.get("name", ""))
    if not artist_name:
        return None
    mbid = _extract_string(artist_data.get("mbid", ""))
    aid = mbid if mbid else artist_name.lower().replace(" ", "_").replace("/", "_")
    return {
        "track": f"Artist: {artist_name}",
        "artist": artist_name,
        "id": aid,
        "reason": reason,
        "match_score": None,
    }


def _gather_candidates(profile: UserProfile, limit_per_seed: int) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    candidates: List[Dict[str, Any]] = []

    # Seed from top tracks (similar tracks)
    for track, artist, _ in (profile.top_tracks[:5] or []):
        try:
            data = track_get_similar(track=track, artist=artist, limit=limit_per_seed)
            tracks = data.get("similartracks", {}).get("track", []) or []
            if isinstance(tracks, dict):
                tracks = [tracks]
            for t in tracks:
                ms = t.get("match")
                try:
                    ms = float(ms) if ms is not None else None
                except (TypeError, ValueError):
                    ms = None
                rec = _normalize_track(t, reason=f"Similar to {track}", match_score=ms)
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    candidates.append(rec)
        except Exception:
            continue

    # Seed from top artists (similar artists – as placeholders)
    for (artist_name, _) in (profile.top_artists[:5] or []):
        try:
            data = artist_get_similar(artist=artist_name, limit=limit_per_seed)
            artists = data.get("similarartists", {}).get("artist", []) or []
            if isinstance(artists, dict):
                artists = [artists]
            for a in artists:
                rec = _normalize_artist_placeholder(a, reason=f"Similar to {artist_name}")
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    candidates.append(rec)
        except Exception:
            continue

    return candidates


def _rerank_by_personal_model(candidates: List[Dict[str, Any]], profile: UserProfile) -> List[Dict[str, Any]]:
    """Score and sort by personal model: artist affinity, liked artist boost, already-logged penalty, Last.fm match."""
    scored = []
    for c in candidates:
        artist = c.get("artist") or ""
        tid = (c.get("id") or "").strip().lower()
        lfm = c.get("match_score")
        lfm_norm = min(1.0, max(0.0, (lfm or 0.0) / 100.0))

        score = 0.0
        score += profile.artist_score(artist)
        if profile.is_liked_artist(artist):
            score += 0.5
        if profile.is_logged(tid):
            score -= 1.0
        score += 0.3 * lfm_norm

        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def get_personal_recommendations(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recommendations personalized to the user: build profile from listening_logs,
    gather candidates from Last.fm (similar to user's top tracks/artists), rerank by personal model.
    Returns list of { track, artist, id, reason, match_score } with source="lastfm" implied.
    """
    profile = get_user_profile(user_id)
    if not profile:
        return []

    candidates = _gather_candidates(profile, limit_per_seed=10)
    if not candidates:
        return []

    reranked = _rerank_by_personal_model(candidates, profile)
    out = []
    for c in reranked[:limit]:
        out.append({
            "track": c["track"],
            "artist": c["artist"],
            "id": c["id"],
            "source": "lastfm",
            "reason": c.get("reason"),
            "match_score": c.get("match_score"),
        })
    return out
