# MediaVault - Media Organization & Deduplication System

**Created:** 2025-11-08
**Status:** Planning Phase
**Priority:** #medium #personal

---

## Project Overview

**Purpose:** Organize, deduplicate, and manage movie/TV show collection on Synology NAS

**Core Problem:**
- Media files scattered across `/volume1/docker` and `/volume1/videos` on NAS (10.27.10.11)
- Duplicate files with slightly different names (e.g., `RedDwarf_TVLab_s01e01.mkv` vs `RedDwarf_s01e01_Wondercrew.mp4`)
- Need to compare quality, archive duplicates, and maintain organized library

**Solution:** Full-stack web application with intelligent deduplication and side-by-side video comparison

---

## Architecture

### Stack
- **Backend:** FastAPI (Python 3.11+) on port 8007
- **Frontend:** React + TypeScript + Vite + Mantine UI on port 3007
- **Database:** PostgreSQL 16 (shared: pm-ideas-postgres:5433, database: `mediavault`)
- **Media Processing:** FFmpeg, FFprobe, MediaInfo
- **Storage:** Synology NAS (10.27.10.11) via SMB mount

### Infrastructure
```
┌─────────────────────────────────────────────────┐
│  Frontend (React)                               │
│  http://10.27.10.104:3007                       │
└──────────────────┬──────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────┐
│  Backend (FastAPI)                              │
│  http://10.27.10.104:8007                       │
│  ┌─────────────┐  ┌──────────────┐             │
│  │ Scanner     │  │ Deduplicator │             │
│  │ Service     │  │ Service      │             │
│  └─────────────┘  └──────────────┘             │
│  ┌─────────────┐  ┌──────────────┐             │
│  │ FFmpeg      │  │ NAS/SMB      │             │
│  │ Service     │  │ Service      │             │
│  └─────────────┘  └──────────────┘             │
└──────────────────┬──────────────────────────────┘
                   │
    ┌──────────────┼────────────────┐
    │              │                │
┌───▼────┐    ┌────▼─────┐    ┌────▼─────────────┐
│ Postgres│    │ NAS      │    │ FFmpeg           │
│ :5433   │    │ 10.27.   │    │ /usr/bin/ffmpeg  │
│ mediavault│  │ 10.11    │    │                  │
└─────────┘    └──────────┘    └──────────────────┘
```

---

## Database Schema (PostgreSQL)

### Connection Info
- **Host:** localhost (via pm-ideas-postgres container)
- **Port:** 5433
- **Database:** mediavault
- **User:** pm_ideas_user
- **Connection String:** `postgresql://pm_ideas_user:PASSWORD@localhost:5433/mediavault`

### Proposed Tables

