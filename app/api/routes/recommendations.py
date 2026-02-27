from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.services.lastfm_service import track_get_similar, artist_get_similar
from app.services.personal_recommendations import get_personal_recommendations
from app.services.discover_recommendations import get_discover_recommendations


router = APIRouter()


class RecommendationResponse(BaseModel):
    track: str
    artist: str
    id: str
    source: str = "lastfm"
    reason: Optional[str] = None
    match_score: Optional[float] = None


def _normalize_text_key(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _dedupe_recommendations(items: List[RecommendationResponse], limit: Optional[int] = None) -> List[RecommendationResponse]:
    seen: set[str] = set()
    out: List[RecommendationResponse] = []
    for item in items:
        # Prefer stable IDs, fallback to normalized artist+track text.
        key = item.id or f"{_normalize_text_key(item.artist)}::{_normalize_text_key(item.track)}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if limit is not None and len(out) >= limit:
            break
    return out


def _extract_string_value(field_value: Any) -> str:
    if isinstance(field_value, dict):
        return str(field_value.get("name", field_value.get("#text", ""))).strip()
    return str(field_value).strip() if field_value else ""

def _normalize_track_from_similar(track_data: Dict[str, Any], reason: str, match_score: Optional[float] = None) -> Optional[RecommendationResponse]:
    track_name = _extract_string_value(track_data.get("name", ""))
    artist_name = _extract_string_value(track_data.get("artist", ""))
    
    if not track_name or not artist_name:
        return None
    
    mbid = _extract_string_value(track_data.get("mbid", ""))
    track_id = mbid if mbid else f"{artist_name}_{track_name}".lower().replace(" ", "_").replace("/", "_")
    
    return RecommendationResponse(
        track=track_name,
        artist=artist_name,
        id=track_id,
        source="lastfm",
        reason=reason,
        match_score=match_score
    )


def _extract_string_value(field_value: Any) -> str:
    if isinstance(field_value, dict):
        return str(field_value.get("name", field_value.get("#text", ""))).strip()
    return str(field_value).strip() if field_value else ""

def _normalize_artist_tracks(artist_data: Dict[str, Any], reason: str) -> List[RecommendationResponse]:
    """Normalize artist data from similar artists response."""
    artist_name = _extract_string_value(artist_data.get("name", ""))
    if not artist_name:
        return []
    
    mbid = _extract_string_value(artist_data.get("mbid", ""))
    artist_id = mbid if mbid else artist_name.lower().replace(" ", "_").replace("/", "_")
    
    return [RecommendationResponse(
        track=f"Artist: {artist_name}",
        artist=artist_name,
        id=artist_id,
        source="lastfm",
        reason=reason,
        match_score=None
    )]


@router.get("/track", response_model=List[RecommendationResponse])
def get_track_recommendations(
    track: str = Query(..., description="Track name"),
    artist: str = Query(..., description="Artist name"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations to return"),
):
    """Get similar tracks based on a specific track using Last.fm track.getSimilar."""
    try:
        tracks_data = track_get_similar(track=track, artist=artist, limit=limit).get("similartracks", {}).get("track", [])
        if not tracks_data:
            return []
        if isinstance(tracks_data, dict):
            tracks_data = [tracks_data]
        
        recommendations = []
        for track_data in tracks_data:
            match_score = track_data.get("match")
            try:
                match_score = float(match_score) if match_score else None
            except (ValueError, TypeError):
                match_score = None
            
            normalized = _normalize_track_from_similar(track_data, reason=f"Similar to {track} by {artist}", match_score=match_score)
            if normalized:
                recommendations.append(normalized)
        
        return _dedupe_recommendations(recommendations, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get track recommendations: {str(e)}")


@router.get("/artist", response_model=List[RecommendationResponse])
def get_artist_recommendations(
    artist: str = Query(..., description="Artist name"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations to return"),
):
    """Get similar artists based on a specific artist using Last.fm artist.getSimilar."""
    try:
        artists_data = artist_get_similar(artist=artist, limit=limit).get("similarartists", {}).get("artist", [])
        if not artists_data:
            return []
        if isinstance(artists_data, dict):
            artists_data = [artists_data]
        
        recommendations = []
        for artist_data in artists_data:
            recommendations.extend(_normalize_artist_tracks(artist_data, reason=f"Similar to {artist}"))
        
        return _dedupe_recommendations(recommendations, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get artist recommendations: {str(e)}")


@router.get("/personal", response_model=List[RecommendationResponse])
def get_personal_recommendations_endpoint(
    user_id: str = Query(..., description="Authenticated user ID (e.g. Supabase auth user id)"),
    limit: int = Query(20, ge=1, le=50, description="Number of recommendations to return"),
):
    """
    Personalized recommendations based on the user's listening log: seeds from their
    top tracks and artists, candidates from Last.fm, reranked by a personal model
    (artist affinity, liked artists, already-logged penalty, Last.fm score).
    Requires Supabase configured and listening_logs data for the user.
    """
    try:
        recs = get_personal_recommendations(user_id=user_id, limit=limit)
        out = [RecommendationResponse(**r) for r in recs]
        return _dedupe_recommendations(out, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Personal recommendations failed: {str(e)}")


@router.get("/discover", response_model=List[RecommendationResponse])
def get_discover_recommendations_endpoint(
    user_id: Optional[str] = Query(None, description="Optional user ID for personalized discover (from your logged artists, tags, etc.)"),
    limit: int = Query(30, ge=1, le=50, description="Number of recommendations to return"),
):
    """
    Discover: recommendations from your logged artists (artist.getSimilar), tags (tag.getTopArtists,
    tag.getTopTracks, tag.getTopAlbums) and global charts (chart.getTopArtists, chart.getTopTracks).
    If user_id is omitted, returns chart-based recommendations only.
    """
    try:
        recs = get_discover_recommendations(user_id=user_id, limit=limit)
        out = [RecommendationResponse(**r) for r in recs]
        return _dedupe_recommendations(out, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discover recommendations failed: {str(e)}")


@router.get("/combined", response_model=List[RecommendationResponse])
def get_combined_recommendations(
    track: Optional[str] = Query(None, description="Track name (optional)"),
    artist: Optional[str] = Query(None, description="Artist name (required if track is provided)"),
    limit: int = Query(20, ge=1, le=50, description="Total number of recommendations to return"),
):
    """Get combined recommendations from both track.getSimilar and artist.getSimilar."""
    if not artist:
        raise HTTPException(status_code=400, detail="At least 'artist' parameter is required")
    
    all_recommendations = []
    seen_ids = set()
    
    try:
        if track:
            tracks_data = track_get_similar(track=track, artist=artist, limit=limit).get("similartracks", {}).get("track", [])
            if isinstance(tracks_data, dict):
                tracks_data = [tracks_data]
            
            for track_data in tracks_data:
                match_score = track_data.get("match")
                try:
                    match_score = float(match_score) if match_score else None
                except (ValueError, TypeError):
                    match_score = None
                
                normalized = _normalize_track_from_similar(track_data, reason=f"Similar track to {track}", match_score=match_score)
                if normalized and normalized.id not in seen_ids:
                    seen_ids.add(normalized.id)
                    all_recommendations.append(normalized)
        
        artists_data = artist_get_similar(artist=artist, limit=limit).get("similarartists", {}).get("artist", [])
        if isinstance(artists_data, dict):
            artists_data = [artists_data]
        
        for artist_data in artists_data:
            for normalized in _normalize_artist_tracks(artist_data, reason=f"Similar artist to {artist}"):
                if normalized.id not in seen_ids:
                    seen_ids.add(normalized.id)
                    all_recommendations.append(normalized)
        
        all_recommendations.sort(key=lambda x: x.match_score if x.match_score is not None else 0.0, reverse=True)
        return _dedupe_recommendations(all_recommendations, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get combined recommendations: {str(e)}")
