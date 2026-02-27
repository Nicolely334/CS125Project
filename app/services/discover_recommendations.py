"""Discover recommendations: from user's logged artists, tracks, tags/genres and from Last.fm tag/chart APIs."""
from typing import Any, Dict, List, Optional

from app.services.user_profile import get_user_profile
from app.services.lastfm_service import (
    artist_get_similar,
    tag_get_similar,
    tag_get_top_artists,
    tag_get_top_tracks,
    tag_get_top_albums,
    chart_get_top_artists,
    chart_get_top_tracks,
)


def _extract_str(v: Any) -> str:
    if isinstance(v, dict):
        return str(v.get("name", v.get("#text", ""))).strip()
    return str(v).strip() if v else ""


def _track_id(artist: str, track: str) -> str:
    a, t = (artist or "").strip().lower(), (track or "").strip().lower()
    return f"{a}_{t}".replace(" ", "_").replace("/", "_")


def _norm_artist_placeholder(artist_data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
    name = _extract_str(artist_data.get("name", ""))
    if not name:
        return None
    mbid = _extract_str(artist_data.get("mbid", ""))
    aid = mbid or name.lower().replace(" ", "_").replace("/", "_")
    return {"track": f"Artist: {name}", "artist": name, "id": aid, "reason": reason, "match_score": None}


def _norm_track(track_data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
    name = _extract_str(track_data.get("name", ""))
    artist = _extract_str(track_data.get("artist", ""))
    if not name or not artist:
        return None
    mbid = _extract_str(track_data.get("mbid", ""))
    tid = mbid or _track_id(artist, name)
    return {"track": name, "artist": artist, "id": tid, "reason": reason, "match_score": None}


def _norm_album(album_data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
    name = _extract_str(album_data.get("name", ""))
    artist = _extract_str(album_data.get("artist", ""))
    if not name or not artist:
        return None
    aid = f"album_{_track_id(artist, name)}"
    return {"track": f"Album: {name}", "artist": artist, "id": aid, "reason": reason, "match_score": None}


def _gather_from_profile(user_id: str, limit_per_source: int) -> List[Dict[str, Any]]:
    profile = get_user_profile(user_id)
    if not profile:
        return []
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []

    for (artist_name, _) in (profile.top_artists[:5] or []):
        try:
            data = artist_get_similar(artist=artist_name, limit=limit_per_source)
            artists = data.get("similarartists", {}).get("artist", []) or []
            if isinstance(artists, dict):
                artists = [artists]
            for a in artists:
                rec = _norm_artist_placeholder(a, reason=f"Similar to {artist_name}")
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    out.append(rec)
        except Exception:
            continue

    for (tag_name, _) in (profile.top_tags[:5] or []):
        if not tag_name:
            continue
        try:
            data = tag_get_top_artists(tag=tag_name, limit=limit_per_source)
            artists = data.get("topartists", {}).get("artist", []) or []
            if isinstance(artists, dict):
                artists = [artists]
            for a in artists:
                rec = _norm_artist_placeholder(a, reason=f"Top artist in {tag_name}")
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    out.append(rec)
        except Exception:
            pass
        try:
            data = tag_get_top_tracks(tag=tag_name, limit=limit_per_source)
            tracks = data.get("toptracks", {}).get("track", []) or data.get("tracks", {}).get("track", []) or []
            if isinstance(tracks, dict):
                tracks = [tracks]
            for t in tracks:
                rec = _norm_track(t, reason=f"Top track in {tag_name}")
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    out.append(rec)
        except Exception:
            pass
        try:
            data = tag_get_top_albums(tag=tag_name, limit=min(5, limit_per_source))
            albums = data.get("albums", {}).get("album", []) or data.get("topalbums", {}).get("album", []) or []
            if isinstance(albums, dict):
                albums = [albums]
            for al in albums:
                rec = _norm_album(al, reason=f"Top album in {tag_name}")
                if rec and rec["id"] not in seen:
                    seen.add(rec["id"])
                    out.append(rec)
        except Exception:
            pass

        try:
            sim = tag_get_similar(tag=tag_name, limit=5)
            similar_tags = sim.get("similartags", {}).get("tag", []) or []
            if isinstance(similar_tags, dict):
                similar_tags = [similar_tags]
            for st in similar_tags[:3]:
                sim_tag_name = _extract_str(st.get("name", ""))
                if not sim_tag_name or sim_tag_name == tag_name:
                    continue
                try:
                    tdata = tag_get_top_tracks(tag=sim_tag_name, limit=3)
                    tracks = tdata.get("toptracks", {}).get("track", []) or tdata.get("tracks", {}).get("track", []) or []
                    if isinstance(tracks, dict):
                        tracks = [tracks]
                    for t in tracks:
                        rec = _norm_track(t, reason=f"Similar tag to {tag_name}: {sim_tag_name}")
                        if rec and rec["id"] not in seen:
                            seen.add(rec["id"])
                            out.append(rec)
                except Exception:
                    pass
        except Exception:
            pass

    return out


def _gather_chart(limit_per: int) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    try:
        data = chart_get_top_artists(limit=limit_per)
        artists = data.get("artists", {}).get("artist", []) or []
        if isinstance(artists, dict):
            artists = [artists]
        for a in artists:
            rec = _norm_artist_placeholder(a, reason="Top artist this week")
            if rec and rec["id"] not in seen:
                seen.add(rec["id"])
                out.append(rec)
    except Exception:
        pass
    try:
        data = chart_get_top_tracks(limit=limit_per)
        tracks = data.get("tracks", {}).get("track", []) or data.get("toptracks", {}).get("track", []) or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        for t in tracks:
            rec = _norm_track(t, reason="Top track this week")
            if rec and rec["id"] not in seen:
                seen.add(rec["id"])
                out.append(rec)
    except Exception:
        pass
    return out


def get_discover_recommendations(user_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Discover recommendations: from user's logged artists/tags (artist.getSimilar, tag.getTopArtists,
    tag.getTopTracks, tag.getTopAlbums) and from chart (chart.getTopArtists, chart.getTopTracks).
    If user_id is None or profile missing, returns chart-only results.
    """
    limit_per = max(5, limit // 4)
    combined: List[Dict[str, Any]] = []

    if user_id:
        combined.extend(_gather_from_profile(user_id, limit_per_source=limit_per))
    combined.extend(_gather_chart(limit_per=limit_per))

    for d in combined:
        d.setdefault("source", "lastfm")
    return combined[:limit]
