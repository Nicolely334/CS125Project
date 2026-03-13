"""Enrich search results with track.getInfo metadata (tags, genre)."""
from typing import Dict, Any, List, Optional, Callable


def extract_tags_from_track_info(track_info: Dict[str, Any]) -> List[str]:
    """
    Extract tags from track.getInfo response.
    Handles both single tag dict and array of tags.
    """
    tags = []
    track = track_info.get("track", {})
    toptags = track.get("toptags", {})
    tag_data = toptags.get("tag", [])
    
    if not tag_data:
        return tags
    
    # Handle both single dict and array
    if isinstance(tag_data, dict):
        tag_data = [tag_data]
    
    for tag in tag_data:
        name = tag.get("name", "").strip()
        if name:
            tags.append(name.lower())
    
    return tags[:5]  # Top 5 tags


def extract_genre_from_track_info(track_info: Dict[str, Any]) -> Optional[str]:
    """
    Extract genre from track.getInfo.
    Strategy: Use first/most common tag as genre proxy.
    """
    tags = extract_tags_from_track_info(track_info)
    if tags:
        return tags[0]  # Most popular tag as genre
    
    return None


def enrich_track_with_info(
    track_name: str,
    artist_name: str,
    track_id: str,
    track_get_info_func: Callable[[str, str], Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Enrich a track with metadata from track.getInfo.
    Returns dict with added 'tags' and 'genre' fields.
    """
    try:
        info = track_get_info_func(track=track_name, artist=artist_name)
        tags = extract_tags_from_track_info(info)
        genre = extract_genre_from_track_info(info)
        
        return {
            "track": track_name,
            "artist": artist_name,
            "id": track_id,
            "source": "lastfm",
            "tags": tags,
            "genre": genre,
        }
    except Exception:
        # Fallback: return original track without enrichment
        return {
            "track": track_name,
            "artist": artist_name,
            "id": track_id,
            "source": "lastfm",
            "tags": [],
            "genre": None,
        }
