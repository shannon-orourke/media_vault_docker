# MediaVault - Infrastructure Documentation

**Created:** 2025-11-08
**Last Updated:** 2025-11-08

---

## Database Configuration

### PostgreSQL Container
**Container:** `pm-ideas-postgres`
**Image:** `pgvector/pgvector:pg16`
**External Port:** `5433` (mapped to internal 5432)
**Network:** `pm-ideas-network`

**Why This Choice:**
- Reusing existing `pm-ideas-postgres` container (already running, healthy)
- Has pgvector extension (useful for future AI/embedding features)
- PostgreSQL 16 (latest stable)
- Already configured with SSL, proper connection pooling
- External port 5433 avoids conflicts with other postgres instances

**Connection Details:**
```
Host: localhost (or 10.27.10.104)
Port: 5433
Database: mediavault
User: pm_ideas_user
Password: ${POSTGRES_PASSWORD} (from pm-ideas .env)
Connection String: postgresql://pm_ideas_user:PASSWORD@localhost:5433/mediavault
```

### Database Created
```sql
-- Created on 2025-11-08
CREATE DATABASE mediavault OWNER pm_ideas_user;
```

**Verification:**
```bash
docker exec pm-ideas-postgres psql -U pm_ideas_user -d postgres -c "\l" | grep mediavault
# Output: mediavault | pm_ideas_user | UTF8 ...
```

### Tables Created
**Migration:** `001_initial_schema.sql` ✅ Executed successfully

**12 Tables:**
1. `users` - Authentication
2. `sessions` - JWT session tracking
3. `nas_config` - NAS connection settings (1 row pre-populated)
4. `duplicate_groups` - Duplicate file groups
5. `media_files` - Core media inventory (with language tracking)
6. `duplicate_members` - Many-to-many relationship
7. `pending_deletions` - Temp staging before deletion ⭐ NEW
8. `scan_history` - Scan operation tracking
9. `user_decisions` - Manual duplicate decisions
10. `archive_operations` - File move tracking
11. `chat_sessions` - Azure OpenAI chat ⭐ NEW
12. `chat_messages` - Chat history with context ⭐ NEW

**Indexes Created:** 40+ indexes for performance

### Postgres Container Details (from pm-ideas)
**Started:** ~7 days ago
**Health:** Healthy
**Volume:** `/home/mercury/docker-volumes/pm-ideas/postgres`
**Max Connections:** 200
**Shared Buffers:** 256MB
**Effective Cache:** 1GB

**SSL Enabled:** Yes
- Cert: `/var/lib/postgresql/certs/server.crt`
- Key: `/var/lib/postgresql/certs/server.key`

**Other Databases on Same Server:**
- `pm_ideas` (main pm-ideas database)
- `postgres` (default)
- `template0`, `template1`
- **`mediavault`** ⭐ NEW

---

## Nginx Configuration

### Existing Nginx Setup
**Config Directory:** `/etc/nginx/sites-available/`
**Enabled Sites:** `/etc/nginx/sites-enabled/`

**Existing orourkes.me Sites:**
- `langfuse.orourkes.me` → http://10.27.10.104:3010
- `pdfrefinery.orourkes.me` → (port TBD)
- `planforge.orourkes.me` → (port TBD)
- `portainer.orourkes.me` → NAS Portainer
- `shotbot.orourkes.me` → (port TBD)
- `sonarr.orourkes.me` → (port TBD)
- `thesisanalyzer.orourkes.me` → (ports 8000/3000)

### SSL Certificate Pattern
**ALL orourkes.me sites use:**
```
ssl_certificate /etc/nginx/ssl/orourkes.me-wildcard.crt;
ssl_certificate_key /etc/nginx/ssl/orourkes.me-wildcard.key;
```

**Wildcard Certificate:** `*.orourkes.me`
- No need for individual Let's Encrypt certs per subdomain
- Managed centrally

### MediaVault Nginx Config
**File:** `/home/mercury/projects/mediavault/nginx-mediavault.conf`
**Pattern:** Matches `langfuse.orourkes.me` (same SSL, same headers)

