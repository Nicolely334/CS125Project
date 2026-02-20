from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from app.services.lastfm_service import track_search

router = APIRouter()

class TrackResponse(BaseModel):
    track: str
    artist: str
    id: str
    source: str = "lastfm"

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
        for track in tracks_data:
            track_name = track.get("name", "").strip()
            artist_name = track.get("artist", "").strip()
            
            if not track_name or not artist_name:
                continue
            
            mbid = track.get("mbid", "").strip()
            track_id = mbid if mbid else f"{artist_name}_{track_name}".lower().replace(" ", "_").replace("/", "_")
            
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

