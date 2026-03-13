"""Personal model scoring functions for search and recommendation reranking."""
from typing import Dict, Any, List
import logging
from app.services.user_profile import UserProfile

logger = logging.getLogger(__name__)


def calculate_tag_alignment(lastfm_tags: List[str], profile: UserProfile) -> float:
    """
    Compare Last.fm tags with user's preferred tags from listening_logs.
    Returns 0.0 to 1.0 based on overlap and weights.
    """
    if not lastfm_tags:
        return 0.0
    
    # Get user's tag preferences (normalized to lowercase)
    user_tag_weights = {tag.lower(): score for tag, score in profile.top_tags}
    lastfm_tag_set = {tag.lower() for tag in lastfm_tags}
    
    # Find overlap
    overlap = set(user_tag_weights.keys()).intersection(lastfm_tag_set)
    if not overlap:
        return 0.0
    
    # Score based on weighted tag preferences
    total_score = 0.0
    for tag in overlap:
        weight = user_tag_weights[tag]
        # Normalize: each matching tag contributes up to 0.3 based on its weight
        # Weight is typically 1-10 range, so divide by 10 to get 0.1-1.0, then multiply by 0.3
        total_score += min(0.3, (weight / 10.0) * 0.3)
    
    # Return normalized score (0-1.0)
    return min(1.0, total_score)


def score_search_result(
    enriched_track: Dict[str, Any],
    user_profile: UserProfile
) -> float:
    """
    Score a search result using personal model.
    enriched_track should have: track, artist, id, tags, genre
    """
    score = 0.0
    
    # 1. Genre preference match (0-1.0, weight: 0.4) - Increased weight
    genre = enriched_track.get("genre")
    if genre:
        genre_score = user_profile.genre_score(genre)
        score += 0.4 * genre_score
        if genre_score > 0:
            logger.debug(f"Genre match: {genre} -> {genre_score:.3f}")
    
    # 2. Tag alignment (0-1.0, weight: 0.3) - Increased weight
    tags = enriched_track.get("tags", [])
    if tags:
        tag_score = calculate_tag_alignment(tags, user_profile)
        score += 0.3 * tag_score
        if tag_score > 0:
            logger.debug(f"Tag match: {tags} -> {tag_score:.3f}")
    
    # 3. Artist affinity (0-1.0, weight: 0.2)
    artist = enriched_track.get("artist", "")
    artist_score = user_profile.artist_score(artist)
    score += 0.2 * artist_score
    if artist_score > 0:
        logger.debug(f"Artist match: {artist} -> {artist_score:.3f}")
    
    # 4. Liked artist boost (+0.1)
    if user_profile.is_liked_artist(artist):
        score += 0.1
        logger.debug(f"Liked artist boost: {artist}")
    
    # 5. Already logged penalty (-0.5)
    track_id = enriched_track.get("id", "")
    if user_profile.is_logged(track_id):
        score -= 0.5
        logger.debug(f"Already logged penalty: {track_id}")
    
    return score


def score_discover_item(
    item: Dict[str, Any],
    user_profile: UserProfile
) -> float:
    """
    Score a discover recommendation item using personal model.
    item should have: track, artist, id, reason, tags (optional), genre (optional)
    """
    score = 0.0
    
    # 1. Genre preference (0-1.0, weight: 0.25)
    genre = item.get("genre")
    if genre:
        genre_score = user_profile.genre_score(genre)
        score += 0.25 * genre_score
    
    # 2. Tag alignment (0-1.0, weight: 0.25)
    tags = item.get("tags", [])
    if tags:
        tag_score = calculate_tag_alignment(tags, user_profile)
        score += 0.25 * tag_score
    
    # 3. Artist affinity (0-1.0, weight: 0.2)
    artist = item.get("artist", "")
    artist_score = user_profile.artist_score(artist)
    score += 0.2 * artist_score
    
    # 4. Rating-weighted preference (0-0.15, weight: 0.15)
    # If item has match_score from Last.fm, use it
    match_score = item.get("match_score")
    if match_score is not None:
        try:
            normalized_match = min(1.0, max(0.0, float(match_score) / 100.0))
            score += 0.15 * normalized_match
        except (ValueError, TypeError):
            pass
    
    # 5. Liked artist boost (+0.1)
    if user_profile.is_liked_artist(artist):
        score += 0.1
    
    # 6. Already logged penalty (-0.5)
    track_id = item.get("id", "")
    if user_profile.is_logged(track_id):
        score -= 0.5
    
    return score
