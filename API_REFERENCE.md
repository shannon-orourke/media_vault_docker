# MediaVault API Reference

Base URL: `http://localhost:8007/api`

Production: `https://mediavault.orourkes.me/api`

---

## Media Files

### List Media Files
```
GET /media/
```

**Query Parameters:**
- `skip` (int): Offset for pagination (default: 0)
- `limit` (int): Number of results (default: 50)
- `media_type` (string): Filter by type ("movie", "tv", etc.)
- `is_duplicate` (bool): Filter duplicates only

**Response:**
```json
{
  "total": 100,
  "skip": 0,
  "limit": 50,
  "files": [
    {
      "id": 1,
      "filename": "Movie.mkv",
      "filepath": "/mnt/nas/movies/Movie.mkv",
      "file_size": 5368709120,
      "media_type": "movie",
      "quality_tier": "high",
      "quality_score": 135,
      "resolution": "1080p",
      "video_codec": "H.264",
      "is_duplicate": false,
      "discovered_at": "2025-11-08T18:30:00"
    }
  ]
}
```

### Get Media File Details
```
GET /media/{file_id}
```

**Response:**
```json
{
  "id": 1,
  "filename": "Movie.mkv",
  "filepath": "/mnt/nas/movies/Movie.mkv",
  "file_size": 5368709120,
  "md5_hash": "abc123def456...",
  "duration": 7200.0,
  "format": "matroska",
  "video_codec": "H.264",
  "audio_codec": "AAC",
  "resolution": "1080p",
  "width": 1920,
  "height": 1080,
  "bitrate": 8000,
  "framerate": 23.976,
  "quality_tier": "high",
  "quality_score": 135,
  "hdr_type": null,
  "audio_channels": 5.1,
  "audio_track_count": 2,
  "subtitle_track_count": 3,
  "audio_languages": ["eng", "spa"],
  "subtitle_languages": ["eng", "spa", "fre"],
  "dominant_audio_language": "eng",
  "parsed_title": "Movie Title",
  "parsed_year": 2020,
  "media_type": "movie",
  "is_duplicate": false,
  "discovered_at": "2025-11-08T18:30:00"
}
```

### Delete Media File (Stage for Deletion)
```
DELETE /media/{file_id}
```

**Response:**
```json
{
  "status": "staged",
  "message": "File moved to /volume1/video/duplicates_before_purge/movies/2025-11-08/Movie.mkv",
  "pending_deletion_id": 123
}
```

### Get Media Statistics
```
GET /media/stats/summary
```

**Response:**
```json
{
  "total_files": 1000,
  "total_size_bytes": 5497558138880,
  "total_size_gb": 5120.0,
  "by_type": {
    "movie": 450,
    "tv": 550
  },
  "by_quality": {
    "high": 600,
    "medium": 300,
    "low": 100
  },
  "duplicates": 45
}
```

---

## Scanning

### Start Scan
```
POST /scan/start
```

**Request:**
```json
{
  "paths": ["/mnt/nas-synology/transmission/downloads/complete/tv/Red.Dwarf"],
  "scan_type": "full"
}
```

**Response:**
```json
{
  "scan_id": 22,
  "status": "started",
  "message": "Scan started successfully"
}
```

### Get Scan History
```
GET /scan/history?limit=10
```

**Response:**
```json
[
  {
    "id": 22,
    "scan_type": "full",
    "nas_paths": ["/mnt/nas-synology/..."],
    "scan_started_at": "2025-11-08T17:56:03",
    "scan_completed_at": "2025-11-08T18:12:33",
    "status": "completed",
    "files_found": 61,
    "files_new": 61,
    "files_updated": 0,
    "errors_count": 0
  }
]
```

### Run Deduplication
```
POST /scan/deduplicate
```

**Response:**
```json
{
  "exact_duplicates": 5,
  "fuzzy_duplicates": 3,
  "groups_created": 8,
  "total_members": 18,
  "message": "Found 5 exact and 3 fuzzy duplicate groups"
}
```

---

## Duplicates

### List Duplicate Groups
```
GET /duplicates/groups
```

**Query Parameters:**
- `skip` (int): Offset for pagination
- `limit` (int): Number of results (default: 50)
- `reviewed` (bool): Filter by review status
- `recommended_action` (string): Filter by action ("delete", "keep", etc.)