#### 1. `media_files` - Core media file inventory
```sql
CREATE TABLE media_files (
    id SERIAL PRIMARY KEY,

    -- File identification
    filename VARCHAR(500) NOT NULL,
    filepath TEXT NOT NULL UNIQUE,  -- Full path on NAS
    file_size BIGINT NOT NULL,      -- Bytes
    md5_hash CHAR(32),               -- Content hash for exact duplicate detection

    -- Media metadata (from FFprobe/MediaInfo)
    duration DECIMAL(10,2),          -- Seconds
    format VARCHAR(50),              -- mp4, mkv, avi, etc.
    video_codec VARCHAR(50),         -- H.264, H.265, VP9, etc.
    audio_codec VARCHAR(50),         -- AAC, MP3, AC3, etc.
    resolution VARCHAR(20),          -- 1920x1080, 3840x2160, etc.
    width INTEGER,
    height INTEGER,
    bitrate INTEGER,                 -- kbps
    framerate DECIMAL(6,2),          -- 23.976, 29.97, 60, etc.

    -- Quality indicators
    quality_tier VARCHAR(20),        -- 4K, 1080p, 720p, 480p, SD
    hdr_type VARCHAR(20),            -- HDR10, Dolby Vision, SDR, etc.
    audio_channels DECIMAL(3,1),     -- 2.0, 5.1, 7.1, etc.
    audio_track_count INTEGER DEFAULT 1,
    subtitle_track_count INTEGER DEFAULT 0,

    -- Parsed content metadata
    media_type VARCHAR(10),          -- 'tv' or 'movie'
    show_name VARCHAR(255),          -- Parsed from filename
    season_number INTEGER,           -- For TV shows
    episode_number INTEGER,          -- For TV shows
    episode_title VARCHAR(255),      -- If parseable
    year INTEGER,                    -- Release year if in filename
    release_group VARCHAR(100),      -- WonderCrew, TVLab, etc.

    -- TMDb metadata (external API)
    tmdb_id INTEGER,                 -- TMDb show/movie ID
    tmdb_type VARCHAR(10),           -- 'tv' or 'movie'
    tmdb_title VARCHAR(255),         -- Official title from TMDb
    tmdb_year INTEGER,               -- Official year
    tmdb_overview TEXT,              -- Description
    tmdb_poster_path VARCHAR(255),   -- Poster URL path
    tmdb_rating DECIMAL(3,1),        -- User rating (0-10)
    tmdb_fetched_at TIMESTAMP,

    -- OMDb metadata (future - source of truth)
    omdb_id VARCHAR(20),             -- IMDb ID (tt1234567)
    omdb_data JSONB,                 -- Full OMDb response
    omdb_fetched BOOLEAN DEFAULT false,
    omdb_last_attempt TIMESTAMP,

    -- File status
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted, error
    is_duplicate BOOLEAN DEFAULT false,
    duplicate_group_id INTEGER,      -- FK to duplicate_groups
    quality_rank INTEGER,            -- Within duplicate group (1=best)

    -- Timestamps
    file_created_at TIMESTAMP,       -- From filesystem
    file_modified_at TIMESTAMP,      -- From filesystem
    scanned_at TIMESTAMP DEFAULT NOW(),
    last_verified_at TIMESTAMP,      -- Last time file existence verified
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    CONSTRAINT fk_duplicate_group FOREIGN KEY (duplicate_group_id)
        REFERENCES duplicate_groups(id) ON DELETE SET NULL
);

CREATE INDEX idx_media_files_filepath ON media_files(filepath);
CREATE INDEX idx_media_files_md5 ON media_files(md5_hash) WHERE md5_hash IS NOT NULL;
CREATE INDEX idx_media_files_show ON media_files(show_name, season_number, episode_number)
    WHERE media_type = 'tv';
CREATE INDEX idx_media_files_status ON media_files(status);
CREATE INDEX idx_media_files_duplicate ON media_files(is_duplicate, duplicate_group_id);
CREATE INDEX idx_media_files_tmdb ON media_files(tmdb_id, tmdb_type);
```

#### 2. `duplicate_groups` - Groups of duplicate files
```sql
CREATE TABLE duplicate_groups (
    id SERIAL PRIMARY KEY,

    -- Group identification
    group_type VARCHAR(20) NOT NULL,     -- 'exact' (md5 match), 'fuzzy' (name match), 'manual'
    confidence_score DECIMAL(5,2),        -- 0-100, fuzzy match confidence

    -- Media info (from representative file)
    show_name VARCHAR(255),
    season_number INTEGER,
    episode_number INTEGER,
    media_type VARCHAR(10),              -- 'tv' or 'movie'

    -- Group stats
    file_count INTEGER DEFAULT 0,
    total_size BIGINT,                   -- Total bytes of all duplicates
    potential_savings BIGINT,            -- Bytes saved by keeping only best quality

    -- Decision tracking
    reviewed BOOLEAN DEFAULT false,
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER,                 -- FK to users.id
    action_taken VARCHAR(20),            -- 'keep_all', 'archive_duplicates', 'delete_duplicates'
    primary_file_id INTEGER,             -- Which file was kept (FK to media_files.id)

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_primary_file FOREIGN KEY (primary_file_id)
        REFERENCES media_files(id) ON DELETE SET NULL
);

CREATE INDEX idx_duplicate_groups_reviewed ON duplicate_groups(reviewed);
CREATE INDEX idx_duplicate_groups_type ON duplicate_groups(group_type);
```

