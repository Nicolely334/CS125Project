from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.services.lastfm_service import track_get_similar, artist_get_similar, artist_get_top_tracks


router = APIRouter()


class RecommendationResponse(BaseModel):
    track: str
    artist: str
    id: str
    source: str = "lastfm"
    reason: Optional[str] = None
    match_score: Optional[float] = None


def _normalize_track_from_similar(track_data: Dict[str, Any], reason: str, match_score: Optional[float] = None) -> Optional[RecommendationResponse]:
    """
    Normalize a track from Last.fm similar tracks/artists response.
    Handles cases where artist/name fields might be strings or dicts.
    """
    # Helper function to extract string value from field (handles both string and dict)
    def extract_string_value(field_value: Any) -> str:
        if isinstance(field_value, dict):
            return str(field_value.get("name", field_value.get("#text", ""))).strip()
        return str(field_value).strip() if field_value else ""
    
    track_name = extract_string_value(track_data.get("name", ""))
    artist_name = extract_string_value(track_data.get("artist", ""))
    mbid = extract_string_value(track_data.get("mbid", ""))
    
    if not track_name or not artist_name:
        return None
    
    track_id = mbid if mbid else f"{artist_name}_{track_name}".lower().replace(" ", "_").replace("/", "_")
    
    return RecommendationResponse(
        track=track_name,
        artist=artist_name,
        id=track_id,
        source="lastfm",
        reason=reason,
        match_score=match_score
    )


def _normalize_artist_tracks(artist_data: Dict[str, Any], reason: str, fetch_tracks: bool = True, max_tracks_per_artist: int = 3) -> List[RecommendationResponse]:
    """
    Normalize tracks from an artist's similar artists response.
    If fetch_tracks is True, fetches top tracks for the artist.
    Otherwise, returns the artist as a placeholder recommendation.
    """
    tracks = []
    
    # Helper function to extract string value (handles both string and dict)
    def extract_string_value(field_value: Any) -> str:
        if isinstance(field_value, dict):
            return str(field_value.get("name", field_value.get("#text", ""))).strip()
        return str(field_value).strip() if field_value else ""
    
    artist_name = extract_string_value(artist_data.get("name", ""))
    
    if not artist_name:
        return tracks
    
    # Note: artist.getSimilar returns artists, not tracks directly
    # For now, we'll return the artist info as a "track" placeholder
    # In a full implementation, you'd want to fetch top tracks for each similar artist
    mbid = extract_string_value(artist_data.get("mbid", ""))
    artist_id = mbid if mbid else artist_name.lower().replace(" ", "_").replace("/", "_")
    
    # Return artist as a recommendation (frontend can handle this)
    tracks.append(RecommendationResponse(
        track=f"Artist: {artist_name}",  # Placeholder - frontend can interpret
        artist=artist_name,
        id=artist_id,
        source="lastfm",
        reason=reason,
        match_score=None
    ))
    
    return tracks


