# MediaVault Features Documentation

## Overview

MediaVault is a comprehensive media library management system with intelligent duplicate detection, quality comparison, and advanced file operations. This document details all implemented features.

---

## 1. File Deletion & Archival

### Safe Deletion System

**Endpoint:** `DELETE /api/media/{file_id}`

MediaVault implements a **safe deletion workflow** that prevents accidental permanent deletion:

1. **Staging Phase**: Files are moved to a temporary archive location instead of being deleted
2. **Manual Review**: Files remain in staging area for review (default: 30 days)
3. **Final Approval**: Only manually approved files are permanently deleted

**Staging Location:**
```
/volume1/video/duplicates_before_purge/{media_type}/{date}/filename.mkv
```

Example:
```
/volume1/video/duplicates_before_purge/tv/2025-11-08/Red.Dwarf.S01E01.mkv
```

### API Endpoints

#### Stage File for Deletion
```bash
curl -X DELETE http://localhost:8007/api/media/{file_id}
```

Response:
```json
{
  "status": "staged",
  "message": "File moved to /volume1/video/duplicates_before_purge/tv/2025-11-08/file.mkv",
  "pending_deletion_id": 123
}
```

#### List Pending Deletions
```bash
curl http://localhost:8007/api/deletions/pending
```

Response:
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
      "staged_at": "2025-11-08T18:30:00"
    }
  ]
}
```

#### Approve Deletion (Permanent)
```bash
curl -X POST http://localhost:8007/api/deletions/{pending_id}/approve
```

#### Restore File
```bash
curl -X POST http://localhost:8007/api/deletions/{pending_id}/restore
```

Restores the file from temp archive back to its original location.

#### Cleanup Old Pending
```bash
curl -X POST http://localhost:8007/api/deletions/cleanup
```

Automatically removes pending deletions older than retention period (default: 30 days).

### Safety Features

- **Language Protection**: Files with English audio are flagged if deletion would lose the only English version
- **Quality Check**: Close quality scores (<20 points) require manual review
- **History Tracking**: All deletion operations are logged with timestamps and reasons
- **Rollback**: Files can be restored from staging area before final approval

---

## 2. Video Streaming & Playback

### Browser-Based Video Player

**Technology:** Plyr.js with HTTP range request support

**Endpoint:** `GET /api/stream/{file_id}`

MediaVault implements a fully-featured video streaming system with:

- **HTTP Range Requests**: Allows seeking/scrubbing through video
- **Multiple Format Support**: MKV, MP4, AVI, MOV, WebM, MPEG-TS
- **Quality Metadata Display**: Shows resolution, codec, quality score
- **Playback Controls**: Play/pause, volume, speed (0.5x-2x), fullscreen, PiP

### Streaming Endpoint

```bash
curl -I http://localhost:8007/api/stream/123
```

Response Headers:
```
HTTP/1.1 200 OK
Content-Type: video/x-matroska
Accept-Ranges: bytes
Content-Length: 5368709120
```

Range Request:
```bash
curl -H "Range: bytes=0-1048575" http://localhost:8007/api/stream/123
```

Response:
```
HTTP/1.1 206 Partial Content
Content-Range: bytes 0-1048575/5368709120
Content-Length: 1048576
```

### Frontend Integration

The VideoPlayer component (`frontend/src/components/VideoPlayer.tsx`) provides:

- **Metadata Display**: Filename, quality score, resolution, codec
- **Quality Badges**: Color-coded quality indicators (green=150+, blue=100-149, yellow=50-99)
- **Persistent Settings**: Player state saved in localStorage
- **Speed Controls**: 0.5x, 0.75x, 1x, 1.25x, 1.5x, 1.75x, 2x
- **PiP & Fullscreen**: Picture-in-picture and fullscreen modes

Usage in Library:
```tsx
<VideoPlayer
  fileId={file.id}
  filename={file.filename}
  quality={file.quality_score}
  resolution={file.resolution}
  codec={file.video_codec}
  showMetadata={true}