**Response:**
```json
{
  "total": 10,
  "skip": 0,
  "limit": 50,
  "groups": [
    {
      "id": 1,
      "title": "Star Trek TNG",
      "year": 1987,
      "media_type": "tv",
      "duplicate_type": "exact",
      "confidence": 100.00,
      "member_count": 2,
      "recommended_action": "delete",
      "action_reason": "Lower quality duplicate",
      "detected_at": "2025-11-08T18:30:00"
    }
  ]
}
```

### Get Duplicate Group Details
```
GET /duplicates/groups/{group_id}
```

**Response:**
```json
{
  "id": 1,
  "title": "Star Trek TNG - S01E01",
  "duplicate_type": "exact",
  "confidence": 100.00,
  "member_count": 2,
  "members": [
    {
      "rank": 1,
      "recommended_action": "keep",
      "action_reason": "Highest quality",
      "file": {
        "id": 101,
        "filename": "TNG.S01E01.1080p.mkv",
        "filepath": "/path/to/file.mkv",
        "file_size": 3221225472,
        "quality_score": 145,
        "resolution": "1080p",
        "video_codec": "H.265",
        "audio_codec": "AAC",
        "hdr_type": null,
        "audio_languages": ["eng"]
      }
    },
    {
      "rank": 2,
      "recommended_action": "delete",
      "action_reason": "Lower quality (score difference: 35)",
      "file": {
        "id": 102,
        "filename": "TNG.S01E01.720p.mkv",
        "filepath": "/path/to/file2.mkv",
        "file_size": 1073741824,
        "quality_score": 110,
        "resolution": "720p",
        "video_codec": "H.264",
        "audio_codec": "AAC",
        "hdr_type": null,
        "audio_languages": ["eng"]
      }
    }
  ]
}
```

### Mark File as Keeper
```
POST /duplicates/{group_id}/keep/{file_id}
```

**Response:**
```json
{
  "status": "ok"
}
```

### Dismiss Duplicate Group
```
DELETE /duplicates/{group_id}
```

**Response:**
```json
{
  "status": "ok"
}
```

---

## Deletions

### List Pending Deletions
```
GET /deletions/pending
```

**Query Parameters:**
- `skip` (int): Offset for pagination
- `limit` (int): Number of results (default: 50)

**Response:**
```json
{
  "total": 5,
  "skip": 0,
  "limit": 50,
  "pending": [
    {
      "id": 1,
      "media_file_id": 456,
      "filename": "Movie.1080p.mkv",
      "original_filepath": "/mnt/nas/movies/Movie.1080p.mkv",
      "temp_filepath": "/volume1/video/duplicates_before_purge/movies/2025-11-08/Movie.1080p.mkv",
      "file_size": 5368709120,
      "reason": "Lower quality duplicate",
      "duplicate_group_id": 789,
      "quality_score_diff": 35,
      "language_concern": false,
      "language_concern_reason": null,
      "staged_at": "2025-11-08T18:30:00",
      "approved_for_deletion": false
    }
  ]
}
```

### Approve Deletion
```
POST /deletions/{pending_id}/approve
```

**Response:**
```json
{
  "status": "approved",
  "message": "File will be permanently deleted"
}
```

### Restore File
```
POST /deletions/{pending_id}/restore
```

**Response:**
```json
{
  "status": "restored",
  "message": "File restored to original location"
}
```

### Cleanup Old Pending
```
POST /deletions/cleanup
```

**Response:**
```json
{
  "status": "cleaned",
  "message": "Cleaned up 3 old pending deletions"
}
```

---

## Streaming

### Stream Video
```
GET /stream/{file_id}
```

**Headers:**
- `Range` (optional): Byte range for seeking (e.g., "bytes=0-1048575")

**Response:**
```
HTTP/1.1 206 Partial Content
Content-Type: video/x-matroska
Content-Range: bytes 0-1048575/5368709120
Content-Length: 1048576
Accept-Ranges: bytes

[binary video data]
```

### Get Stream Metadata (HEAD)
```
HEAD /stream/{file_id}
```

**Response:**
```
HTTP/1.1 200 OK
Content-Type: video/x-matroska
Content-Length: 5368709120
Accept-Ranges: bytes
```

---

## Renaming

### Rename Single File
```
POST /rename/{file_id}
```

**Request:**
```json
{
  "new_filename": "Star Trek TNG - S01E01 - Encounter at Farpoint.mkv"
}
```

**Response:**
```json
{
  "status": "success",
  "old_path": "/mnt/nas/tv/tng.s01e01.mkv",
  "new_path": "/mnt/nas/tv/Star Trek TNG - S01E01 - Encounter at Farpoint.mkv",
  "old_filename": "tng.s01e01.mkv",
  "new_filename": "Star Trek TNG - S01E01 - Encounter at Farpoint.mkv"
}
```

