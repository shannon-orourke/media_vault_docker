import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types - Aligned with backend schema
export interface MediaFile {
  id: number;
  filename: string;
  filepath: string;
  file_size: number;
  md5_hash: string;
  duration: number | null;
  format: string | null;
  video_codec: string | null;
  audio_codec: string | null;
  resolution: string | null;
  width: number | null;
  height: number | null;
  bitrate: number | null;
  framerate: number | null;
  quality_tier: string | null;
  quality_score: number | null;
  hdr_type: string | null;
  audio_channels: number | null;
  audio_track_count: number | null;
  subtitle_track_count: number | null;
  audio_languages: string[] | null;
  subtitle_languages: string[] | null;
  dominant_audio_language: string | null;
  parsed_title: string | null;
  parsed_year: number | null;
  parsed_season: number | null;
  parsed_episode: number | null;
  media_type: string | null;
  is_duplicate: boolean;
  discovered_at: string;
  tmdb_id: number | null;
  tmdb_type: string | null;
  imdb_id: string | null;
}

export interface RenameHistoryEntry {
  old_filename: string;
  new_filename: string;
  old_filepath?: string;
  new_filepath?: string;
  renamed_at: string;
  renamed_by_user_id?: number | null;
}

export interface TMDBSearchResult {
  id: number;
  title?: string;
  name?: string;
  media_type?: string;
  overview?: string;
  release_date?: string;
  first_air_date?: string;
  poster_path?: string | null;
}

export interface ScanHistory {
  id: number;
  scan_type: string;
  nas_paths: string[];
  scan_started_at: string;
  scan_completed_at: string | null;
  duration_seconds: number | null;
  status: string;
  files_found: number;
  files_new: number;
  files_updated: number;
  errors_count: number;
}

export interface DuplicateGroup {
  id: number;
  title: string | null;
  year: number | null;
  media_type: string | null;
  duplicate_type: string;
  confidence: number | null;
  member_count: number;
  recommended_action: string | null;
  action_reason: string | null;
  detected_at: string;
}

export interface DuplicateMember {
  rank: number;
  recommended_action: string;
  action_reason: string | null;
  file: MediaFile;
}

export interface StartScanRequest {
  paths: string[];
  scan_type: 'full' | 'incremental';
}

export interface StartScanResponse {
  scan_id: number;
  scan_type: string;
  status: string;
  files_found: number;
  files_new: number;
  files_updated: number;
  errors_count: number;
  message: string;
}

export interface DeduplicateResponse {
  exact_duplicates: number;
  fuzzy_duplicates: number;
  groups_created: number;
  total_members: number;
}

// Response types
export interface MediaListResponse {
  total: number;
  skip: number;
  limit: number;
  files: MediaFile[];
}

export interface DuplicateGroupsResponse {
  total: number;
  skip: number;
  limit: number;
  groups: DuplicateGroup[];
}

// Archive types
export interface ArchiveFile {
  id: number;
  filename: string;
  filepath: string;
  file_size: number;
  archive_type: string;
  extraction_status: string;
  parsed_title: string | null;
  parsed_year: number | null;
  media_type: string | null;
  destination_path: string | null;
  extracted_to_path: string | null;
  mark_for_deletion_at: string | null;
  discovered_at: string;
}

export interface ArchiveListResponse {
  total: number;
  skip: number;
  limit: number;
  archives: ArchiveFile[];
}

export interface ScanArchivesRequest {
  paths?: string[];
}

// Batch operation types
export interface BatchRenamePayload {
  file_ids: number[];
  pattern?: string;
  prefix?: string;
  suffix?: string;
  replace_old?: string;
  replace_new?: string;
}

export interface BatchRenameResponse {
  success_count: number;
  total: number;
  results: Array<{
    old_filename: string;
    new_filename: string;
    old_path?: string;
    new_path?: string;
  }>;
  failures: Array<{
    file_id: number;
    filename?: string;
    error: string;
  }>;
}

export interface BatchDeleteResponse {
  success: boolean;
  staged_count: number;
  failed_count: number;
  deleted_count: number;
  failures?: Array<{ file_id: number; error: string }>;
}

// Pending Deletions types
export interface PendingDeletion {
  id: number;
  media_file_id: number;
  filename: string | null;
  original_filepath: string;
  temp_filepath: string | null;
  file_size: number;
  reason: string;
  duplicate_group_id: number | null;
  quality_score_diff: number | null;
  language_concern: boolean;
  language_concern_reason?: string | null;
  staged_at: string | null;
  approved_for_deletion: boolean;
}

