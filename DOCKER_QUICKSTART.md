# MediaVault Docker Quick Start

This project is now fully Dockerized! Here's how to get started.

## What's Been Created

✅ **Backend Dockerfile** (`backend/Dockerfile`)
- NVIDIA CUDA base image for GPU acceleration
- Python 3.11 with all dependencies
- FFmpeg, MediaInfo, CIFS utilities
- Privileged mode for NAS mounting

✅ **Frontend Dockerfile** (`frontend/Dockerfile`)
- Multi-stage build (Node.js → Nginx)
- Production-optimized with small final image
- Built-in API proxy configuration

✅ **Docker Compose** (`docker-compose.yml`)
- Two services: backend and frontend
- Proper networking between containers
- GPU support configured
- All environment variables mapped

✅ **Environment Variables** (`.env`)
- Pre-configured with your existing settings
- **IMPORTANT**: Database URL updated to use host IP (10.27.10.104)
- All secrets already in place

✅ **Dockerignore Files**
- Optimized build context for faster builds
- Excludes unnecessary files

✅ **Documentation** (`DOCKER_SETUP.md`)
- Complete guide for managing Docker environment
- Troubleshooting section
- Security best practices

## Quick Start Commands

### 1. First Time Setup
```bash
cd /home/user/media_vault_docker

# Verify .env exists and has correct values
cat .env | grep DATABASE_URL
# Should show: postgresql://...@10.27.10.104:5433/mediavault

# Build and start services
docker compose up --build
```

### 2. Run in Background
```bash
docker compose up -d --build
docker compose logs -f
```

### 3. Access Your Application
- Frontend: http://localhost:3007 or https://mediavault.orourkes.me
- Backend API: http://localhost:8007
- API Docs: http://localhost:8007/docs

### 4. Stop Services
```bash
docker compose down
```

## Important Environment Variable Notes

### Database Connection
The `.env` file now uses the host IP address instead of `localhost`:

```env
# ✅ CORRECT (for Docker)
DATABASE_URL=postgresql://pm_ideas_user:PASSWORD@10.27.10.104:5433/mediavault

# ❌ WRONG (won't work from inside container)
DATABASE_URL=postgresql://pm_ideas_user:PASSWORD@localhost:5433/mediavault
```

This is because Docker containers cannot access the host's `localhost`. They need to use:
- **Host IP address** (10.27.10.104) - Recommended
- OR `host.docker.internal` (Docker Desktop only)

### Environment Variable Hierarchy

1. **`.env`** (root) - Used by docker-compose.yml
2. **`docker-compose.yml`** - Reads .env and passes to containers
3. **Container environment** - Variables available inside containers

### Verifying Environment Variables

```bash
# Check what docker-compose will use
docker compose config

# Check variables inside running container
docker exec mediavault-backend env | grep DATABASE_URL
```

## GPU Acceleration

The backend container requires NVIDIA Docker runtime for GPU-accelerated MD5 hashing:

```bash
# Test GPU access
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Verify GPU in backend container (after starting)
docker exec mediavault-backend nvidia-smi
```

If you don't need GPU acceleration, you can remove these sections from `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

## NAS Mounting

The backend container has privileged access to mount your NAS:

```yaml
privileged: true
cap_add:
  - SYS_ADMIN
  - DAC_READ_SEARCH
```

The application will automatically mount:
```
//10.27.10.11/volume1 → /mnt/nas-media
```

## Port Mapping

| Service  | Container Port | Host Port | Public URL |
|----------|---------------|-----------|------------|
| Backend  | 8000          | 8007      | https://mediavault.orourkes.me/api |
| Frontend | 3000          | 3007      | https://mediavault.orourkes.me |

## Common Issues

### "Can't connect to database"
- Verify DATABASE_URL uses `10.27.10.104:5433`, not `localhost:5433`
- Check if PostgreSQL is running: `docker ps | grep postgres`

### "GPU not found"
- Install nvidia-docker2
- Verify with: `nvidia-smi`

### "NAS mount failed"
- Verify NAS is reachable: `ping 10.27.10.11`
- Check credentials in `.env`

### "Environment variable not found"
- Ensure `.env` is in project root (not in backend/ or frontend/)
- Restart containers: `docker compose restart`

## Next Steps

1. ✅ Start services: `docker compose up -d --build`
2. ✅ Check logs: `docker compose logs -f`
3. ✅ Access frontend: http://localhost:3007
4. ✅ Test API: http://localhost:8007/docs
5. ⬜ Configure Nginx reverse proxy (see `nginx-mediavault.conf`)
6. ⬜ Set up SSL certificates for production
7. ⬜ Create systemd service for auto-start

## File Structure Summary

```
media_vault_docker/
├── .env                       # 🔐 Docker Compose environment (contains secrets)
├── .env.example               # ✅ Template (safe to commit)
├── docker-compose.yml         # 🐳 Service orchestration
├── DOCKER_SETUP.md           # 📖 Complete guide
├── DOCKER_QUICKSTART.md      # ⚡ This file
├── backend/
│   ├── Dockerfile            # 🐳 Backend image definition
│   ├── .dockerignore         # 🚫 Build exclusions
│   ├── .env                  # ⚠️ Old (not used by Docker)
│   └── requirements.txt      # 📦 Python dependencies
└── frontend/
    ├── Dockerfile            # 🐳 Frontend image definition
    ├── .dockerignore         # 🚫 Build exclusions
    └── package.json          # 📦 Node.js dependencies
```

## Security Reminders

- ✅ `.env` is in `.gitignore` (contains secrets)
- ✅ Use strong JWT_SECRET_KEY (32+ characters)
- ✅ ALLOW_REGISTRATION=false (after first user)
- ✅ Review CORS_ORIGINS before production

## Getting Help

- Full documentation: `DOCKER_SETUP.md`
- Project overview: `CLAUDE.md`
- Infrastructure details: `INFRASTRUCTURE.md`

---

**Ready to go!** Run `docker compose up --build` to start your Dockerized MediaVault! 🚀