### Batch Rename
```
POST /rename/batch
```

**Request (Pattern-based):**
```json
{
  "file_ids": [1, 2, 3],
  "pattern": "{title} - S{season}E{episode}"
}
```

**Request (Prefix/Suffix):**
```json
{
  "file_ids": [1, 2, 3],
  "prefix": "[4K] ",
  "suffix": " - BluRay"
}
```

**Request (Find/Replace):**
```json
{
  "file_ids": [1, 2, 3],
  "replace_old": "x264",
  "replace_new": "x265"
}
```

**Response:**
```json
{
  "success_count": 3,
  "total": 3,
  "results": [
    {
      "status": "success",
      "old_filename": "file1.mkv",
      "new_filename": "[4K] file1 - BluRay.mkv"
    }
  ],
  "failures": []
}
```

### Get Rename History
```
GET /rename/{file_id}/history
```

**Response:**
```json
{
  "file_id": 123,
  "history": [
    {
      "old_filename": "original.mkv",
      "new_filename": "renamed_v1.mkv",
      "renamed_at": "2025-11-08T14:30:00",
      "renamed_by_user_id": 1
    },
    {
      "old_filename": "renamed_v1.mkv",
      "new_filename": "renamed_v2.mkv",
      "renamed_at": "2025-11-08T15:45:00",
      "renamed_by_user_id": 1
    }
  ]
}
```

### Revert Rename
```
POST /rename/{file_id}/revert?history_index=-1
```

**Response:**
```json
{
  "status": "success",
  "old_filename": "renamed_v2.mkv",
  "new_filename": "renamed_v1.mkv"
}
```

---

## TMDB Integration

### Search TMDB
```
POST /rename/{file_id}/tmdb-search
```

**Request:**
```json
{
  "query": "Red Dwarf",
  "media_type": "tv",
  "year": 1988
}
```

**Response:**
```json
{
  "query": "Red Dwarf",
  "results": [
    {
      "id": 146,
      "name": "Red Dwarf",
      "first_air_date": "1988-02-15",
      "overview": "The adventures of the last human alive...",
      "poster_path": "/abc123.jpg",
      "vote_average": 8.1,
      "genre_ids": [35, 10765]
    }
  ]
}
```

### Apply TMDB Rename
```
POST /rename/{file_id}/tmdb-apply
```

**Request:**
```json
{
  "tmdb_id": 146,
  "media_type": "tv",
  "enrich_metadata": true
}
```

**Response:**
```json
{
  "status": "success",
  "old_filename": "red.dwarf.s01e01.mkv",
  "new_filename": "Red Dwarf - S01E01 - The End.mkv",
  "tmdb_data": {
    "id": 146,
    "title": "Red Dwarf",
    "overview": "The adventures of the last human alive..."
  }
}
```

### Batch TMDB Rename
```
POST /rename/batch/tmdb
```

**Request:**
```json
{
  "file_ids": [1, 2, 3, 4, 5, 6],
  "auto_search": true,
  "enrich_metadata": true
}
```

**Response:**
```json
{
  "success_count": 6,
  "total": 6,
  "results": [
    {
      "status": "success",
      "old_filename": "red.dwarf.s01e01.mkv",
      "new_filename": "Red Dwarf - S01E01 - The End.mkv"
    },
    {
      "status": "success",
      "old_filename": "red.dwarf.s01e02.mkv",
      "new_filename": "Red Dwarf - S01E02 - Future Echoes.mkv"
    }
  ],
  "failures": []
}
```

---

## Health & System

### Health Check
```
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "app": "MediaVault",
  "version": "0.1.0",
  "environment": "production"
}
```

### Root Endpoint
```
GET /
```

**Response:**
```json
{
  "app": "MediaVault",
  "version": "0.1.0",
  "message": "MediaVault API is running",
  "docs": "/docs"
}
```

### API Documentation (Swagger)
```
GET /docs
```

Interactive API documentation powered by Swagger UI.

---

## Error Responses

All endpoints return standard HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource created
- `204 No Content`: Successful request with no response body
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `409 Conflict`: Conflict (e.g., file already exists)
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limits

- **TMDB API**: 40 requests per 10 seconds (automatically enforced)
- **General API**: No rate limits (local deployment)

---

## Authentication

Currently, MediaVault does not require authentication for local deployments. For production deployments, implement JWT authentication using the existing user model.

---

## WebSocket Support

Not yet implemented. Future versions may include WebSocket support for real-time scan progress updates.