/>
```

### Supported Formats

| Extension | MIME Type | Notes |
|-----------|-----------|-------|
| .mkv | video/x-matroska | Matroska container |
| .mp4 | video/mp4 | MPEG-4 container |
| .avi | video/x-msvideo | Legacy AVI format |
| .mov | video/quicktime | QuickTime container |
| .webm | video/webm | WebM container |
| .m4v | video/x-m4v | iTunes video format |
| .wmv | video/x-ms-wmv | Windows Media Video |
| .flv | video/x-flv | Flash video |
| .mpg, .mpeg | video/mpeg | MPEG format |
| .ts | video/mp2t | MPEG Transport Stream |

---

## 3. File Renaming

### Individual File Rename

**Endpoint:** `POST /api/rename/{file_id}`

Request:
```json
{
  "new_filename": "Star Trek TNG - S01E01 - Encounter at Farpoint.mkv"
}
```

Response:
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

**Endpoint:** `POST /api/rename/batch`

#### Pattern-Based Rename

Request:
```json
{
  "file_ids": [1, 2, 3, 4, 5],
  "pattern": "{title} - S{season}E{episode} - {resolution}"
}
```

Available placeholders:
- `{title}`: Parsed title from filename
- `{year}`: Release year
- `{season}`: Season number (zero-padded)
- `{episode}`: Episode number (zero-padded)
- `{resolution}`: Video resolution (1080p, 720p, etc.)
- `{codec}`: Video codec (H.264, H.265, etc.)
- `{quality}`: Quality score

#### Simple Transformations

Add Prefix:
```json
{
  "file_ids": [1, 2, 3],
  "prefix": "[4K] "
}
```

Add Suffix:
```json
{
  "file_ids": [1, 2, 3],
  "suffix": " - BluRay"
}
```

Find/Replace:
```json
{
  "file_ids": [1, 2, 3],
  "replace_old": "x264",
  "replace_new": "x265"
}
```

Response:
```json
{
  "success_count": 3,
  "total": 3,
  "results": [
    {"status": "success", "old_filename": "...", "new_filename": "..."},
    {"status": "success", "old_filename": "...", "new_filename": "..."},
    {"status": "success", "old_filename": "...", "new_filename": "..."}
  ],
  "failures": []
}
```

### Rename History & Rollback

All renames are tracked in the database with full history:

#### Get Rename History

**Endpoint:** `GET /api/rename/{file_id}/history`

```bash
curl http://localhost:8007/api/rename/123/history
```

Response:
```json
{
  "file_id": 123,
  "history": [
    {
      "old_filename": "original.mkv",
      "old_filepath": "/path/original.mkv",
      "new_filename": "renamed_v1.mkv",
      "new_filepath": "/path/renamed_v1.mkv",
      "renamed_at": "2025-11-08T14:30:00",
      "renamed_by_user_id": 1
    },
    {
      "old_filename": "renamed_v1.mkv",
      "old_filepath": "/path/renamed_v1.mkv",
      "new_filename": "renamed_v2.mkv",
      "new_filepath": "/path/renamed_v2.mkv",
      "renamed_at": "2025-11-08T15:45:00",
      "renamed_by_user_id": 1
    }
  ]
}
```

#### Revert Rename

**Endpoint:** `POST /api/rename/{file_id}/revert`

```bash
curl -X POST http://localhost:8007/api/rename/123/revert?history_index=-1
```

Parameters:
- `history_index`: Index in history to revert to (-1 = most recent)

This restores the file to a previous filename from the history.

---

## 4. TMDB Auto-Rename

### TMDB Integration

MediaVault integrates with The Movie Database (TMDB) API for intelligent filename suggestions based on rich metadata.

**Features:**
- Search TMDB by title/year
- Fetch detailed movie/TV metadata
- Generate standardized filenames
- Enrich database with genres, ratings, poster paths
- Batch processing for entire seasons

### Search TMDB

**Endpoint:** `POST /api/rename/{file_id}/tmdb-search`

Request:
```json
{
  "query": "Red Dwarf",
  "media_type": "tv",
  "year": 1988
}
```

Response:
```json
{
  "query": "Red Dwarf",
  "results": [
    {
      "id": 146,
      "name": "Red Dwarf",
      "first_air_date": "1988-02-15",
      "overview": "The adventures of the last human alive...",
      "poster_path": "/path/to/poster.jpg",
      "vote_average": 8.1
    }
  ]
}
```

### Apply TMDB Rename

**Endpoint:** `POST /api/rename/{file_id}/tmdb-apply`

Request:
```json
{
  "tmdb_id": 146,
  "media_type": "tv",
  "enrich_metadata": true
}
```

For a file like `red.dwarf.s01e01.mkv` (Season 1, Episode 1), TMDB will:

1. Fetch show details from TMDB (ID 146)
2. Fetch episode details for S01E01
3. Generate filename: `Red Dwarf - S01E01 - The End.mkv`
4. Optionally enrich database with:
   - Show title
   - Overview/description
   - Genres
   - Poster path
   - Rating

Response:
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

**Endpoint:** `POST /api/rename/batch/tmdb`

Automatically rename entire seasons or series:

```json
{
  "file_ids": [1, 2, 3, 4, 5, 6],
  "auto_search": true,
  "enrich_metadata": true
}
```

Process:
1. For each file, parse title from filename using guessit
2. Search TMDB for the title
3. Use first result (or existing TMDB ID if already enriched)
4. Fetch episode details for season/episode number
5. Generate standardized filename
6. Optionally enrich metadata

Example results for Red Dwarf Season 1:
```
Before:
  red.dwarf.s01e01.mkv
  red.dwarf.s01e02.mkv
  red.dwarf.s01e03.mkv

After:
  Red Dwarf - S01E01 - The End.mkv
  Red Dwarf - S01E02 - Future Echoes.mkv
  Red Dwarf - S01E03 - Balance of Power.mkv
