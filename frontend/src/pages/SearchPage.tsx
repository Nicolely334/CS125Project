import { useState } from 'react';
import { searchTracks, type Track } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { LogSongModal } from '../components/LogSongModal';

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [artist, setArtist] = useState('');
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const { user } = useAuth();

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const results = await searchTracks(query, {
        artist: artist.trim() || undefined,
        limit: 20,
      });
      setTracks(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setTracks([]);
    } finally {
      setLoading(false);
    }
  }

  function handleLogClick(track: Track) {
    if (!user) {
      setError('Please sign in to log songs');
      return;
    }
    setSelectedTrack(track);
  }

  return (
    <section className="page search-page">
      <h1>Search & Log Music</h1>
      <p className="page-desc">
        Find songs to rate, tag with mood/activity, and save to your personal listening log.
      </p>

      <form onSubmit={handleSearch} className="search-form">
        <div className="form-row">
          <input
            type="text"
            placeholder="Track name..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="search-input"
            autoFocus
          />
          <input
            type="text"
            placeholder="Artist (optional)"
            value={artist}
            onChange={(e) => setArtist(e.target.value)}
            className="search-input search-input--secondary"
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {tracks.length > 0 && (
        <div className="track-list">
          <h2>Results</h2>
          <ul>
            {tracks.map((t) => (
              <li key={t.id} className="track-card">
                <div className="track-info">
                  <span className="track-name">{t.track}</span>
                  <span className="track-artist">{t.artist}</span>
                </div>
                <div className="track-actions">
                  <button
                    className="btn btn-sm"
                    title="Add to log"
                    onClick={() => handleLogClick(t)}
                    disabled={!user}
                  >
                    ➕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!loading && query && tracks.length === 0 && !error && (
        <p className="empty-state">No tracks found. Try a different search.</p>
      )}

      {selectedTrack && (
        <LogSongModal
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
          onSuccess={() => setSelectedTrack(null)}
        />
      )}
    </section>
  );
}