#### 3. `duplicate_members` - Many-to-many relationship
```sql
CREATE TABLE duplicate_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,

    -- Quality ranking within group
    quality_rank INTEGER,               -- 1=best quality, 2=second best, etc.
    is_primary BOOLEAN DEFAULT false,   -- The file we're keeping

    -- Comparison metrics
    quality_score DECIMAL(6,2),         -- Calculated quality score (resolution + bitrate + codec)
    size_rank INTEGER,                  -- Rank by file size (1=largest)

    -- Timestamps
    added_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_group FOREIGN KEY (group_id)
        REFERENCES duplicate_groups(id) ON DELETE CASCADE,
    CONSTRAINT fk_file FOREIGN KEY (file_id)
        REFERENCES media_files(id) ON DELETE CASCADE,
    CONSTRAINT unique_group_file UNIQUE (group_id, file_id)
);

CREATE INDEX idx_duplicate_members_group ON duplicate_members(group_id);
CREATE INDEX idx_duplicate_members_file ON duplicate_members(file_id);
```

#### 4. `scan_history` - Track scanning operations
```sql
CREATE TABLE scan_history (
    id SERIAL PRIMARY KEY,

    -- Scan configuration
    scan_type VARCHAR(20),              -- 'full', 'incremental', 'path'
    nas_paths TEXT[],                   -- Array of scanned paths

    -- Scan stats
    scan_started_at TIMESTAMP NOT NULL,
    scan_completed_at TIMESTAMP,
    duration_seconds INTEGER,

    files_found INTEGER DEFAULT 0,
    files_new INTEGER DEFAULT 0,
    files_updated INTEGER DEFAULT 0,
    files_deleted INTEGER DEFAULT 0,      -- No longer exist on NAS

    errors_count INTEGER DEFAULT 0,
    error_details JSONB,                  -- Array of error messages

    -- Status
    status VARCHAR(20) DEFAULT 'running', -- running, completed, failed, cancelled
    triggered_by VARCHAR(50),             -- 'manual', 'scheduled', 'api'
    user_id INTEGER,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_scan_history_status ON scan_history(status);
CREATE INDEX idx_scan_history_started ON scan_history(scan_started_at DESC);
```

#### 5. `user_decisions` - Track manual duplicate decisions
```sql
CREATE TABLE user_decisions (
    id SERIAL PRIMARY KEY,

    duplicate_group_id INTEGER NOT NULL,
    user_id INTEGER,

    -- Decision details
    action_taken VARCHAR(50),            -- 'archive_file', 'delete_file', 'keep_all', 'mark_not_duplicate'
    files_archived INTEGER[],            -- Array of file IDs archived
    files_deleted INTEGER[],             -- Array of file IDs deleted
    primary_file_id INTEGER,             -- File ID chosen as best quality

    -- User notes
    notes TEXT,
    confidence VARCHAR(20),              -- 'certain', 'uncertain', 'needs_review'

    -- Timestamps
    decided_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_duplicate_group_decision FOREIGN KEY (duplicate_group_id)
        REFERENCES duplicate_groups(id) ON DELETE CASCADE
);

CREATE INDEX idx_user_decisions_group ON user_decisions(duplicate_group_id);
```

#### 6. `nas_config` - NAS connection settings
```sql
CREATE TABLE nas_config (
    id SERIAL PRIMARY KEY,

    -- NAS details
    nas_name VARCHAR(100) NOT NULL,
    nas_host VARCHAR(255) NOT NULL,      -- 10.27.10.11
    nas_type VARCHAR(50) DEFAULT 'smb',  -- smb, nfs

    -- SMB credentials (encrypted in production)
    smb_username VARCHAR(100),
    smb_password_encrypted TEXT,         -- TODO: Encrypt with app secret
    smb_domain VARCHAR(100),
    smb_share VARCHAR(100),              -- volume1

    -- Mount configuration
    mount_path VARCHAR(255),             -- /mnt/nas-media
    mount_options TEXT,                  -- uid=1000,gid=1000,etc.

    -- Scan paths on NAS
    scan_paths TEXT[],                   -- ['/volume1/docker', '/volume1/videos']

    -- Connection status
    is_active BOOLEAN DEFAULT true,
    last_connected_at TIMESTAMP,
    last_connection_error TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 7. `users` - Authentication (copy from pm-ideas pattern)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,

    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,

    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    must_change_password BOOLEAN DEFAULT false,

    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

#### 8. `sessions` - JWT session tracking
```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL,
    jti VARCHAR(255) UNIQUE NOT NULL,    -- JWT ID
    token_hash VARCHAR(255) NOT NULL,

    ip_address VARCHAR(45),
    user_agent TEXT,

    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_jti ON sessions(jti);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