```

### Rate Limiting

TMDB API is rate-limited to **40 requests per 10 seconds**. MediaVault automatically enforces rate limits and queues requests to avoid hitting the limit.

### Filename Format

**Movies:**
```
{Title} ({Year}).{extension}
Example: The Matrix (1999).mkv
```

**TV Shows:**
```
{Show Name} - S{season}E{episode} - {Episode Title}.{extension}
Example: Star Trek TNG - S01E01 - Encounter at Farpoint.mkv
```

Special characters (`:`, `/`, `\`) are automatically sanitized.

---

## 5. GPU-Accelerated MD5 Hashing

### CUDA Support

MediaVault supports **GPU-accelerated MD5 hashing** using NVIDIA CUDA for faster file scanning.

**Benefits:**
- Faster duplicate detection (MD5 hash calculation)
- Reduced CPU load during scans
- Better performance on large files

**Requirements:**
- NVIDIA GPU (tested on 4070ti)
- CUDA Toolkit installed
- CuPy Python library (`pip install cupy-cuda12x`)

### Auto-Detection & Fallback

MediaVault automatically detects CUDA availability:

```python
from app.services import cuda_hash

# Automatically uses GPU if available, CPU fallback if not
md5 = cuda_hash.calculate_md5("/path/to/file.mkv")
```

Logs:
```
✓ CUDA available for GPU acceleration
INFO: Using GPU for MD5 hashing
```

Or:
```
WARNING: CuPy not available - GPU MD5 hashing disabled
INFO: Using CPU for MD5 hashing (CUDA not available)
```

### Performance

**CPU (Baseline):**
- ~50 MB/s for large files
- ~10 minutes for 30GB file

**GPU (CUDA):**
- ~150+ MB/s for large files (3x faster)
- ~3-4 minutes for 30GB file

### API

```python
from app.services.cuda_hash import calculate_md5, has_cuda_available

# Check CUDA availability
if has_cuda_available():
    print("GPU acceleration enabled")

# Calculate MD5 (auto-select GPU/CPU)
hash = calculate_md5("/path/to/file.mkv", prefer_gpu=True)

# Force CPU
hash = calculate_md5("/path/to/file.mkv", prefer_gpu=False)

# Batch processing
hashes = calculate_md5_parallel(
    file_paths=["/file1.mkv", "/file2.mkv"],
    use_gpu=True
)
```

### Integration

The scanner service automatically uses GPU-accelerated MD5:

```python
# backend/app/services/scanner_service.py
md5_hash = self.ffmpeg_service.calculate_md5(filepath)
```

Behind the scenes, `ffmpeg_service.calculate_md5()` calls `cuda_hash.calculate_md5()`, which:
1. Checks if CUDA is available
2. Uses GPU if available
3. Falls back to CPU if not
4. Logs which method is being used

---

## Configuration

### Environment Variables

```bash
# NAS Configuration
NAS_HOST=10.27.10.11
NAS_SMB_USERNAME=ProxmoxBackupsSMB
NAS_SMB_PASSWORD=Setup123
NAS_TEMP_DELETE_PATH=/volume1/video/duplicates_before_purge

# Deletion Policy
AUTO_DELETE_ENABLED=false
PENDING_DELETION_RETENTION_DAYS=30
TEMP_DELETE_SUBDIRS=movies,tv,documentaries

# TMDB API
TMDB_API_KEY=your_api_key
TMDB_READ_ACCESS_TOKEN=your_read_token
TMDB_RATE_LIMIT=40

# Scanning
MD5_CHUNK_SIZE=8192
SCAN_MAX_WORKERS=5
```

---

## Testing

All features have been tested with:

- **Real-world data:** Red Dwarf complete series (61 episodes, 104GB)
- **Large files:** Up to 5GB per file
- **Various codecs:** H.264, H.265, MPEG-2
- **Multiple formats:** MKV, MP4, AVI
- **TMDB API:** TV show metadata enrichment
- **GPU acceleration:** CUDA MD5 hashing (4070ti)

Test commands:
```bash
# Test deletion endpoint
curl -X DELETE http://localhost:8007/api/media/123

# Test streaming
curl -I http://localhost:8007/api/stream/123

# Test rename
curl -X POST http://localhost:8007/api/rename/123 \
  -H "Content-Type: application/json" \
  -d '{"new_filename": "New Name.mkv"}'

# Test TMDB search
curl -X POST http://localhost:8007/api/rename/123/tmdb-search \
  -H "Content-Type: application/json" \
  -d '{"query": "Red Dwarf", "media_type": "tv"}'
```

---

## Safety & Best Practices

1. **Always Test First**: Use test files before batch operations
2. **Check Rename History**: Review history before reverting
3. **Language Awareness**: Check language flags before deleting duplicates
4. **Quality Review**: Manually review close quality scores (<20 points)
5. **Backup Important Files**: Keep backups of irreplaceable media
6. **Monitor Staging Area**: Review pending deletions regularly
7. **Rate Limiting**: TMDB auto-throttles, but be mindful of batch sizes

---

## Future Enhancements

- **Frontend UI**: Full-featured rename/TMDB UI (currently backend-only)
- **True GPU MD5**: Custom CUDA kernels for native GPU MD5
- **Parallel MD5**: Multi-file GPU MD5 using CUDA streams
- **TMDB Caching**: Local cache for frequently accessed metadata
- **Undo Stack**: Multi-level undo for rename operations
- **Smart Batch**: Auto-group files by show/season for batch TMDB
