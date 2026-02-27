import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getDiscoverRecommendations, type RecommendationItem } from '../services/api';

export function DiscoverPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getDiscoverRecommendations({
      user_id: user?.id ?? undefined,
      limit: 30,
    })
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load discover');
          setItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [user?.id]);

  return (
    <section className="page discover-page">
      <h1>Discover</h1>
      <p className="page-desc">
        Recommendations from your logged artists, tags, and genres plus global charts.
      </p>

      {loading && <p className="loading-state">Loading recommendations…</p>}
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="track-list">
          <h2>For you</h2>
          <ul>
            {items.map((item) => (
              <li key={item.id} className="track-card">
                <div className="track-info">
                  <span className="track-name">{item.track}</span>
                  <span className="track-artist">{item.artist}</span>
                  {item.reason && (
                    <span className="track-reason">{item.reason}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <p className="empty-state">No recommendations right now. Log some tracks and tags to get personalized discover.</p>
      )}
    </section>
  );
}
