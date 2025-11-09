# MediaVault

**Media Organization & Deduplication System**

Intelligent media library manager with duplicate detection, quality comparison, and AI-powered chat interface.

---

## Quick Start

### 1. Database Setup

```bash
# Database already created: mediavault on pm-ideas-postgres:5433
# Run migration
psql -U pm_ideas_user -h localhost -p 5433 -d mediavault -f 001_initial_schema.sql
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your specific values
nano .env
```

### 3. Nginx Setup

```bash
# Copy nginx config
sudo cp nginx-mediavault.conf /etc/nginx/sites-available/mediavault

# Enable site
sudo ln -s /etc/nginx/sites-available/mediavault /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 4. SSL Certificate (Let's Encrypt)

```bash
# Install certbot if not already installed
sudo apt install certbot python3-certbot-nginx

# Get certificate for mediavault.orourkes.me
sudo certbot --nginx -d mediavault.orourkes.me

# Certbot will automatically update nginx config
```

---

## Architecture

### Stack
- **Backend:** FastAPI (Python 3.11+) on port 8007
- **Frontend:** React + TypeScript + Vite + Mantine UI on port 3007
- **Database:** PostgreSQL 16 (shared: pm-ideas-postgres:5433)
- **Reverse Proxy:** Nginx (https://mediavault.orourkes.me)
- **Media Processing:** FFmpeg, FFprobe, MediaInfo
- **AI:** Azure OpenAI GPT-4o (Chat with your data)
- **Metadata:** TMDb API (primary), OMDb API (future)

### Ports
- **Backend:** 8007
- **Frontend:** 3007
- **Database:** 5433 (pm-ideas-postgres)
- **HTTPS:** 443 (nginx)

---

## Features

### Core Functionality
1. **Media Scanning**
   - Recursive NAS scanning (`/volume1/docker`, `/volume1/videos`)
   - FFprobe metadata extraction
   - MD5 hash calculation
   - TMDb metadata lookup

2. **Intelligent Duplicate Detection**
   - Exact match (MD5 hash)
   - Fuzzy match (filename similarity with `guessit` + `rapidfuzz`)
   - Configurable confidence threshold
   - Quality scoring algorithm

3. **Language-Aware Decisions**
   - Audio/subtitle language detection
   - Never delete only English version
   - Foreign film detection (non-English audio + English subs)
   - Manual review flagging for uncertain decisions

4. **Side-by-Side Video Player**
   - Dual video playback
   - Metadata comparison
   - Quality score display
   - Mark for archive/keep

5. **Staging Before Deletion**
   - Move to `/volume1/video/duplicates_before_purge/{media_type}/{date}/`
   - **Manual approval only** (no auto-deletion)
   - Detailed deletion reasoning
   - Restore functionality

6. **Chat with Your Data** (Azure OpenAI GPT-4o)
   - Natural language queries: "How many 4K movies do I have?"
   - Context-aware responses with database injection
   - Duplicate decision explanations
   - Storage insights and recommendations

---

## Database Schema

### Core Tables
1. **users** - Authentication (JWT)
2. **sessions** - Session tracking
3. **media_files** - Complete media inventory (with language tracking)
4. **duplicate_groups** - Groups of duplicate files
5. **duplicate_members** - Many-to-many relationship
6. **pending_deletions** - Staging area before permanent deletion
7. **scan_history** - Track scanning operations
8. **user_decisions** - Manual duplicate decisions
9. **archive_operations** - File move tracking
10. **nas_config** - NAS connection settings
11. **chat_sessions** - AI chat sessions
12. **chat_messages** - Chat history with context

See `PLANNING.md` and `SCHEMA_UPDATE.md` for detailed schema documentation.

---

## Configuration

### Domain
- **Production:** https://mediavault.orourkes.me
- **Local Backend:** http://localhost:8007
- **Local Frontend:** http://localhost:3007

### NAS
- **Host:** 10.27.10.11
- **Scan Paths:**
  - `/volume1/docker`
  - `/volume1/videos`
- **Archive Path:** `/volume1/video/duplicates_before_purge/`

### API Keys
- **TMDb:** Configured in `.env`
- **Azure OpenAI:** Shared from bimodal_agent project

---

## Deletion Policy

### Rules
1. **Exact duplicates (MD5):** Keep higher quality
2. **Fuzzy duplicates:** Quality score comparison
3. **Language priority:** English audio > higher quality non-English (unless foreign film)
4. **3+ duplicates:** Keep #1, delete #2 and #3
5. **Close quality (<20 points):** Requires manual review

### Temp Directory Structure
```
/volume1/video/duplicates_before_purge/
├── movies/
│   └── 2025-11-08/
│       └── Inception.2010.1080p.mkv
├── tv/
│   └── 2025-11-08/
│       └── RedDwarf_s01e01_TVLab.avi
└── documentaries/
    └── 2025-11-08/
        └── ...