**Proxies:**
- `/` → Frontend (http://10.27.10.104:3007)
- `/api/` → Backend API (http://10.27.10.104:8007)
- `/api/media/stream/` → Video streaming (range requests)
- `/ws/` → WebSocket (real-time updates)
- `/health` → Health check (no logging)

**Installation:**
```bash
sudo cp /home/mercury/projects/mediavault/nginx-mediavault.conf /etc/nginx/sites-available/mediavault.orourkes.me
sudo ln -s /etc/nginx/sites-available/mediavault.orourkes.me /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**DNS:**
- Cloudflare DNS: `mediavault.orourkes.me` A record → `10.27.10.104`
- DNS only mode (reserved IP)

---

## Port Allocation

### MediaVault Ports
- **Backend:** 8007
- **Frontend:** 3007
- **Database:** 5433 (shared pm-ideas-postgres)

### Existing Port Registry
**In Use:**
- **8000/3000:** thesisanalyzermvp
- **8001/3001:** pdf-refinery
- **8005/3005:** shopbot-agent
- **8006/3006:** pm-ideas
- **3010:** bimodal_agent (LangFuse web UI)
- **3030:** bimodal_agent (LangFuse worker)

**Database Ports:**
- **5432:** server-postgres-1 (internal only, LangFuse)
- **5433:** pm-ideas-postgres (external, shared with mediavault) ✅

**Next Available (after MediaVault):**
- Backend: 8008
- Frontend: 3008

---

## NAS Configuration

### Synology NAS
**IP:** `10.27.10.11`
**Access Method:** SMB/CIFS
**Credentials:**
- Username: `ProxmoxBackupsSMB`
- Password: `Setup123`
- Share: `volume1`

**Scan Paths:**
- `/volume1/docker` (recursive)
- `/volume1/videos` (recursive)

**Archive Path (Temp Staging):**
- `/volume1/video/duplicates_before_purge/`
- Subdirectories:
  - `movies/` → YYYY-MM-DD folders
  - `tv/` → YYYY-MM-DD folders
  - `documentaries/` → YYYY-MM-DD folders

**Pre-populated in Database:**
```sql
SELECT * FROM nas_config;
-- id=1, nas_name='Synology NAS', nas_host='10.27.10.11'
```

### Mount Strategy (When Backend Runs)
**Mount Point:** `/mnt/nas-media` (inside backend container)
**Mount Type:** SMB/CIFS
**Mount Options:** `uid=1000,gid=1000,rw,file_mode=0644,dir_mode=0755`

**Pattern:** Based on `youtube-scrapper/backend/services/nas_service.py`

---

## API Credentials

### TMDb (The Movie Database)
**Purpose:** Primary metadata source for all files

```
API Key: 8c6d956e5e4a94ca19adbbb782495a89
Read Access Token: eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI4YzZkOTU2ZTVlNGE5NGNhMTlhZGJiYjc4MjQ5NWE4OSIsIm5iZiI6MTc2MjYwOTc0NS41OCwic3ViIjoiNjkwZjRhNTE0N2QxZmFiNDljMzFhYWU1Iiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.Ai1G41L66BpKLlEtYLMC_X3UmogP9QTibH4zsUl7WaM
Base URL: https://api.themoviedb.org/3/
Rate Limit: 40 requests per 10 seconds
```

**Stored in:** `.env` file (not committed to git)

### Azure OpenAI (Chat with Your Data)
**Purpose:** GPT-4o chat interface with database context

```
Key: 9abCh0KH4swF6vplFQ5GYIOQ6XqYTht6PZQ7xCVK4KtKG0m31UyxJQQJ99BJACYeBjFXJ3w3AAABACOGmjSQ
Endpoint: https://eastus.api.cognitive.microsoft.com/
API Version: 2024-08-01-preview
Chat Model: gpt-4o
Chat Mini Model: gpt-4o-mini (cheaper)
```

**Shared From:** `/home/mercury/projects/bimodal_agent/.env`
**Stored in:** MediaVault `.env` file

### OMDb (Future - IMDb Data)
**Status:** Not registered yet
**Plan:** Secondary "source of truth" API
**Rate Limit:** 1,000 requests/day (free tier)
**Strategy:** Daily batch processing

---

## Docker Strategy

### Option 1: Separate Containers (Recommended)
**Pattern:** Same as pm-ideas

```yaml
services:
  backend:
    build: ./backend
    ports: ["8007:8000"]
    depends_on: [postgres]

  frontend:
    build: ./frontend
    ports: ["3007:3000"]
    depends_on: [backend]

  # No postgres service - use existing pm-ideas-postgres
```

**Network:** `mediavault-network` (bridge)

**Volumes:**
- Backend logs: `./backend/logs:/app/logs`
- NAS mount: `/mnt/nas-media` (SMB mount on startup)

### Database Connection from Docker
**Inside Container:**
```
DATABASE_URL=postgresql://pm_ideas_user:PASSWORD@10.27.10.104:5433/mediavault
```

**Why 10.27.10.104 not localhost:**
- Container network isolation
- Host network mode not used
- Bridge network requires host IP

---

## File Structure

```
/home/mercury/projects/mediavault/
├── README.md                       ✅ Created
├── PLANNING.md                     ✅ Created
├── SCHEMA_UPDATE.md                ✅ Created
├── SETUP_STATUS.md                 ✅ Created
├── INFRASTRUCTURE.md               ✅ This file
├── 001_initial_schema.sql          ✅ Created, executed
├── nginx-mediavault.conf           ✅ Created (updated for wildcard SSL)
├── .env.example                    ✅ Created
├── .env                            ⏳ To be created (copy from .env.example)
│
├── backend/                        ⏳ Next phase
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   └── utils/
│   └── logs/
│
├── frontend/                       ⏳ Next phase
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/
│   └── public/
│
├── docker-compose.yml              ⏳ Next phase
├── scripts/                        ⏳ Next phase
│   └── nas_scan.py
└── data/                           ⏳ Runtime
    └── logs/
```

---

## System Integration

### Integrated with PM-Ideas Infrastructure
**Shares:**
- PostgreSQL container (pm-ideas-postgres)
- Nginx setup (wildcard SSL cert)
- Docker network pattern
- Port allocation scheme

**Independent:**
- Dedicated database (`mediavault`)
- Dedicated ports (8007/3007)
- Own docker-compose file
- Own backend/frontend containers

### File System Paths
**Project:** `/home/mercury/projects/mediavault/`
**Nginx Config:** `/etc/nginx/sites-available/mediavault.orourkes.me`
**Database Volume:** `/home/mercury/docker-volumes/pm-ideas/postgres` (shared)
**Logs:** `/var/log/nginx/mediavault.*.log`

---

## Security Configuration

### SSL/TLS
**Certificate:** Wildcard `*.orourkes.me` (shared)
**Protocols:** TLSv1.2, TLSv1.3
**OCSP Stapling:** Enabled
**HSTS:** 2 years (`max-age=63072000`)

### Headers
- `Strict-Transport-Security`
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`

### Authentication
**Method:** JWT (same pattern as pm-ideas)
- Algorithm: HS256
- Token lifetime: 24 hours
- Session tracking in database
- First user becomes superuser

---

## Environment Variables

### Required in .env
```bash
# Database (shared pm-ideas postgres)
DATABASE_URL=postgresql://pm_ideas_user:PASSWORD@10.27.10.104:5433/mediavault
POSTGRES_PASSWORD=<get from pm-ideas .env>

# JWT
JWT_SECRET_KEY=<generate random key>

# NAS
NAS_SMB_PASSWORD=Setup123

# TMDb
TMDB_API_KEY=8c6d956e5e4a94ca19adbbb782495a89
TMDB_READ_ACCESS_TOKEN=eyJhbGci...

# Azure OpenAI
AZURE_OPENAI_KEY=9abCh0KH4sw...
AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
```

---

## Verification Commands

### Database
```bash
# Check database exists
docker exec pm-ideas-postgres psql -U pm_ideas_user -d postgres -c "\l" | grep mediavault

# Check tables
docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -c "\dt"

# Check NAS config
docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -c "SELECT * FROM nas_config;"

# Check row counts
docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -c "
SELECT
  'media_files' as table_name, COUNT(*) as rows FROM media_files
UNION ALL
SELECT 'duplicate_groups', COUNT(*) FROM duplicate_groups
UNION ALL
SELECT 'pending_deletions', COUNT(*) FROM pending_deletions
UNION ALL
SELECT 'chat_sessions', COUNT(*) FROM chat_sessions;
"
```

### Nginx
```bash
# Check config syntax
sudo nginx -t

# Check enabled sites
ls -la /etc/nginx/sites-enabled/

# Check mediavault config
cat /etc/nginx/sites-available/mediavault.orourkes.me

# View logs
sudo tail -f /var/log/nginx/mediavault.access.log
```

### Docker
```bash
# Check postgres container
docker ps | grep postgres

# Check postgres logs
docker logs pm-ideas-postgres --tail 50

# Check postgres health
docker inspect pm-ideas-postgres | grep -A5 Health
```

### DNS
```bash
# Check DNS resolution
dig mediavault.orourkes.me +short
# Should return: 10.27.10.104

# Test HTTPS (after nginx setup)
curl -I https://mediavault.orourkes.me
```

---

## Next Steps

### 1. Install Nginx Config
```bash
cd /home/mercury/projects/mediavault
sudo cp nginx-mediavault.conf /etc/nginx/sites-available/mediavault.orourkes.me
sudo ln -s /etc/nginx/sites-available/mediavault.orourkes.me /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. Create .env File
```bash
cd /home/mercury/projects/mediavault
cp .env.example .env

# Get postgres password from pm-ideas
grep POSTGRES_PASSWORD /home/mercury/projects/pm-ideas/.env

# Edit .env with real values
nano .env
```

### 3. Backend Development (Next Session)
- Create FastAPI app structure
- SQLAlchemy models
- Scanner service (NAS file walker)
- FFmpeg integration
- TMDb API service
- Docker Compose

---

## Troubleshooting

### Database Connection Issues
```bash
# Test connection from host
psql -U pm_ideas_user -h localhost -p 5433 -d mediavault

# Check postgres is listening
docker exec pm-ideas-postgres netstat -tlnp | grep 5432
```

### Nginx Issues
```bash
# Check for syntax errors
sudo nginx -t

# Check if site is enabled
ls -la /etc/nginx/sites-enabled/ | grep mediavault

# Reload config
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx
```

### Port Conflicts
```bash
# Check if ports 8007/3007 are available
sudo netstat -tlnp | grep -E '8007|3007'

# Should show nothing (ports available)
```

---

**Documentation Complete:** 2025-11-08
**Status:** Infrastructure ready, nginx config pending installation
**Next:** Install nginx, create .env, start backend development