export interface PendingDeletionsResponse {
  total: number;
  skip: number;
  limit: number;
  pending: PendingDeletion[];
}

export interface ActionResponse {
  success: boolean;
  message: string;
}

export interface CleanupResponse {
  status: string;
  message: string;
  deleted: number;
}

// API Functions
export const mediaApi = {
  // Media endpoints
  listMedia: (params?: { limit?: number; skip?: number }) =>
    api.get<MediaListResponse>('/media/', { params }),

  getMedia: (id: number) =>
    api.get<MediaFile>(`/media/${id}`),

  deleteMedia: (id: number) =>
    api.delete(`/media/${id}`),

  batchDelete: (fileIds: number[], reason?: string) =>
    api.post<BatchDeleteResponse>('/media/batch-delete', {
      file_ids: fileIds,
      reason,
    }),

  // Rename endpoints
  renameFile: (fileId: number, newFilename: string) =>
    api.post(`/rename/${fileId}`, { new_filename: newFilename }),

  batchRename: (payload: BatchRenamePayload) =>
    api.post<BatchRenameResponse>('/rename/batch', payload),

  getRenameHistory: (fileId: number) =>
    api.get<{ file_id: number; history: RenameHistoryEntry[] }>(`/rename/${fileId}/history`),

  revertRename: (fileId: number, historyIndex: number) =>
    api.post(`/rename/${fileId}/revert`, null, { params: { history_index: historyIndex } }),

  tmdbSearch: (fileId: number, query: string, mediaType: string, year?: number) =>
    api.post<{ query: string; results: TMDBSearchResult[] }>(`/rename/${fileId}/tmdb-search`, {
      query,
      media_type: mediaType,
      year,
    }),

  tmdbApply: (fileId: number, tmdbId: number, mediaType: string, enrichMetadata: boolean) =>
    api.post(`/rename/${fileId}/tmdb-apply`, {
      tmdb_id: tmdbId,
      media_type: mediaType,
      enrich_metadata: enrichMetadata,
    }),

  // Batch deletions handled above

  // Scan endpoints
  startScan: (data: StartScanRequest) =>
    api.post<StartScanResponse>('/scan/start', data),

  getScanHistory: (limit = 10) =>
    api.get<ScanHistory[]>('/scan/history', { params: { limit } }),

  runDeduplicate: () =>
    api.post<DeduplicateResponse>('/scan/deduplicate'),

  // Duplicate endpoints
  listDuplicateGroups: () =>
    api.get<DuplicateGroupsResponse>('/duplicates/groups'),

  getDuplicateGroup: (id: number) =>
    api.get<DuplicateGroup & { members: DuplicateMember[] }>(`/duplicates/groups/${id}`),

  keepFile: (groupId: number, fileId: number) =>
    api.post(`/duplicates/${groupId}/keep/${fileId}`),

  dismissGroup: (groupId: number) =>
    api.delete(`/duplicates/${groupId}`),

  // Pending Deletions endpoints
  listPendingDeletions: (params?: { skip?: number; limit?: number; language_concern?: boolean }) =>
    api.get<PendingDeletionsResponse>('/deletions/pending', { params }),

  restoreFile: (pendingId: number) =>
    api.post<ActionResponse>(`/deletions/${pendingId}/restore`),

  approveDeletion: (pendingId: number) =>
    api.post<ActionResponse>(`/deletions/${pendingId}/approve`),

  cleanupOldPending: () =>
    api.post<CleanupResponse>('/deletions/cleanup'),

  // Archive endpoints
  scanArchives: (data: ScanArchivesRequest) =>
    api.post('/archives/scan', data),

  listArchives: (params?: { status?: string; limit?: number; skip?: number }) =>
    api.get<ArchiveListResponse>('/archives', { params }),

  getArchive: (id: number) =>
    api.get<ArchiveFile>(`/archives/${id}`),

  extractArchive: (id: number, destination?: string) =>
    api.post(`/archives/${id}/extract`, { destination }),

  markArchiveForDeletion: (id: number) =>
    api.post(`/archives/${id}/mark-for-deletion`),

  deleteArchive: (id: number) =>
    api.delete(`/archives/${id}`),

  cleanupOldArchives: () =>
    api.post('/archives/cleanup'),

  // Health check
  health: () =>
    api.get<{ status: string; app: string; version: string; environment: string }>('/health'),
};

export default api;