```

#### 9. `archive_operations` - Track file archival
```sql
CREATE TABLE archive_operations (
    id SERIAL PRIMARY KEY,

    file_id INTEGER NOT NULL,
    duplicate_group_id INTEGER,

    -- Operation details
    operation_type VARCHAR(20),          -- 'archive', 'restore', 'delete'
    source_path TEXT NOT NULL,
    destination_path TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, in_progress, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,

    -- Reversal tracking
    is_reversed BOOLEAN DEFAULT false,
    reversed_at TIMESTAMP,
    reversed_by INTEGER,                 -- FK to users.id

    -- User tracking
    triggered_by INTEGER,                -- FK to users.id

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_file_archive FOREIGN KEY (file_id)
        REFERENCES media_files(id) ON DELETE CASCADE
);

CREATE INDEX idx_archive_operations_file ON archive_operations(file_id);
CREATE INDEX idx_archive_operations_status ON archive_operations(status);
```

---

## API Credentials

### TMDb (The Movie Database)
- **API Key:** `8c6d956e5e4a94ca19adbbb782495a89`
- **Read Access Token:** `eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI4YzZkOTU2ZTVlNGE5NGNhMTlhZGJiYjc4MjQ5NWE4OSIsIm5iZiI6MTc2MjYwOTc0NS41OCwic3ViIjoiNjkwZjRhNTE0N2QxZmFiNDljMzFhYWU1Iiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.Ai1G41L66BpKLlEtYLMC_X3UmogP9QTibH4zsUl7WaM`
- **Base URL:** `https://api.themoviedb.org/3/`
- **Rate Limit:** 40 requests/10 seconds
- **Usage:** Primary metadata source for all files

### OMDb (Future - IMDb data)
- **Status:** Not registered yet
- **Plan:** Secondary "source of truth" API
- **Rate Limit:** 1,000 requests/day (free tier)
- **Strategy:** Daily batch processing for >1000 files

---

## NAS Configuration

### Synology NAS Details
- **IP Address:** 10.27.10.11
- **Access Method:** SMB/CIFS
- **Credentials:** `ProxmoxBackupsSMB` / `Setup123` (from youtube-scrapper config)
- **Scan Paths:**
  - `/volume1/docker` (recursive)
  - `/volume1/videos` (recursive)
- **Archive Path:** `/volume1/archive` (to be created)

### Mount Strategy
- **Mount Point:** `/mnt/nas-media`
- **Mount Type:** SMB/CIFS (proven working in youtube-scrapper)
- **Mount Options:** `uid=1000,gid=1000,rw,file_mode=0644,dir_mode=0755`
- **Auto-mount:** On container startup via entrypoint script

---

## Core Features - Phase 1

### 1. Media Scanner
- Recursive directory traversal of NAS paths
- Video file detection (`.mkv`, `.mp4`, `.avi`, `.m4v`, `.mov`, `.wmv`, `.flv`, `.webm`)
- FFprobe metadata extraction (codec, resolution, bitrate, duration)
- MD5 hash calculation (chunked for large files)
- TMDb metadata lookup (show name, year, poster)
- Database storage with full indexing

### 2. Duplicate Detection Engine
- **Exact Match:** MD5 hash comparison
- **Fuzzy Match:** Filename similarity with configurable threshold
  - Use `guessit` library to parse show names, seasons, episodes
  - Use `rapidfuzz` for string similarity scoring
  - Parse patterns: `S01E01`, `1x01`, `Season 1 Episode 01`
  - Handle release groups: `TVLab`, `WonderCrew`, `WEB-DL`, etc.
