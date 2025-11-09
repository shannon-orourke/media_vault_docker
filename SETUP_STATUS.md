# MediaVault - Setup Status

**Date:** 2025-11-08
**Status:** Infrastructure Ready ✅

---

## Completed Tasks ✅

### 1. Project Structure
- [x] Created `/home/mercury/projects/mediavault/` directory
- [x] Created `PLANNING.md` (comprehensive project plan)
- [x] Created `SCHEMA_UPDATE.md` (database schema details)
- [x] Created `README.md` (project documentation)
- [x] Created `.env.example` (environment template)

### 2. Database Setup
- [x] Created `mediavault` database on pm-ideas-postgres (port 5433)
- [x] Ran migration script `001_initial_schema.sql`
- [x] **12 tables created:**
  1. users
  2. sessions
  3. nas_config (with default Synology NAS config)
  4. duplicate_groups
  5. media_files (with language tracking)
  6. duplicate_members
  7. **pending_deletions** (temp staging area)
  8. scan_history
  9. user_decisions
  10. archive_operations
  11. **chat_sessions** (Azure OpenAI)
  12. **chat_messages** (Chat with your data)

### 3. Nginx Configuration
- [x] Created `nginx-mediavault.conf`
- [x] Configured for `mediavault.orourkes.me`
- [x] Backend proxy: http://localhost:8007
- [x] Frontend proxy: http://localhost:3007
- [x] Video streaming support (range requests)
- [x] WebSocket support (real-time updates)
- [x] SSL/TLS ready (Let's Encrypt paths)

### 4. Domain & DNS
- [x] Cloudflare DNS: mediavault.orourkes.me → 10.27.10.104
- [x] DNS only mode (reserved IP)
- [ ] **TODO:** Install nginx config and get SSL certificate

### 5. API Configuration
- [x] **TMDb API:**
  - API Key: `8c6d956e5e4a94ca19adbbb782495a89`
  - Read Token: Configured
- [x] **Azure OpenAI:**
  - Key: `9abCh0KH4swF6vplFQ5GYIOQ6XqYTht6PZQ7xCVK4KtKG0m31UyxJQQJ99BJACYeBjFXJ3w3AAABACOGmjSQ`
  - Endpoint: `https://eastus.api.cognitive.microsoft.com/`
  - Model: `gpt-4o` (chat), `gpt-4o-mini` (cheaper queries)

---

## Configuration Summary

### Database
```
Host: localhost
Port: 5433
Database: mediavault
User: pm_ideas_user
Connection: postgresql://pm_ideas_user:PASSWORD@localhost:5433/mediavault
```

### Domain
```
Production: https://mediavault.orourkes.me
Local Backend: http://localhost:8007
Local Frontend: http://localhost:3007
```

### NAS
```
Host: 10.27.10.11
Username: ProxmoxBackupsSMB
Password: Setup123
Scan Paths:
  - /volume1/docker
  - /volume1/videos
Archive Path: /volume1/video/duplicates_before_purge/
```

### Ports
```
Backend: 8007
Frontend: 3007
Database: 5433
HTTPS: 443 (nginx)
```

---

## Next Steps

### Immediate (Today)
1. **Install Nginx Config:**
   ```bash
   sudo cp nginx-mediavault.conf /etc/nginx/sites-available/mediavault
   sudo ln -s /etc/nginx/sites-available/mediavault /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

2. **Get SSL Certificate:**
   ```bash
   sudo certbot --nginx -d mediavault.orourkes.me
   ```

3. **Create .env file:**
   ```bash
   cp .env.example .env
   nano .env  # Add database password
   ```

4. **Run Initial NAS Scan:**
   - Scan `/volume1/docker` and `/volume1/videos`
   - Extract metadata with FFprobe
   - Populate `media_files` table
   - Look up TMDb metadata

### Phase 2 (Next Session)
1. **Backend Development:**
   - FastAPI app structure
   - SQLAlchemy models
   - Scanner service
   - FFmpeg integration
   - TMDb service
   - Docker Compose setup

2. **Frontend Skeleton:**
   - React + TypeScript + Vite
   - Mantine UI setup
   - Basic routing

### Phase 3 (Week 2)
1. **Duplicate Detection:**
   - MD5 hash comparison
   - Fuzzy matching (guessit + rapidfuzz)
   - Quality scoring
   - Language detection

2. **UI Development:**
   - Dashboard
   - Library browser
   - Duplicate comparison view

### Phase 4 (Week 3)
1. **Video Player:**
   - Side-by-side comparison
   - Metadata overlay
   - Archive/keep decisions

2. **Archive Management:**
   - Move to temp directory
   - Track in `pending_deletions`
   - Restore functionality

### Phase 5 (Week 4)
1. **Chat Interface:**
   - Azure OpenAI integration
   - Context injection
   - Natural language queries
   - Explanation of duplicate decisions

---

## Key Features Confirmed

### 1. Language-Aware Deletion ✅
- **Rule:** Never delete only English version
- **Rule:** Keep English audio > higher quality non-English (unless foreign film)
- **Heuristic:** Non-English audio + English subs = foreign film (trust it)

### 2. Temp Staging Area ✅
```
/volume1/video/duplicates_before_purge/
├── movies/2025-11-08/...
├── tv/2025-11-08/...
└── documentaries/2025-11-08/...
```

### 3. Manual Approval Only ✅
- **No auto-deletion** (`AUTO_DELETE_ENABLED=false`)
- All deletions require explicit user approval
- Detailed reasoning for every deletion

### 4. Chat with Your Data ✅
- Azure OpenAI GPT-4o integration
- Context-aware responses
- Natural language queries
- Database injection for accurate answers

---

## Deletion Reasoning Examples

### Stored in `pending_deletions.deletion_reason`:

```
"Kept 4K version (3840x2160, H.265, 25 Mbps, HDR10).
Deleted 1080p version (1920x1080, H.264, 8 Mbps, SDR).
Quality difference: +89.0 points.
Confidence: CERTAIN."
```

```
"Same show S01E01 detected (fuzzy match 95% confidence).
Kept 'RedDwarf_s01e01_Wondercrew.mkv' (720p H.264, English audio).
Deleted 'RedDwwarf_TVLab_s01e01.avi' (480p MPEG4, English audio).
Quality difference: +45.2 points.
Confidence: CERTAIN."
```

```
"REQUIRES MANUAL REVIEW: Two versions of The Departed (2006).
Higher quality version (1080p, +35 points) lacks English audio.
Lower quality version (720p) has English audio.
Not detected as foreign film (no English subtitles on higher quality).
Confidence: UNCERTAIN."
```

---

## Quality Scoring Algorithm (0-200 scale)

### Components:
- **Resolution:** 4K=100, 1080p=75, 720p=50, 480p=25, SD=10
- **Codec:** H.265=20, H.264=15, VP9=18, AV1=22, others=5
- **Bitrate:** Normalized 0-30 (ideal varies by resolution)
- **Audio Quality:** 5.1+=15, 2.0=10, mono=5
- **Multi-audio:** +3 per additional track (max 10)
- **Subtitles:** +2 per track (max 10)
- **HDR:** +15 if HDR10/Dolby Vision

### Auto-Approval Thresholds:
- **>50 points difference:** Auto-approve deletion (certain)
- **<20 points difference:** Require manual review (uncertain)
- **20-50 points:** Auto-approve if language matches, otherwise review

---

## Security Features

1. **JWT Authentication:**
   - 24-hour access tokens
   - Session tracking with revocation
   - First user becomes superuser

2. **HTTPS Only:**
   - Let's Encrypt SSL certificate
   - Automatic HTTP→HTTPS redirect
   - HSTS headers

3. **Rate Limiting:**
   - Login attempts (slowapi)
   - API endpoints
   - Scan operations

4. **Password Security:**
   - Bcrypt hashing
   - Minimum 8 characters
   - Change password on first login

---

## File Structure

```
/home/mercury/projects/mediavault/
├── README.md                     # Project overview
├── PLANNING.md                   # Comprehensive plan
├── SCHEMA_UPDATE.md              # Database schema details
├── SETUP_STATUS.md               # This file
├── 001_initial_schema.sql        # Database migration
├── nginx-mediavault.conf         # Nginx reverse proxy
├── .env.example                  # Environment template
├── .env                          # Actual config (create this)
│
├── backend/                      # FastAPI app (to be created)
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   └── utils/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                     # React app (to be created)
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml            # Orchestration (to be created)
├── scripts/                      # Utility scripts (to be created)
│   └── nas_scan.py
└── data/                         # Logs, temp files (to be created)
```

---

## Database Statistics (Current)

```sql
-- Run this to check tables:
\dt

-- Check NAS config:
SELECT * FROM nas_config;

-- Verify no media files yet:
SELECT COUNT(*) FROM media_files;
```

**Result:**
- 12 tables created ✅
- 1 NAS config row inserted ✅
- 0 media files (waiting for initial scan)

---

## Commands Reference

### Database
```bash
# Connect to database
docker exec -it pm-ideas-postgres psql -U pm_ideas_user -d mediavault

# List tables
\dt

# Check schema
\d media_files

# Exit
\q
```

### Nginx
```bash
# Install config
sudo cp nginx-mediavault.conf /etc/nginx/sites-available/mediavault
sudo ln -s /etc/nginx/sites-available/mediavault /etc/nginx/sites-enabled/

# Test
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx

# View logs
sudo tail -f /var/log/nginx/mediavault-access.log
sudo tail -f /var/log/nginx/mediavault-error.log
```

### SSL Certificate
```bash
# Get certificate
sudo certbot --nginx -d mediavault.orourkes.me

# Renew (automatic, but manual command)
sudo certbot renew

# Check expiry
sudo certbot certificates
```

### Docker
```bash
# Check postgres container
docker ps | grep postgres

# View logs
docker logs pm-ideas-postgres

# Execute SQL
docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -c "SELECT COUNT(*) FROM media_files;"
```

---

## Open Questions (For Next Session)

1. **Backend Framework Version:**
   - FastAPI version? (recommend 0.109.0 from pm-ideas)
   - Python version? (3.11+ required)

2. **Frontend Library Versions:**
   - React 18?
   - Mantine v7 (like youtube-scrapper)?

3. **Docker Strategy:**
   - Separate containers for backend/frontend?
   - Or single container with both?

4. **Scan Implementation:**
   - Synchronous (FastAPI async) or background (Celery)?
   - Progress updates via WebSocket or polling?

5. **Video Streaming:**
   - Direct file serve or proxy through backend?
   - Transcoding needed or serve original?

---

## Success Criteria

### Infrastructure Phase ✅
- [x] Database created and migrated
- [x] Domain configured (DNS)
- [x] Nginx config ready
- [x] API credentials documented
- [ ] SSL certificate installed
- [ ] Initial NAS scan completed

### Ready for Development When:
- [ ] .env file created with real passwords
- [ ] Nginx installed and SSL configured
- [ ] Initial NAS scan populates database with real files
- [ ] Backend skeleton created (FastAPI structure)
- [ ] Frontend skeleton created (React + Vite)
- [ ] Docker Compose orchestration

---

**Status:** Infrastructure complete, ready for nginx setup and initial scan!
**Next Action:** Install nginx config, get SSL cert, run NAS scan
