"""Discover recommendations: personalized sections based on user's listening history."""
from typing import Any, Dict, List, Optional
import logging
import random

from app.services.user_profile import get_user_profile
from app.services.personal_model import score_discover_item
from app.services.lastfm_service import (
    artist_get_similar,
    track_get_similar,
    tag_get_top_artists,
    tag_get_top_tracks,
    tag_get_top_albums,
    chart_get_top_artists,
    chart_get_top_tracks,
)

logger = logging.getLogger(__name__)


def _extract_str(v: Any) -> str:
    if isinstance(v, dict):
        return str(v.get("name", v.get("#text", ""))).strip()
    return str(v).strip() if v else ""


def _track_id(artist: str, track: str) -> str:
    a, t = (artist or "").strip().lower(), (track or "").strip().lower()
    return f"{a}_{t}".replace(" ", "_").replace("/", "_")


def _norm_track(track_data: Dict[str, Any], reason: str, match_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
    name = _extract_str(track_data.get("name", ""))
    artist = _extract_str(track_data.get("artist", ""))
    if not name or not artist:
        return None
    mbid = _extract_str(track_data.get("mbid", ""))
    tid = mbid or _track_id(artist, name)
    return {"track": name, "artist": artist, "id": tid, "reason": reason, "match_score": match_score, "source": "lastfm"}


def _norm_artist_placeholder(artist_data: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
    name = _extract_str(artist_data.get("name", ""))
    if not name:
        return None
    mbid = _extract_str(artist_data.get("mbid", ""))
    aid = mbid or name.lower().replace(" ", "_").replace("/", "_")
    return {"track": f"Artist: {name}", "artist": name, "id": aid, "reason": reason, "match_score": None, "source": "lastfm"}


def _get_recommendations_from_track(track_name: str, artist_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get similar tracks using track.getSimilar."""
    try:
        logger.info(f"Getting similar tracks for: {track_name} by {artist_name}")
        data = track_get_similar(track=track_name, artist=artist_name, limit=limit)
        tracks = data.get("similartracks", {}).get("track", []) or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        
        results = []
        for t in tracks:
            match_score = t.get("match")
            try:
                match_score = float(match_score) if match_score else None
            except (ValueError, TypeError):
                match_score = None
            
            rec = _norm_track(
                t,
                reason=f"Because you liked {track_name}",
                match_score=match_score
            )
            if rec:
                results.append(rec)
        logger.info(f"Found {len(results)} similar tracks for {track_name}")
        return results
    except Exception as e:
        logger.error(f"Failed to get similar tracks for {track_name}: {e}")
        return []


def _get_recommendations_from_artist(artist_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get similar artists using artist.getSimilar."""
    try:
        logger.info(f"Getting similar artists for: {artist_name}")
        data = artist_get_similar(artist=artist_name, limit=limit)
        artists = data.get("similarartists", {}).get("artist", []) or []
        if isinstance(artists, dict):
            artists = [artists]
        
        results = []
        for a in artists:
            similar_artist = _extract_str(a.get("name", ""))
            if similar_artist and similar_artist.lower() != artist_name.lower():
                rec = _norm_artist_placeholder(a, reason=f"Because you like {artist_name}")
                if rec:
                    results.append(rec)
        logger.info(f"Found {len(results)} similar artists for {artist_name}")
        return results
    except Exception as e:
        logger.error(f"Failed to get similar artists for {artist_name}: {e}")
        return []


def _get_recommendations_from_tag(tag_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get top tracks/artists for a tag using tag.getTopTracks and tag.getTopArtists."""
    results = []
    seen_ids = set()
    
    try:
        logger.info(f"Getting top tracks for tag: {tag_name}")
        # Get top tracks for this tag
        data = tag_get_top_tracks(tag=tag_name, limit=limit)
        tracks = data.get("toptracks", {}).get("track", []) or data.get("tracks", {}).get("track", []) or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        
        for t in tracks:
            rec = _norm_track(t, reason=f"When you're feeling {tag_name}")
            if rec and rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                results.append(rec)
        logger.info(f"Found {len(results)} tracks for tag {tag_name}")
    except Exception as e:
        logger.error(f"Failed to get top tracks for tag {tag_name}: {e}")
    
    try:
        logger.info(f"Getting top artists for tag: {tag_name}")
        # Get top artists for this tag
        data = tag_get_top_artists(tag=tag_name, limit=limit)
        artists = data.get("topartists", {}).get("artist", []) or []
        if isinstance(artists, dict):
            artists = [artists]
        
        for a in artists:
            rec = _norm_artist_placeholder(a, reason=f"When you're feeling {tag_name}")
            if rec and rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                results.append(rec)
        logger.info(f"Found {len(results)} total items for tag {tag_name}")
    except Exception as e:
        logger.error(f"Failed to get top artists for tag {tag_name}: {e}")
    
    return results


def _get_chart_recommendations(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top artists and tracks from charts."""
    results = []
    seen_ids = set()
    
    try:
        data = chart_get_top_artists(limit=limit)
        artists = data.get("artists", {}).get("artist", []) or []
        if isinstance(artists, dict):
            artists = [artists]
        for a in artists:
            rec = _norm_artist_placeholder(a, reason="Top artist this week")
            if rec and rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                results.append(rec)
    except Exception as e:
        logger.error(f"Failed to get top artists: {e}")
    
    try:
        data = chart_get_top_tracks(limit=limit)
        tracks = data.get("tracks", {}).get("track", []) or data.get("toptracks", {}).get("track", []) or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        for t in tracks:
            rec = _norm_track(t, reason="Top track this week")
            if rec and rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                results.append(rec)
    except Exception as e:
        logger.error(f"Failed to get top tracks: {e}")
    
    return results


def get_discover_recommendations(user_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Get personalized discover recommendations organized by sections:
    - "Because you liked (song)" - from top tracks
    - "Because you like (artist)" - from top artists
    - "When you're feeling (tag)" - from top tags
    - "Top artists/tracks this week" - from charts
    
    If user_id is None, returns only chart recommendations.
    """
    all_recommendations = []
    seen_ids = set()
    
    if user_id:
        logger.info(f"Loading profile for user: {user_id}")
        profile = get_user_profile(user_id)
        if profile:
            logger.info(
                f"Profile loaded: {len(profile.top_tracks)} tracks, {len(profile.top_artists)} artists, {len(profile.top_tags)} tags"
            )

            # Add a bit of randomness so each refresh can use different seeds
            rng = random.Random()  # local RNG, no fixed seed

            # 1. "Because you liked (song)" - pick up to 2 random top tracks
            if profile.top_tracks:
                track_seeds = profile.top_tracks[:10]  # look at up to top 10
                rng.shuffle(track_seeds)
                selected_tracks = track_seeds[:2]
                logger.info(f"Using track seeds: {selected_tracks}")
                for track, artist, _ in selected_tracks:
                    recs = _get_recommendations_from_track(track, artist, limit=3)
                    for rec in recs:
                        if rec["id"] not in seen_ids:
                            seen_ids.add(rec["id"])
                            all_recommendations.append(rec)
            else:
                logger.warning("No top tracks found in profile")

            # 2. "Because you like (artist)" - pick up to 2 random top artists
            if profile.top_artists:
                artist_seeds = profile.top_artists[:10]
                rng.shuffle(artist_seeds)
                selected_artists = artist_seeds[:2]
                logger.info(f"Using artist seeds: {[a[0] for a in selected_artists]}")
                for artist_name, _ in selected_artists:
                    recs = _get_recommendations_from_artist(artist_name, limit=3)
                    for rec in recs:
                        if rec["id"] not in seen_ids:
                            seen_ids.add(rec["id"])
                            all_recommendations.append(rec)
            else:
                logger.warning("No top artists found in profile")

            # 3. "When you're feeling (tag)" - pick up to 2 random top tags
            if profile.top_tags:
                tag_seeds = profile.top_tags[:10]
                rng.shuffle(tag_seeds)
                selected_tags = tag_seeds[:2]
                logger.info(f"Using tag seeds: {[t[0] for t in selected_tags]}")
                for tag_name, _ in selected_tags:
                    recs = _get_recommendations_from_tag(tag_name, limit=5)
                    for rec in recs:
                        if rec["id"] not in seen_ids:
                            seen_ids.add(rec["id"])
                            all_recommendations.append(rec)
            else:
                logger.warning("No top tags found in profile")
            
            logger.info(f"Total personalized recommendations before reranking: {len(all_recommendations)}")
            
            # 4. Rerank by personal model
            if all_recommendations:
                scored_items = [
                    (score_discover_item(item, profile), item)
                    for item in all_recommendations
                ]
                scored_items.sort(key=lambda x: x[0], reverse=True)
                all_recommendations = [item for _, item in scored_items]
                logger.info(f"Reranked {len(all_recommendations)} recommendations")
        else:
            logger.warning(f"Could not load profile for user_id: {user_id}")
    
    # 5. Always add chart recommendations (top artists/tracks)
    logger.info("Adding chart recommendations")
    chart_recs = _get_chart_recommendations(limit=10)
    for rec in chart_recs:
        if rec["id"] not in seen_ids:
            seen_ids.add(rec["id"])
            all_recommendations.append(rec)
    
    logger.info(f"Total recommendations: {len(all_recommendations)}")
    return all_recommendations[:limit]