- **Quality Ranking:**
  - Resolution score: 4K=100, 1080p=75, 720p=50, 480p=25, SD=10
  - Codec score: H.265=20, H.264=15, others=5
  - Bitrate score: normalized to 0-20 range
  - Audio score: 5.1+=10, 2.0=5
  - Total quality score = sum of all scores
- Group duplicates by confidence level

### 3. Side-by-Side Video Player
- Dual video player component
- Stream video via backend proxy endpoint: `/api/media/stream/{file_id}`
- Synchronized play/pause/seek controls
- Metadata overlay showing:
  - Resolution, codec, bitrate, file size
  - Audio/subtitle track counts
  - Quality score ranking
- Mark file for archive/keep decision

### 4. Archive Management
- Move duplicates to `/volume1/archive/` on NAS
- Preserve directory structure: `archive/YYYY-MM-DD/{original_path}`
- Update database: `status='archived'`
- Track operation in `archive_operations` table
- Restore functionality (undo archive)

---

## User Interface Mockup

### Pages
1. **Dashboard**
   - Total files count
   - Total library size
   - Duplicate groups count
   - Potential space savings
   - Recent scan history

2. **Library Browser**
   - Filterable/sortable table of all media files
   - Group by: Show, Season, Movie
   - Filter by: Format, Resolution, Status
   - Search by filename

3. **Duplicates View**
   - List of duplicate groups
   - Confidence score badges
   - Quick actions: Compare, Archive, Keep All
   - Filter by: Confidence, Reviewed/Unreviewed

4. **Comparison Tool**
   - Side-by-side video players
   - Metadata comparison table
   - Decision buttons: Keep Left, Keep Right, Keep Both
   - Notes field for manual decisions

5. **Scanner Control**
   - Start new scan (full/incremental)
   - Scan history with status
   - Progress indicator for running scans
   - Error log viewer

6. **Settings**
   - NAS connection config
   - Scan paths management
   - Fuzzy match threshold slider
   - TMDb API key config
   - Archive path configuration

---

## Quality Scoring Algorithm

```python
def calculate_quality_score(file: MediaFile) -> float:
    """
    Calculate quality score (0-200 range)
    Higher is better quality
    """
    score = 0.0

    # Resolution score (0-100)
    resolution_map = {
        '4K': 100,      # 3840x2160
        '1080p': 75,    # 1920x1080
        '720p': 50,     # 1280x720
        '480p': 25,     # 854x480
        'SD': 10        # <480p
    }
    score += resolution_map.get(file.quality_tier, 0)

    # Codec score (0-20)
    codec_map = {
        'hevc': 20,     # H.265
        'h264': 15,     # H.264
        'vp9': 18,
        'av1': 22,
        'mpeg4': 5,
        'mpeg2': 3
    }
    score += codec_map.get(file.video_codec.lower(), 5)

    # Bitrate score (0-30)
    # Normalize bitrate to 0-30 range
    # 1080p sweet spot: 8-12 Mbps
    if file.bitrate:
        bitrate_mbps = file.bitrate / 1000
        if file.quality_tier == '1080p':
            ideal = 10000  # 10 Mbps
        elif file.quality_tier == '4K':
            ideal = 25000  # 25 Mbps
        elif file.quality_tier == '720p':
            ideal = 5000   # 5 Mbps
        else:
            ideal = 2000   # 2 Mbps

        # Score based on proximity to ideal
        ratio = min(file.bitrate / ideal, 2.0)
        score += ratio * 30

    # Audio score (0-15)
    if file.audio_channels >= 5.1:
        score += 15
    elif file.audio_channels >= 2.0:
        score += 10
    else:
        score += 5

    # Multi-audio bonus (0-10)
    if file.audio_track_count > 1:
        score += min(file.audio_track_count * 3, 10)

    # Subtitle bonus (0-10)
    if file.subtitle_track_count > 0:
        score += min(file.subtitle_track_count * 2, 10)

    # HDR bonus (0-15)
    if file.hdr_type and file.hdr_type != 'SDR':
        score += 15

    return round(score, 2)
```

---

## Fuzzy Matching Strategy