@router.get("/track", response_model=List[RecommendationResponse])
def get_track_recommendations(
    track: str = Query(..., description="Track name"),
    artist: str = Query(..., description="Artist name"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations to return"),
):
    """
    Get similar tracks based on a specific track using Last.fm track.getSimilar.
    """
    try:
        result = track_get_similar(track=track, artist=artist, limit=limit)
        
        # Last.fm response structure: similartracks.track[]
        similartracks = result.get("similartracks", {})
        tracks_data = similartracks.get("track", [])
        
        if not tracks_data:
            return []
        
        # Handle case where single track is returned (not a list)
        if isinstance(tracks_data, dict):
            tracks_data = [tracks_data]
        
        recommendations = []
        for track_data in tracks_data:
            # Extract match score if available (Last.fm provides match as a float)
            match_score = track_data.get("match")
            if match_score:
                try:
                    match_score = float(match_score)
                except (ValueError, TypeError):
                    match_score = None
            
            normalized = _normalize_track_from_similar(
                track_data,
                reason=f"Similar to {track} by {artist}",
                match_score=match_score
            )
            if normalized:
                recommendations.append(normalized)
        
        return recommendations
    
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get track recommendations: {str(e)}")


@router.get("/artist", response_model=List[RecommendationResponse])
def get_artist_recommendations(
    artist: str = Query(..., description="Artist name"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations to return"),
):
    """
    Get similar artists based on a specific artist using Last.fm artist.getSimilar.
    Note: This returns similar artists. To get tracks from these artists, 
    you may want to combine this with artist.getTopTracks in the frontend.
    """
    try:
        result = artist_get_similar(artist=artist, limit=limit)
        
        # Last.fm response structure: similarartists.artist[]
        similarartists = result.get("similarartists", {})
        artists_data = similarartists.get("artist", [])
        
        if not artists_data:
            return []
        
        # Handle case where single artist is returned (not a list)
        if isinstance(artists_data, dict):
            artists_data = [artists_data]
        
        recommendations = []
        for artist_data in artists_data:
            normalized_list = _normalize_artist_tracks(
                artist_data,
                reason=f"Similar to {artist}",
                fetch_tracks=True,
                max_tracks_per_artist=2  # Limit tracks per artist to avoid too many results
            )
            recommendations.extend(normalized_list)
        
        return recommendations
    
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get artist recommendations: {str(e)}")


@router.get("/combined", response_model=List[RecommendationResponse])
def get_combined_recommendations(
    track: Optional[str] = Query(None, description="Track name (optional)"),
    artist: Optional[str] = Query(None, description="Artist name (required if track is provided)"),
    limit: int = Query(20, ge=1, le=50, description="Total number of recommendations to return"),
):
    """
    Get combined recommendations from both track.getSimilar and artist.getSimilar.
    If both track and artist are provided, returns similar tracks.
    If only artist is provided, returns similar artists.
    Results are combined and deduplicated.
    """
    if not artist:
        raise HTTPException(
            status_code=400,
            detail="At least 'artist' parameter is required"
        )
    
    if track and not artist:
        raise HTTPException(
            status_code=400,
            detail="'artist' parameter is required when 'track' is provided"
        )
    
    all_recommendations = []
    seen_ids = set()
    
    try:
        # Get track-based recommendations if track is provided
        if track:
            track_result = track_get_similar(track=track, artist=artist, limit=limit)
            similartracks = track_result.get("similartracks", {})
            tracks_data = similartracks.get("track", [])
            
            if isinstance(tracks_data, dict):
                tracks_data = [tracks_data]
            
            for track_data in tracks_data:
                match_score = track_data.get("match")
                if match_score:
                    try:
                        match_score = float(match_score)
                    except (ValueError, TypeError):
                        match_score = None
                
                normalized = _normalize_track_from_similar(
                    track_data,
                    reason=f"Similar track to {track}",
                    match_score=match_score
                )
                if normalized and normalized.id not in seen_ids:
                    seen_ids.add(normalized.id)
                    all_recommendations.append(normalized)
        
        # Get artist-based recommendations
        artist_result = artist_get_similar(artist=artist, limit=limit)
        similarartists = artist_result.get("similarartists", {})
        artists_data = similarartists.get("artist", [])
        
        if isinstance(artists_data, dict):
            artists_data = [artists_data]
        
        for artist_data in artists_data:
            normalized_list = _normalize_artist_tracks(
                artist_data,
                reason=f"Similar artist to {artist}",
                fetch_tracks=True,
                max_tracks_per_artist=2  # Limit tracks per artist
            )
            for normalized in normalized_list:
                if normalized.id not in seen_ids:
                    seen_ids.add(normalized.id)
                    all_recommendations.append(normalized)
        
        # Sort by match_score if available, then limit
        all_recommendations.sort(
            key=lambda x: x.match_score if x.match_score is not None else 0.0,
            reverse=True
        )
        
        return all_recommendations[:limit]
    
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get combined recommendations: {str(e)}")
