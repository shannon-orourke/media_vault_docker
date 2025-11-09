# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaVault is an intelligent media library manager with duplicate detection, quality comparison, and AI-powered chat interface. The system scans a Synology NAS for video files, detects duplicates (exact and fuzzy matching), compares quality scores, and stages lower-quality duplicates for deletion with manual approval.

**Current Status:** Planning phase - database schema created, infrastructure configured, no backend/frontend code yet.

## Technology Stack

- **Backend:** FastAPI (Python 3.11+) on port 8007
- **Frontend:** React + TypeScript + Vite + Mantine UI on port 3007
- **Database:** PostgreSQL 16 (shared container: `pm-ideas-postgres` on port 5433, database: `mediavault`)
- **Media Processing:** FFmpeg, FFprobe, MediaInfo
- **AI Chat:** Azure OpenAI GPT-4o (shared from bimodal_agent project)
- **External APIs:** TMDb API (primary metadata source)
- **Storage:** Synology NAS at 10.27.10.11 via SMB/CIFS mount

## Infrastructure

### Database Connection
```bash
# Database already exists in shared PostgreSQL container
# Connection: postgresql://pm_ideas_user:PASSWORD@localhost:5433/mediavault
# Schema migration: 001_initial_schema.sql (already executed)
# Tables: users, sessions, nas_config, media_files, duplicate_groups, duplicate_members, pending_deletions, scan_history, user_decisions, archive_operations, chat_sessions, chat_messages
```

### Port Allocation
- Backend: 8007
- Frontend: 3007
- Database: 5433 (shared pm-ideas-postgres)

### Domain & SSL
- Production: https://mediavault.orourkes.me
- Nginx config: `nginx-mediavault.conf` (uses wildcard SSL cert `*.orourkes.me`)
- Installation path: `/etc/nginx/sites-available/mediavault.orourkes.me`

### NAS Configuration
- Host: 10.27.10.11
- Credentials: ProxmoxBackupsSMB / Setup123
- Scan paths: `/volume1/docker`, `/volume1/videos`
- Archive path: `/volume1/video/duplicates_before_purge/{media_type}/{date}/`
- Mount point (in container): `/mnt/nas-media`

## Database Schema Architecture

### Core Tables
1. **media_files** - Complete media inventory with language tracking (audio_languages, subtitle_languages, dominant_audio_language)
2. **duplicate_groups** - Groups of duplicate files with confidence levels
3. **duplicate_members** - Many-to-many relationship between groups and media files
4. **pending_deletions** - Staging area before manual approval (NEVER auto-delete)
5. **user_decisions** - Manual override decisions for duplicates
6. **chat_sessions** / **chat_messages** - Azure OpenAI chat history with database context injection

See `001_initial_schema.sql` for complete schema (already executed).

## Quality Scoring Algorithm

The system ranks media files on a 0-200 scale:

- **Resolution:** 4K=100, 1080p=75, 720p=50, 480p=25, SD=10
- **Codec:** H.265=20, H.264=15, VP9=18, AV1=22
- **Bitrate:** Normalized 0-30 (based on resolution-specific ideals)
- **Audio:** 5.1+=15, 2.0=10
- **Multi-audio tracks:** +3 per track (max 10)
- **Subtitles:** +2 per track (max 10)
- **HDR:** +15 if HDR10/Dolby Vision

Quality scores determine which duplicate to keep. Differences <20 points require manual review.

## Language-Aware Deletion Policy

Critical rules for duplicate detection:
1. **Never delete the only English version** - If one duplicate has English audio and others don't, keep English version
2. **Foreign film detection** - Non-English audio + English subs = foreign film (safe to prefer higher quality non-English version)
3. **Close quality (<20 points):** Always flag for manual review
4. **3+ duplicates:** Keep #1, delete #2 and #3
5. **Manual approval only:** `AUTO_DELETE_ENABLED=false` (never change this without explicit user request)

## Duplicate Detection Strategy

### Exact Match
- MD5 hash comparison for identical files
- Stored in `media_files.md5_hash`

### Fuzzy Match
- Uses `guessit` library to parse filenames into structured metadata (title, year, season, episode, release_group, etc.)
- Uses `rapidfuzz` for similarity scoring (threshold: 85% default)
- Considers same title + year (movies) or title + season + episode (TV) as fuzzy duplicates

## Development Commands

### Database Operations
```bash
# Connect to database
psql -U pm_ideas_user -h localhost -p 5433 -d mediavault

# Run migration (already done, but for reference)
psql -U pm_ideas_user -h localhost -p 5433 -d mediavault -f 001_initial_schema.sql

# Check tables
docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -c "\dt"

# Check NAS config
docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -c "SELECT * FROM nas_config;"
```

### Nginx Setup
```bash
# Install nginx config (not done yet)
sudo cp nginx-mediavault.conf /etc/nginx/sites-available/mediavault.orourkes.me
sudo ln -s /etc/nginx/sites-available/mediavault.orourkes.me /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Environment Configuration
```bash
# Create .env from template (not done yet)
cp .env.example .env

# Get postgres password from pm-ideas project
grep POSTGRES_PASSWORD /home/mercury/projects/pm-ideas/.env

