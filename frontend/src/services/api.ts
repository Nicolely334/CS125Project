const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export interface Track {
  track: string;
  artist: string;
  id: string;
  source: string;
  reason?: string;
}

export interface ListeningLog {
  id: number;
  user_id: string;
  track_id: string;
  track?: string;
  artist?: string;
  genre?: string;
  rating?: number;
  liked: boolean;
  favorite?: boolean;
  notes?: string;
  logged_at: string;
}

export async function searchTracks(
  query: string,
  options?: { artist?: string; limit?: number; page?: number }
): Promise<Track[]> {
  const params = new URLSearchParams({
    q: query,
    limit: String(options?.limit ?? 20),
    page: String(options?.page ?? 1),
  });
  if (options?.artist) params.set('artist', options.artist);

  const url = API_BASE ? `${API_BASE}/api/search?${params}` : `/api/search?${params}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Search failed: ${res.status}`);
  }
  return res.json();
}

export interface ArtistSearchResult {
  name: string;
  id: string;
  mbid?: string;
  source: string;
}

export async function searchArtists(
  query: string,
  options?: { limit?: number; page?: number }
): Promise<ArtistSearchResult[]> {
  const params = new URLSearchParams({
    q: query,
    limit: String(options?.limit ?? 20),
    page: String(options?.page ?? 1),
  });
  const url = API_BASE ? `${API_BASE}/api/search/artists?${params}` : `/api/search/artists?${params}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Artist search failed: ${res.status}`);
  }
  return res.json();
}

export interface RecommendationItem {
  track: string;
  artist: string;
  id: string;
  source: string;
  reason?: string;
  match_score?: number;
}

export async function getDiscoverRecommendations(
  options?: { user_id?: string; limit?: number }
): Promise<RecommendationItem[]> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 30),
  });
  if (options?.user_id) params.set('user_id', options.user_id);

  const url = API_BASE ? `${API_BASE}/api/recommendations/discover?${params}` : `/api/recommendations/discover?${params}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Discover failed: ${res.status}`);
  }
  return res.json();
}