### Show Name Matching
```python
from guessit import guessit
from rapidfuzz import fuzz

def parse_filename(filename: str) -> dict:
    """Parse filename using guessit"""
    guess = guessit(filename)
    return {
        'title': guess.get('title'),
        'season': guess.get('season'),
        'episode': guess.get('episode'),
        'year': guess.get('year'),
        'release_group': guess.get('release_group'),
        'screen_size': guess.get('screen_size'),  # 720p, 1080p
        'video_codec': guess.get('video_codec'),
    }

def calculate_similarity(file1: dict, file2: dict, threshold: int) -> float:
    """
    Calculate similarity between two parsed filenames
    Returns 0-100 confidence score
    """
    # Title similarity (weighted 50%)
    title_score = fuzz.token_sort_ratio(file1['title'], file2['title'])

    # Season/Episode exact match (weighted 30%)
    se_score = 0
    if file1.get('season') == file2.get('season'):
        se_score += 50
    if file1.get('episode') == file2.get('episode'):
        se_score += 50

    # Year match (weighted 10%)
    year_score = 100 if file1.get('year') == file2.get('year') else 0

    # Resolution match (weighted 10%)
    res_score = 100 if file1.get('screen_size') == file2.get('screen_size') else 0

    # Weighted average
    confidence = (
        title_score * 0.5 +
        se_score * 0.3 +
        year_score * 0.1 +
        res_score * 0.1
    )

    return confidence if confidence >= threshold else 0
```

---

## File Hashing Strategy

```python
import hashlib

def calculate_md5(filepath: str, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash of file using chunked reading
    Efficient for large video files (10GB+)
    """
    md5 = hashlib.md5()

    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)

    return md5.hexdigest()

# For 10GB file with 8KB chunks: ~2-3 minutes on typical SSD
# For NAS over SMB: ~5-10 minutes depending on network speed
```

---

## Next Steps

### Phase 1: Setup (This Session)
- [x] Create `/home/mercury/projects/mediavault` directory
- [x] Create `mediavault` database on pm-ideas-postgres
- [ ] Write database schema migration script
- [ ] Create planning documentation (this file)
- [ ] Run initial NAS scan and save results to database

### Phase 2: Backend Skeleton (Next Session)
- [ ] FastAPI app structure
- [ ] Database models (SQLAlchemy)
- [ ] Scanner service (NAS file walker)
- [ ] FFmpeg service (metadata extraction)
- [ ] TMDb service (API integration)
- [ ] Docker Compose configuration

### Phase 3: Duplicate Detection
- [ ] MD5 hash comparison
- [ ] Fuzzy matching with guessit + rapidfuzz
- [ ] Quality ranking algorithm
- [ ] Duplicate grouping logic

### Phase 4: Frontend
- [ ] React + Mantine UI setup
- [ ] Dashboard page
- [ ] Library browser
- [ ] Duplicate comparison tool
- [ ] Side-by-side video player

### Phase 5: Archive Management
- [ ] Move files to archive folder
- [ ] Track operations in database
- [ ] Restore/undo functionality
- [ ] Batch operations

---

## Open Questions

1. **Archive retention:** How long to keep archived files before permanent deletion? (30 days, 90 days, forever?)
2. **Scan frequency:** Should we implement scheduled scans? (Daily, weekly?)
3. **Background processing:** Use Celery for long-running scans, or FastAPI async with progress webhooks?
4. **Dry-run mode:** Should all archive operations require explicit confirmation, or allow "auto-archive" for high-confidence duplicates?
5. **Notification system:** Email/webhook when scan completes or duplicates found?

---

## Resources

- **PM-Ideas Template:** `/home/mercury/projects/pm-ideas/` (reference architecture)
- **YouTube Scrapper NAS Service:** `/home/mercury/projects/youtube-scrapper/backend/services/nas_service.py`
- **TMDb API Docs:** https://developers.themoviedb.org/3/getting-started/introduction
- **Guessit Docs:** https://github.com/guessit-io/guessit
- **RapidFuzz Docs:** https://github.com/maxbachmann/RapidFuzz

---

**Next Action:** Review database schema and run initial NAS scan