# Edit .env with real values (especially JWT_SECRET_KEY and DATABASE_URL password)
nano .env
```

## Architecture Patterns to Follow

### Backend Structure (to be created)
```
backend/
├── app/
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Environment variable loading
│   ├── database.py             # SQLAlchemy connection pool
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── media_file.py
│   │   ├── duplicate_group.py
│   │   └── chat.py
│   ├── routes/                 # API endpoints
│   │   ├── auth.py
│   │   ├── media.py
│   │   ├── duplicates.py
│   │   ├── chat.py
│   │   └── nas.py
│   ├── services/               # Business logic
│   │   ├── scanner_service.py      # NAS file walker
│   │   ├── ffmpeg_service.py       # Metadata extraction
│   │   ├── dedup_service.py        # Duplicate detection (exact + fuzzy)
│   │   ├── quality_service.py      # Quality scoring algorithm
│   │   ├── nas_service.py          # SMB mount + file operations
│   │   ├── tmdb_service.py         # TMDb API integration
│   │   └── chat_service.py         # Azure OpenAI + context injection
│   └── utils/
│       ├── hash.py                  # MD5 calculation
│       ├── guessit_parser.py        # Filename parsing
│       └── fuzzy_matcher.py         # RapidFuzz similarity
├── Dockerfile
└── requirements.txt
```

### Frontend Structure (to be created)
```
frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx           # Library stats, recent scans
│   │   ├── Library.tsx             # Browse all media files
│   │   ├── Duplicates.tsx          # Duplicate groups, manual review queue
│   │   ├── Comparison.tsx          # Side-by-side video player
│   │   ├── Chat.tsx                # AI chat interface
│   │   └── Settings.tsx            # NAS config, scan settings
│   ├── components/
│   │   ├── VideoPlayer.tsx         # Dual video player with metadata overlay
│   │   ├── QualityBadge.tsx        # Quality score display
│   │   ├── MediaCard.tsx           # Grid view for media files
│   │   └── DuplicateCard.tsx       # Duplicate group card
│   └── services/
│       ├── api.ts                  # Axios client
│       └── auth.ts                 # JWT token management
├── Dockerfile
├── package.json
└── vite.config.ts
```

### Docker Compose Pattern
Follow pm-ideas pattern (separate backend/frontend containers, no postgres service since using shared container):
```yaml
services:
  backend:
    build: ./backend
    ports: ["8007:8000"]
    environment:
      DATABASE_URL: postgresql://pm_ideas_user:${POSTGRES_PASSWORD}@10.27.10.104:5433/mediavault
    volumes:
      - ./backend/logs:/app/logs

  frontend:
    build: ./frontend
    ports: ["3007:3000"]
    depends_on: [backend]
```

## Important Development Constraints

1. **Shared Database Container:** Do NOT create a new postgres service. Use existing `pm-ideas-postgres:5433` with database name `mediavault`.

2. **Deletion Safety:** All deletions must go through `pending_deletions` table first. Files are moved to `/volume1/video/duplicates_before_purge/{media_type}/{date}/` for manual approval. NEVER implement auto-deletion.

3. **Language Awareness:** Always check `audio_languages` and `subtitle_languages` before suggesting deletion. Flag for manual review if English audio would be lost.

4. **Quality Scoring:** Implement the exact algorithm defined in README.md (0-200 scale). Do not invent new scoring criteria.

5. **Fuzzy Matching:** Use `guessit` + `rapidfuzz` as specified. Do not use alternative libraries without discussion.

6. **API Rate Limits:**
   - TMDb: 40 requests per 10 seconds
   - Implement request queuing/throttling in `tmdb_service.py`

7. **Security:** First user becomes superuser automatically. Registration disabled after first user (`ALLOW_REGISTRATION=false`).

## External Dependencies

### Python Libraries (for backend requirements.txt)
- fastapi
- uvicorn[standard]
- sqlalchemy
- psycopg2-binary (PostgreSQL driver)
- pydantic
- python-jose[cryptography] (JWT)
- passlib[bcrypt] (password hashing)
- python-multipart (file uploads)
- guessit (filename parsing)
- rapidfuzz (fuzzy matching)
- requests (TMDb API)
- openai (Azure OpenAI SDK)
- langfuse (observability)

### System Dependencies (for Dockerfile)
- ffmpeg, ffprobe (media analysis)
- mediainfo (detailed media metadata)
- cifs-utils (SMB mount)

## Documentation Files

- **README.md** - Quick start, architecture, quality scoring, chat examples
- **PLANNING.md** - Comprehensive project plan and schema details
- **INFRASTRUCTURE.md** - Database, nginx, NAS, API credentials, verification commands
- **SCHEMA_UPDATE.md** - Detailed database schema with language tracking
- **LANGFUSE_PROJECT_SETUP.md** - Langfuse/TraceForge observability setup
- **TRACEFORGE_INTEGRATION.md** - TraceForge hooks integration guide
- **001_initial_schema.sql** - Database migration script (already executed)
- **nginx-mediavault.conf** - Nginx reverse proxy configuration
- **.env.example** - Environment variable template with all required keys

## Next Development Steps

1. Create backend FastAPI skeleton (`backend/app/main.py`, config, database connection)
2. Create SQLAlchemy models matching `001_initial_schema.sql`
3. Implement `scanner_service.py` (recursive NAS file walker)
4. Implement `ffmpeg_service.py` (FFprobe metadata extraction)
5. Implement `dedup_service.py` (exact MD5 + fuzzy guessit/rapidfuzz matching)
6. Implement `quality_service.py` (quality scoring algorithm)
7. Create Docker Compose setup
8. Create frontend React skeleton with Mantine UI
9. Implement dashboard, library browser, duplicate comparison UI
10. Implement side-by-side video player with quality comparison
11. Implement Azure OpenAI chat with database context injection
