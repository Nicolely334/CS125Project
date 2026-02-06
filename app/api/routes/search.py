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
    reason: Optional[str] = None


@router.get("/search", response_model=List[TrackResponse])
def search_tracks(
    q: str = Query(..., description="Search query (track name)"),
    artist: Optional[str] = Query(None, description="Optional artist name to filter results"),
    limit: int = Query(20, ge=1, le=50, description="Number of results to return"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """
    Search for tracks using Last.fm API.
    Returns a list of tracks matching the search query.
    """
    try:
        # Call Last.fm API
        result = track_search(track=q, artist=artist, limit=limit, page=page)
        
        # Extract tracks from Last.fm response
        # Last.fm response structure: results.trackmatches.track[]
        results = result.get("results", {})
        trackmatches = results.get("trackmatches", {})
        tracks_data = trackmatches.get("track", [])
        
        # Handle empty results
        if not tracks_data:
            return []
        
        # Handle case where single track is returned (not a list)
        if isinstance(tracks_data, dict):
            tracks_data = [tracks_data]
        
        # Normalize to minimal track format
        normalized_tracks = []
        for track in tracks_data:
            # Last.fm returns track name and artist as strings
            track_name = track.get("name", "").strip()
            artist_name = track.get("artist", "").strip()
            mbid = track.get("mbid", "").strip()
            
            # Skip if essential data is missing
            if not track_name or not artist_name:
                continue
            
            # Use mbid if available, otherwise use a fallback identifier
            track_id = mbid if mbid else f"{artist_name}_{track_name}".lower().replace(" ", "_").replace("/", "_")
            
            normalized_tracks.append(
                TrackResponse(
                    track=track_name,
                    artist=artist_name,
                    id=track_id,
                    source="lastfm",
                )
            )
        
        return normalized_tracks
    
    except RuntimeError as e:
        # Last.fm API error
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

