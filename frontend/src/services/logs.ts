import { supabase } from './supabase';
import type { ListeningLog } from './api';

export interface LogSongParams {
  track_id: string;
  track: string;
  artist: string;
  genre?: string;
  rating?: number;
  liked?: boolean;
  favorite?: boolean;
  notes?: string;
  tagIds?: number[];
  customTagIds?: number[];
}

export interface Tag {
  id: number;
  name: string;
}

export interface PresetTag {
  id: number;
  name: string;
  category: string;
  created_at: string;
}

export async function logSong(params: LogSongParams): Promise<ListeningLog> {
  const { data: { user }, error: userError } = await supabase.auth.getUser();
  if (userError || !user) {
    throw new Error('You must be signed in to log songs');
  }

  const { data: logData, error: logError } = await supabase
    .from('listening_logs')
    .insert({
      user_id: user.id,
      track_id: params.track_id,
      track: params.track,
      artist: params.artist,
      genre: params.genre,
      rating: params.rating,
      liked: params.liked ?? false,
      favorite: params.favorite ?? false,
      notes: params.notes,
    })
    .select()
    .single();

  if (logError) {
    throw new Error(logError.message || 'Failed to log song');
  }

  if ((params.tagIds && params.tagIds.length > 0) || (params.customTagIds && params.customTagIds.length > 0)) {
    const logTags: any[] = [];
    if (params.tagIds) {
      params.tagIds.forEach(tagId => logTags.push({ log_id: logData.id, tag_id: tagId }));
    }
    if (params.customTagIds) {
      params.customTagIds.forEach(tagId => logTags.push({ log_id: logData.id, user_tag_id: tagId }));
    }
    const { error: tagError } = await supabase.from('log_tags').insert(logTags);
    if (tagError) {
      console.warn('Failed to add tags:', tagError);
    }
  }

  return logData;
}

export async function getUserLogsWithTags(limit: number = 50, offset: number = 0): Promise<(ListeningLog & { tags?: Tag[] })[]> {
  const { data, error } = await supabase
    .from('listening_logs')
    .select(`
      *,
      log_tags(
        tag_id,
        user_tag_id,
        preset_tags(id, name)
      )
    `)
    .order('logged_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(error.message || 'Failed to fetch logs');
  }

  // Get all unique user_tag_ids to fetch custom tags
  const userTagIds = new Set<number>();
  (data || []).forEach((log: any) => {
    (log.log_tags || []).forEach((lt: any) => {
      if (lt.user_tag_id) {
        userTagIds.add(lt.user_tag_id);
      }
    });
  });

  // Fetch custom tags in one query
  const customTagsMap: Record<number, Tag> = {};
  if (userTagIds.size > 0) {
    const { data: customTags } = await supabase
      .from('tags')
      .select('id, name')
      .in('id', Array.from(userTagIds));
    
    (customTags || []).forEach((tag: any) => {
      customTagsMap[tag.id] = { id: tag.id, name: tag.name };
    });
  }

  return (data || []).map((log: any) => {
    const tags: Tag[] = [];
    (log.log_tags || []).forEach((lt: any) => {
      if (lt.preset_tags) {
        tags.push({ id: lt.preset_tags.id, name: lt.preset_tags.name });
      } else if (lt.user_tag_id && customTagsMap[lt.user_tag_id]) {
        tags.push(customTagsMap[lt.user_tag_id]);
      }
    });
    return { ...log, tags };
  });
}

export async function deleteLog(logId: number): Promise<void> {
  const { error } = await supabase
    .from('listening_logs')
    .delete()
    .eq('id', logId);

  if (error) {
    throw new Error(error.message || 'Failed to delete log');
  }
}

// Tag management functions
export async function getPresetTags(): Promise<PresetTag[]> {
  const { data, error } = await supabase
    .from('preset_tags')
    .select('*')
    .order('category', { ascending: true })
    .order('name', { ascending: true });

  if (error) {
    throw new Error(error.message || 'Failed to fetch preset tags');
  }

  return data || [];
}

export async function getUserCustomTags(): Promise<Tag[]> {
  const { data, error } = await supabase
    .from('tags')
    .select('id, name')
    .order('name', { ascending: true });

  if (error) {
    throw new Error(error.message || 'Failed to fetch custom tags');
  }

  return (data || []).map(tag => ({ id: tag.id, name: tag.name }));
}

export async function createTag(name: string): Promise<Tag> {
  const { data: { user }, error: userError } = await supabase.auth.getUser();
  if (userError || !user) {
    throw new Error('You must be signed in to create tags');
  }

  const { data, error } = await supabase
    .from('tags')
    .insert({ 
      user_id: user.id,  // Explicitly set user_id for RLS policy
      name: name.trim() 
    })
    .select()
    .single();

  if (error) {
    throw new Error(error.message || 'Failed to create tag');
  }

  return { id: data.id, name: data.name };
}

export async function addTagsToLog(logId: number, tagIds: number[], customTagIds?: number[]): Promise<void> {
  if (tagIds.length === 0 && (!customTagIds || customTagIds.length === 0)) return;
  
  const logTags: any[] = [];
  
  // Add preset tags
  tagIds.forEach(tagId => {
    logTags.push({ log_id: logId, tag_id: tagId });
  });
  
  // Add custom tags
  if (customTagIds) {
    customTagIds.forEach(tagId => {
      logTags.push({ log_id: logId, user_tag_id: tagId });
    });
  }
  
  const { error } = await supabase.from('log_tags').insert(logTags);
  if (error) {
    throw new Error(error.message || 'Failed to add tags to log');
  }
}

