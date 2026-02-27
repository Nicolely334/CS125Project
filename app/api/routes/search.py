from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from app.services.lastfm_service import track_search, artist_search

router = APIRouter()


class TrackResponse(BaseModel):
    track: str
    artist: str
    id: str
    source: str = "lastfm"


class ArtistResponse(BaseModel):
    name: str
    id: str
    mbid: Optional[str] = None
    source: str = "lastfm"


def _normalize_text_key(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _track_text_key(track_name: str, artist_name: str) -> str:
    return f"{_normalize_text_key(artist_name)}::{_normalize_text_key(track_name)}"

@router.get("/search", response_model=List[TrackResponse])
def search_tracks(
    q: str = Query(..., description="Search query (track name)"),
    artist: Optional[str] = Query(None, description="Optional artist name to filter results"),
    limit: int = Query(20, ge=1, le=50, description="Number of results to return"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """Search for tracks using Last.fm API."""
    try:
        result = track_search(track=q, artist=artist, limit=limit, page=page)
        tracks_data = result.get("results", {}).get("trackmatches", {}).get("track", [])
        
        if not tracks_data:
            return []
        
        if isinstance(tracks_data, dict):
            tracks_data = [tracks_data]
        
        normalized_tracks = []
        seen_track_keys: set[str] = set()
        for track in tracks_data:
            track_name = track.get("name", "").strip()
            artist_name = track.get("artist", "").strip()
            
            if not track_name or not artist_name:
                continue
            
            mbid = track.get("mbid", "").strip()
            track_id = mbid if mbid else f"{artist_name}_{track_name}".lower().replace(" ", "_").replace("/", "_")
            dedupe_key = mbid if mbid else _track_text_key(track_name, artist_name)
            if dedupe_key in seen_track_keys:
                continue
            seen_track_keys.add(dedupe_key)
            
            normalized_tracks.append(TrackResponse(
                track=track_name,
                artist=artist_name,
                id=track_id,
                source="lastfm",
            ))
        
        return normalized_tracks
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/artists", response_model=List[ArtistResponse])
def search_artists(
    q: str = Query(..., description="Artist name to search"),
    limit: int = Query(20, ge=1, le=50, description="Number of results to return"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """Search for artists using Last.fm artist.search."""
    try:
        result = artist_search(artist=q, limit=limit, page=page)
        artists_data = result.get("results", {}).get("artistmatches", {}).get("artist", [])

        if not artists_data:
            return []

        if isinstance(artists_data, dict):
            artists_data = [artists_data]

        normalized = []
        seen_names: set[str] = set()
        for a in artists_data:
            name = (a.get("name") or "").strip()
            if not name:
                continue
            lower_name = name.lower()
            # Remove noisy/combined names for cleaner artist picks.
            if "," in name or " and " in lower_name or "&" in name:
                continue
            name_key = _normalize_text_key(name)
            if name_key in seen_names:
                continue
            seen_names.add(name_key)
            mbid = (a.get("mbid") or "").strip() or None
            aid = mbid or name.lower().replace(" ", "_").replace("/", "_")
            normalized.append(ArtistResponse(name=name, id=aid, mbid=mbid, source="lastfm"))
        return normalized
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Artist search failed: {str(e)}")

