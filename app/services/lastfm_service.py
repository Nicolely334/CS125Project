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


def artist_search(artist: str, limit: int = 10, page: int = 1) -> Dict[str, Any]:
    """
    Uses artist.search (no auth required).
    """
    return _call_lastfm("artist.search", {"artist": artist, "limit": limit, "page": page})


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


def tag_get_similar(tag: str, limit: int = 10) -> Dict[str, Any]:
    """Uses tag.getSimilar to get similar tags."""
    return _call_lastfm("tag.getSimilar", {"tag": tag, "limit": limit})


def tag_get_top_artists(tag: str, limit: int = 10, page: int = 1) -> Dict[str, Any]:
    """Uses tag.getTopArtists for top artists by tag."""
    return _call_lastfm("tag.getTopArtists", {"tag": tag, "limit": limit, "page": page})


def tag_get_top_tracks(tag: str, limit: int = 10, page: int = 1) -> Dict[str, Any]:
    """Uses tag.getTopTracks for top tracks by tag."""
    return _call_lastfm("tag.getTopTracks", {"tag": tag, "limit": limit, "page": page})


def tag_get_top_albums(tag: str, limit: int = 10, page: int = 1) -> Dict[str, Any]:
    """Uses tag.getTopAlbums for top albums by tag."""
    return _call_lastfm("tag.getTopAlbums", {"tag": tag, "limit": limit, "page": page})


def chart_get_top_artists(limit: int = 10, page: int = 1) -> Dict[str, Any]:
    """Uses chart.getTopArtists for global top artists chart."""
    return _call_lastfm("chart.getTopArtists", {"limit": limit, "page": page})


def chart_get_top_tracks(limit: int = 10, page: int = 1) -> Dict[str, Any]:
    """Uses chart.getTopTracks for global top tracks chart."""
    return _call_lastfm("chart.getTopTracks", {"limit": limit, "page": page})