```

### Manual Approval Only
- **No auto-deletion** (`AUTO_DELETE_ENABLED=false`)
- All deletions require user review and explicit approval
- Files remain in temp directory until manually confirmed

---

## Quality Scoring

### Algorithm (0-200 scale)
- **Resolution:** 4K=100, 1080p=75, 720p=50, 480p=25, SD=10
- **Codec:** H.265=20, H.264=15, VP9=18, AV1=22
- **Bitrate:** Normalized to 0-30 (based on resolution ideal)
- **Audio:** 5.1+=15, 2.0=10
- **Multi-audio tracks:** +3 per track (max 10)
- **Subtitles:** +2 per track (max 10)
- **HDR:** +15 if HDR10/Dolby Vision

### Example
```
Inception.2010.2160p.mkv:
  Resolution: 100 (4K)
  Codec: 20 (H.265)
  Bitrate: 28 (25 Mbps, ideal for 4K)
  Audio: 15 (5.1 surround)
  Multi-audio: 6 (2 tracks)
  HDR: 15 (HDR10)
  = 184 total quality score
```

---

## Chat Examples

### Example 1: Library Stats
**User:** "How many 4K movies do I have?"

**MediaVault:** "You have 127 4K movies in your library, totaling 3.2 TB of storage."

### Example 2: Duplicate Explanation
**User:** "Why did you suggest deleting Inception (2010)?"

**MediaVault:** "I found two versions of Inception (2010):
- **Kept:** 4K (3840x2160), H.265, 25 Mbps, HDR10 - Quality score: 184
- **Deleted:** 1080p (1920x1080), H.264, 8 Mbps, SDR - Quality score: 95

The 4K version has significantly higher quality (+89 points) with HDR support. The 1080p version was moved to `/volume1/video/duplicates_before_purge/movies/2025-11-08/` for your review."

### Example 3: Manual Review
**User:** "What duplicates should I review manually?"

**MediaVault:** "You have 3 duplicates flagged for manual review:

1. **Red Dwarf S01E01** - Two versions with similar quality (720p H.264 vs 720p H.265, only 12 points difference)
2. **The Departed (2006)** - Higher quality version lacks English audio (needs language verification)
3. **Breaking Bad S03E07** - Three versions with quality scores within 8 points of each other"

---

## Development Roadmap

### Phase 1: Infrastructure (Current)
- [x] Database schema
- [x] Nginx configuration
- [x] Domain setup (mediavault.orourkes.me)
- [ ] Initial NAS scan

### Phase 2: Backend Skeleton
- [ ] FastAPI app structure
- [ ] SQLAlchemy models
- [ ] Scanner service
- [ ] FFmpeg service
- [ ] TMDb service
- [ ] Docker Compose

### Phase 3: Duplicate Detection
- [ ] MD5 hash comparison
- [ ] Fuzzy matching (guessit + rapidfuzz)
- [ ] Quality ranking
- [ ] Language detection

### Phase 4: Frontend
- [ ] React + Mantine setup
- [ ] Dashboard
- [ ] Library browser
- [ ] Duplicate comparison
- [ ] Video player

### Phase 5: Chat Interface
- [ ] Azure OpenAI integration
- [ ] Context injection
- [ ] Chat UI
- [ ] Query parsing

---

## Documentation

- **PLANNING.md** - Comprehensive project plan
- **SCHEMA_UPDATE.md** - Database schema with language tracking
- **001_initial_schema.sql** - Database migration script
- **nginx-mediavault.conf** - Nginx reverse proxy config
- **.env.example** - Environment template

---

## Security

- JWT authentication (24-hour tokens)
- First user becomes superuser automatically
- Registration disabled after first user
- Rate limiting (slowapi)
- HTTPS only (Let's Encrypt SSL)
- Secure password hashing (bcrypt)

---

## Resources

- **TMDb API:** https://www.themoviedb.org/settings/api
- **Guessit:** https://github.com/guessit-io/guessit
- **RapidFuzz:** https://github.com/maxbachmann/RapidFuzz
- **MediaInfo:** https://mediaarea.net/en/MediaInfo
- **FFmpeg:** https://ffmpeg.org/

---

**Created:** 2025-11-08
**Status:** Planning Phase
**Domain:** https://mediavault.orourkes.me
