# app/services/lastfm_service.py
from typing import Any, Dict, Optional
import requests

from app.core.config import settings

DEFAULT_TIMEOUT = 15


def _call_lastfm(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic Last.fm REST call.
    Last.fm expects method + api_key + format=json on the root endpoint.
    """
    base_params = {
        "method": method,
        "api_key": settings.LASTFM_API_KEY,
        "format": "json",
    }
    base_params.update(params)

    resp = requests.get(settings.LASTFM_BASE_URL, params=base_params, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    # Last.fm returns errors in JSON payload sometimes
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"Last.fm error {data.get('error')}: {data.get('message')}")
    return data


def track_search(track: str, artist: Optional[str] = None, limit: int = 10, page: int = 1) -> Dict[str, Any]:
    """
    Uses track.search (no auth required).
    """
    params: Dict[str, Any] = {"track": track, "limit": limit, "page": page}
    if artist:
        params["artist"] = artist
    return _call_lastfm("track.search", params)


def track_get_info(track: str, artist: str) -> Dict[str, Any]:
    """
    Uses track.getInfo to fetch metadata by artist+track.
    """
    return _call_lastfm("track.getInfo", {"track": track, "artist": artist})


def track_get_similar(track: str, artist: str, limit: int = 10) -> Dict[str, Any]:
    """
    Uses track.getSimilar to get similar tracks.
    """
    return _call_lastfm("track.getSimilar", {"track": track, "artist": artist, "limit": limit})


def artist_get_similar(artist: str, limit: int = 10) -> Dict[str, Any]:
    """
    Uses artist.getSimilar to get similar artists.
    """
    return _call_lastfm("artist.getSimilar", {"artist": artist, "limit": limit})


def artist_get_top_tracks(artist: str, limit: int = 10) -> Dict[str, Any]:
    """
    Uses artist.getTopTracks to get top tracks for an artist.
    """
    return _call_lastfm("artist.getTopTracks", {"artist": artist, "limit": limit})
