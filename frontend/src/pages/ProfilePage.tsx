import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getUserLogsWithTags, deleteLog } from '../services/logs';
import { AuthModal } from '../components/AuthModal';
import type { Tag } from '../services/logs';

interface LogWithTags {
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
  tags?: Tag[];
}

export function ProfilePage() {
  const { user, loading: authLoading } = useAuth();
  const [logs, setLogs] = useState<LogWithTags[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    if (user && !authLoading) {
      loadLogs();
    }
  }, [user, authLoading]);

  async function loadLogs() {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    try {
      const userLogs = await getUserLogsWithTags(100);
      setLogs(userLogs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteLog(logId: number) {
    if (!confirm('Are you sure you want to delete this log entry?')) {
      return;
    }

    try {
      await deleteLog(logId);
      setLogs(logs.filter(log => log.id !== logId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete log');
    }
  }

  if (authLoading) {
    return (
      <section className="page profile-page">
        <h1>Your Profile</h1>
        <p>Loading...</p>
      </section>
    );
  }

  if (!user) {
    return (
      <section className="page profile-page">
        <h1>Your Profile</h1>
        <p className="page-desc">
          Sign in to view your logged tracks, ratings, favorites, and listening history.
        </p>
        <button
          onClick={() => setShowAuthModal(true)}
          className="btn btn-primary"
        >
          Sign In
        </button>
        {showAuthModal && (
          <AuthModal
            onClose={() => setShowAuthModal(false)}
            initialMode="signin"
          />
        )}
      </section>
    );
  }

  return (
    <section className="page profile-page">
      <h1>Your Profile</h1>
      <p className="page-desc">
        Your logged tracks, ratings, favorites, and listening history.
      </p>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {loading ? (
        <p>Loading your logs...</p>
      ) : logs.length === 0 ? (
        <div className="placeholder-card">
          <p>No songs logged yet.</p>
          <p>Search for songs and click the ➕ button to add them to your log!</p>
        </div>
      ) : (
        <div className="track-list">
          <h2>Your Listening Log ({logs.length})</h2>
          <ul>
            {logs.map((log) => (
              <li key={log.id} className="track-card">
                <div className="track-info">
                  <span className="track-name">
                    {log.track || `Track ID: ${log.track_id}`}
                    {log.rating !== undefined && log.rating !== null && (
                      <span className="rating" style={{ marginLeft: '0.5rem', color: '#f5c542' }}>
                        ⭐ {log.rating}/5
                      </span>
                    )}
                    {log.liked && (
                      <span className="liked" style={{ marginLeft: '0.5rem' }}>❤️</span>
                    )}
                    {log.favorite && (
                      <span className="favorite" style={{ marginLeft: '0.5rem', color: '#f5c542' }}>⭐</span>
                    )}
                  </span>
                  <span className="track-artist">
                    {log.artist || 'Unknown Artist'}
                    {log.genre && (
                      <span style={{ marginLeft: '0.5rem', fontSize: '0.85rem', color: 'rgba(255,255,255,0.5)' }}>
                        • {log.genre}
                      </span>
                    )}
                  </span>
                  {log.tags && log.tags.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.5rem' }}>
                      {log.tags.map((tag) => (
                        <span
                          key={tag.id}
                          style={{
                            fontSize: '0.75rem',
                            padding: '0.25rem 0.5rem',
                            background: 'rgba(245, 197, 66, 0.2)',
                            borderRadius: '4px',
                            color: '#f5c542',
                          }}
                        >
                          {tag.name}
                        </span>
                      ))}
                    </div>
                  )}
                  {log.notes && (
                    <span className="notes" style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)', marginTop: '0.5rem', display: 'block' }}>
                      Notes: {log.notes}
                    </span>
                  )}
                  <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.25rem', display: 'block' }}>
                    Logged: {new Date(log.logged_at).toLocaleDateString()} at{' '}
                    {new Date(log.logged_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="track-actions">
                  <button
                    className="btn btn-sm"
                    title="Delete"
                    onClick={() => handleDeleteLog(log.id)}
                  >
                    🗑️
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
