import { useState } from 'react';
import { searchTracks, searchArtists, type Track, type ArtistSearchResult } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { LogSongModal } from '../components/LogSongModal';
import { LogArtistModal } from '../components/LogArtistModal';

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [artist, setArtist] = useState('');
  const [tracks, setTracks] = useState<Track[]>([]);
  const [artists, setArtists] = useState<ArtistSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const [selectedArtist, setSelectedArtist] = useState<ArtistSearchResult | null>(null);
  const [didSearch, setDidSearch] = useState(false);
  const { user } = useAuth();

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const trackQ = query.trim();
    const artistQ = artist.trim();
    if (!trackQ && !artistQ) return;
    setLoading(true);
    setError(null);
    setTracks([]);
    setArtists([]);
    setDidSearch(true);
    try {
      if (trackQ) {
        const results = await searchTracks(trackQ, {
          artist: artistQ || undefined,
          limit: 20,
        });
        setTracks(results);
      } else {
        const results = await searchArtists(artistQ, { limit: 20 });
        setArtists(results);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setTracks([]);
      setArtists([]);
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

  function handleArtistLogClick(artistResult: ArtistSearchResult) {
    if (!user) {
      setError('Please sign in to log artists');
      return;
    }
    setSelectedArtist(artistResult);
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
            placeholder="Track name (leave empty to search artists)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="search-input"
            autoFocus
          />
          <input
            type="text"
            placeholder="Artist (optional for tracks; use for artist search when track is empty)"
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
          <h2>Track results</h2>
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

      {artists.length > 0 && (
        <div className="track-list">
          <h2>Artist results</h2>
          <ul>
            {artists.map((a) => (
              <li key={a.id} className="track-card">
                <div className="track-info">
                  <span className="track-name">{a.name}</span>
                </div>
                <div className="track-actions">
                  <button
                    className="btn btn-sm"
                    title="Add artist to log"
                    onClick={() => handleArtistLogClick(a)}
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

      {!loading && didSearch && tracks.length === 0 && artists.length === 0 && !error && (
        <p className="empty-state">
          No results found. Try a different search.
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
