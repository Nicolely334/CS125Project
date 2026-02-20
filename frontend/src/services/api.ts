const API_BASE = import.meta.env.VITE_API_URL || '';

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

  const res = await fetch(`${API_BASE}/api/search?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Search failed: ${res.status}`);
  }
  return res.json();
}

