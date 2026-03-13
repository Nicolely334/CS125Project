import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getDiscoverRecommendations, type RecommendationItem, type Track, type ArtistSearchResult } from '../services/api';
import { LogSongModal } from '../components/LogSongModal';
import { LogArtistModal } from '../components/LogArtistModal';

// Simple in-memory cache for discover recommendations
interface DiscoverCacheEntry {
  userId: string | null;
  items: RecommendationItem[];
  timestamp: number;
}

let discoverCache: DiscoverCacheEntry | null = null;

export function DiscoverPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const [selectedArtist, setSelectedArtist] = useState<ArtistSearchResult | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRecommendations(forceRefresh: boolean) {
      const currentUserId = user?.id ?? null;
      const now = Date.now();
      const TWENTY_MIN_MS = 20 * 60 * 1000;

      // Use cache if available, user matches, and not expired, and not forcing refresh
      if (
        !forceRefresh &&
        discoverCache &&
        discoverCache.userId === currentUserId &&
        now - discoverCache.timestamp < TWENTY_MIN_MS
      ) {
        setItems(discoverCache.items);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const data = await getDiscoverRecommendations({
          user_id: currentUserId ?? undefined,
          limit: 50,
        });
        if (!cancelled) {
          setItems(data);
          // Update cache
          discoverCache = {
            userId: currentUserId,
            items: data,
            timestamp: Date.now(),
          };
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load discover');
          setItems([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setIsRefreshing(false);
        }
      }
    }

    // Initial load (use cache if valid)
    loadRecommendations(false);

    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  // Group items by reason for better display
  const groupedItems = items.reduce((acc, item) => {
    const reason = item.reason || 'Other';
    if (!acc[reason]) {
      acc[reason] = [];
    }
    acc[reason].push(item);
    return acc;
  }, {} as Record<string, RecommendationItem[]>);

  function handleRefreshClick() {
    // Force refresh recommendations and update cache
    setIsRefreshing(true);
    // Clear cache so useEffect reloads fresh data
    discoverCache = null;
    // Trigger effect by temporarily changing user id dependency via state isn't ideal,
    // so instead we directly call the API here.
    const currentUserId = user?.id ?? null;
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getDiscoverRecommendations({
          user_id: currentUserId ?? undefined,
          limit: 50,
        });
        if (!cancelled) {
          setItems(data);
          discoverCache = {
            userId: currentUserId,
            items: data,
            timestamp: Date.now(),
          };
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to refresh discover');
          setItems([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setIsRefreshing(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }

  function handleLogFromItem(item: RecommendationItem) {
    if (!user) {
      setError('Please sign in to log from Discover');
      return;
    }

    // If this is an artist placeholder (track starts with "Artist: "), open artist modal
    if (item.track.startsWith('Artist: ')) {
      const name = item.track.replace('Artist: ', '');
      const artist: ArtistSearchResult = {
        name,
        id: item.id,
        mbid: undefined,
        source: item.source,
      };
      setSelectedArtist(artist);
      return;
    }

    // Otherwise treat as a track recommendation
    const track: Track = {
      track: item.track,
      artist: item.artist,
      id: item.id,
      source: item.source,
      reason: item.reason,
    };
    setSelectedTrack(track);
  }

  return (
    <section className="page discover-page">
      <h1>Discover</h1>
      <p className="page-desc">
        {user 
          ? 'Personalized recommendations based on your listening history, plus top charts.'
          : 'Top artists and tracks this week.'}
      </p>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <span style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)' }}>
          Recommendations refresh automatically every ~20 minutes.
        </span>
        <button
          type="button"
          className="btn btn-sm"
          onClick={handleRefreshClick}
          disabled={loading || isRefreshing}
        >
          {isRefreshing || loading ? 'Refreshing…' : 'Refresh recommendations'}
        </button>
      </div>

      {loading && <p className="loading-state">Loading recommendations…</p>}
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {!loading && !error && Object.keys(groupedItems).length > 0 && (
        <div className="discover-sections">
          {/* Show "Because you liked" sections */}
          {Object.keys(groupedItems)
            .filter(reason => reason.startsWith('Because you liked'))
            .map(reason => {
              const song = reason.replace('Because you liked ', '');
              return (
                <div key={reason} className="discover-section">
                  <h2 className="section-header">Because you liked "{song}"</h2>
                  <div className="discover-grid">
                    {groupedItems[reason].map((item) => (
                      <div key={item.id} className="discover-card">
                        <div className="discover-card-content">
                          <span className="discover-track-name">{item.track}</span>
                          <span className="discover-artist-name">{item.artist}</span>
                        </div>
                        <button
                          className="btn btn-sm"
                          title={user ? 'Add to log' : 'Sign in to log'}
                          onClick={() => handleLogFromItem(item)}
                          disabled={!user}
                        >
                          ➕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          
          {/* Show "Because you like" sections */}
          {Object.keys(groupedItems)
            .filter(reason => reason.startsWith('Because you like') && !reason.startsWith('Because you liked'))
            .map(reason => {
              const artist = reason.replace('Because you like ', '');
              return (
                <div key={reason} className="discover-section">
                  <h2 className="section-header">Because you like {artist}</h2>
                  <div className="discover-grid">
                    {groupedItems[reason].map((item) => (
                      <div key={item.id} className="discover-card">
                        <div className="discover-card-content">
                          <span className="discover-track-name">
                            {item.track.startsWith('Artist: ') ? item.track.replace('Artist: ', '') : item.track}
                          </span>
                          {!item.track.startsWith('Artist: ') && (
                            <span className="discover-artist-name">{item.artist}</span>
                          )}
                        </div>
                        <button
                          className="btn btn-sm"
                          title={user ? 'Add to log' : 'Sign in to log'}
                          onClick={() => handleLogFromItem(item)}
                          disabled={!user}
                        >
                          ➕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          
          {/* Show "When you're feeling" sections */}
          {Object.keys(groupedItems)
            .filter(reason => reason.startsWith("When you're feeling"))
            .map(reason => {
              const tag = reason.replace("When you're feeling ", '');
              return (
                <div key={reason} className="discover-section">
                  <h2 className="section-header">When you're feeling {tag}</h2>
                  <div className="discover-grid">
                    {groupedItems[reason].map((item) => (
                      <div key={item.id} className="discover-card">
                        <div className="discover-card-content">
                          <span className="discover-track-name">
                            {item.track.startsWith('Artist: ') ? item.track.replace('Artist: ', '') : item.track}
                          </span>
                          {!item.track.startsWith('Artist: ') && (
                            <span className="discover-artist-name">{item.artist}</span>
                          )}
                        </div>
                        <button
                          className="btn btn-sm"
                          title={user ? 'Add to log' : 'Sign in to log'}
                          onClick={() => handleLogFromItem(item)}
                          disabled={!user}
                        >
                          ➕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          
          {/* Show chart sections */}
          {Object.keys(groupedItems)
            .filter(reason => reason === 'Top artist this week' || reason === 'Top track this week')
            .map(reason => (
              <div key={reason} className="discover-section">
                <h2 className="section-header">
                  {reason === 'Top artist this week' ? 'Top Artists This Week' : 'Top Tracks This Week'}
                </h2>
                <div className="discover-grid">
                  {groupedItems[reason].map((item) => (
                    <div key={item.id} className="discover-card">
                      <div className="discover-card-content">
                        <span className="discover-track-name">
                          {item.track.startsWith('Artist: ') ? item.track.replace('Artist: ', '') : item.track}
                        </span>
                        {!item.track.startsWith('Artist: ') && (
                          <span className="discover-artist-name">{item.artist}</span>
                        )}
                      </div>
                      <button
                        className="btn btn-sm"
                        title={user ? 'Add to log' : 'Sign in to log'}
                        onClick={() => handleLogFromItem(item)}
                        disabled={!user}
                      >
                        ➕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <p className="empty-state">
          {user 
            ? 'No recommendations right now. Log some tracks and tags to get personalized discover.'
            : 'No recommendations available.'}
        </p>
      )}

      {selectedTrack && (
        <LogSongModal
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
          onSuccess={() => setSelectedTrack(null)}
        />
      )}

      {selectedArtist && (
        <LogArtistModal
          artist={selectedArtist}
          onClose={() => setSelectedArtist(null)}
          onSuccess={() => setSelectedArtist(null)}
        />
      )}
    </section>
  );
}
