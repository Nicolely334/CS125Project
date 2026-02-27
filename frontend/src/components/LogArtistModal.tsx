import { useEffect, useState } from 'react';
import { createTag, getPresetTags, getUserCustomTags, logArtist, type PresetTag, type Tag } from '../services/logs';
import type { ArtistSearchResult } from '../services/api';

interface LogArtistModalProps {
  artist: ArtistSearchResult;
  onClose: () => void;
  onSuccess: () => void;
}

export function LogArtistModal({ artist, onClose, onSuccess }: LogArtistModalProps) {
  const [liked, setLiked] = useState(false);
  const [favorite, setFavorite] = useState(false);
  const [notes, setNotes] = useState('');
  const [genre, setGenre] = useState('');
  const [presetTags, setPresetTags] = useState<PresetTag[]>([]);
  const [customTags, setCustomTags] = useState<Tag[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [selectedCustomTagIds, setSelectedCustomTagIds] = useState<number[]>([]);
  const [newTagName, setNewTagName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingTags, setLoadingTags] = useState(true);

  useEffect(() => {
    loadTags();
  }, []);

  async function loadTags() {
    try {
      const [presets, custom] = await Promise.all([
        getPresetTags(),
        getUserCustomTags(),
      ]);
      setPresetTags(presets);
      setCustomTags(custom);
    } catch (err) {
      console.error('Failed to load tags:', err);
    } finally {
      setLoadingTags(false);
    }
  }

  async function handleCreateTag() {
    if (!newTagName.trim()) return;
    try {
      const newTag = await createTag(newTagName.trim());
      setCustomTags([...customTags, newTag]);
      if (!selectedCustomTagIds.includes(newTag.id)) {
        setSelectedCustomTagIds([...selectedCustomTagIds, newTag.id]);
      }
      setNewTagName('');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create tag');
    }
  }

  function toggleTag(tagId: number) {
    if (selectedTagIds.includes(tagId)) {
      setSelectedTagIds(selectedTagIds.filter(id => id !== tagId));
    } else {
      setSelectedTagIds([...selectedTagIds, tagId]);
    }
  }

  function toggleCustomTag(tagId: number) {
    if (selectedCustomTagIds.includes(tagId)) {
      setSelectedCustomTagIds(selectedCustomTagIds.filter(id => id !== tagId));
    } else {
      setSelectedCustomTagIds([...selectedCustomTagIds, tagId]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await logArtist({
        artist_id: artist.id,
        artist_name: artist.name,
        genre: genre.trim() || undefined,
        genres: genre.trim() ? [genre.trim()] : undefined,
        liked,
        favorite,
        notes: notes.trim() || undefined,
        tagIds: selectedTagIds.length > 0 ? selectedTagIds : undefined,
        customTagIds: selectedCustomTagIds.length > 0 ? selectedCustomTagIds : undefined,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log artist');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h2>Log Artist</h2>

        <div style={{ marginBottom: '1rem' }}>
          <strong>{artist.name}</strong>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Quick Actions</label>
            <div className="quick-actions">
              <button
                type="button"
                className={`action-button ${liked ? 'active' : ''}`}
                onClick={() => setLiked(!liked)}
              >
                <span className="action-icon">❤️</span>
                <span>Liked</span>
              </button>
              <button
                type="button"
                className={`action-button ${favorite ? 'active' : ''}`}
                onClick={() => setFavorite(!favorite)}
              >
                <span className="action-icon">⭐</span>
                <span>Favorite</span>
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="artist-genre">Genre</label>
            <input
              id="artist-genre"
              type="text"
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              placeholder="e.g., Indie Pop, Hip-Hop..."
            />
          </div>

          <div className="form-group">
            <label htmlFor="artist-notes">Notes</label>
            <textarea
              id="artist-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label>Tags</label>
            {loadingTags ? (
              <p>Loading tags...</p>
            ) : (
              <>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
                    Preset Tags:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {presetTags.map((tag) => (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => toggleTag(tag.id)}
                        className="tag-button"
                        style={{
                          background: selectedTagIds.includes(tag.id)
                            ? 'rgba(245, 197, 66, 0.3)'
                            : 'rgba(255, 255, 255, 0.1)',
                          border: selectedTagIds.includes(tag.id)
                            ? '1px solid rgba(245, 197, 66, 0.5)'
                            : '1px solid rgba(255, 255, 255, 0.2)',
                          cursor: 'pointer',
                          padding: '0.4rem 0.8rem',
                          borderRadius: '6px',
                          fontSize: '0.85rem',
                          transition: 'all 0.2s',
                        }}
                      >
                        {tag.name} {selectedTagIds.includes(tag.id) ? '✓' : ''}
                      </button>
                    ))}
                  </div>
                </div>

                {customTags.length > 0 && (
                  <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
                      Your Custom Tags:
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {customTags.map((tag) => (
                        <button
                          key={tag.id}
                          type="button"
                          onClick={() => toggleCustomTag(tag.id)}
                          className="tag-button"
                          style={{
                            background: selectedCustomTagIds.includes(tag.id)
                              ? 'rgba(245, 197, 66, 0.3)'
                              : 'rgba(255, 255, 255, 0.1)',
                            border: selectedCustomTagIds.includes(tag.id)
                              ? '1px solid rgba(245, 197, 66, 0.5)'
                              : '1px solid rgba(255, 255, 255, 0.2)',
                            cursor: 'pointer',
                            padding: '0.4rem 0.8rem',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            transition: 'all 0.2s',
                          }}
                        >
                          {tag.name} {selectedCustomTagIds.includes(tag.id) ? '✓' : ''}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
                    Create Custom Tag:
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="text"
                      value={newTagName}
                      onChange={(e) => setNewTagName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleCreateTag();
                        }
                      }}
                      placeholder="Type custom tag name..."
                      style={{ flex: 1, padding: '0.5rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(0,0,0,0.2)', color: '#fff' }}
                    />
                    <button type="button" onClick={handleCreateTag} className="btn btn-sm">
                      Add
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button type="button" onClick={onClose} className="btn" style={{ flex: 1 }}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
              {loading ? 'Logging...' : 'Log Artist'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
