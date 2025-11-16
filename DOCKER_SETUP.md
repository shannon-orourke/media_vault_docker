# MediaVault Docker Setup Guide

This guide explains how to run MediaVault using Docker and Docker Compose, including environment variable management.

## Prerequisites

1. **Docker** (version 20.10+)
2. **Docker Compose** (version 2.0+)
3. **NVIDIA Docker Runtime** (for GPU acceleration)
   ```bash
   # Install nvidia-docker2
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

## Project Structure

```
media_vault_docker/
├── backend/
│   ├── Dockerfile          # Backend container image
│   ├── .dockerignore       # Files to exclude from build
│   ├── requirements.txt    # Python dependencies
│   └── app/                # FastAPI application
├── frontend/
│   ├── Dockerfile          # Frontend container image (multi-stage build)
│   ├── .dockerignore       # Files to exclude from build
│   └── src/                # React application
├── docker-compose.yml      # Service orchestration
├── .env                    # Environment variables (DO NOT COMMIT)
└── .env.example            # Environment variable template
```

## Environment Variable Management

### 1. Root `.env` File (For Docker Compose)

The `.env` file in the project root is used by `docker-compose.yml` to pass environment variables into containers.

**IMPORTANT**: This file contains secrets and should NEVER be committed to git.

### 2. Environment Variable Flow

```
.env (root)
  ↓
docker-compose.yml (reads and passes to containers)
  ↓
Container environment variables
```

### 3. Key Environment Variables

#### Database Connection
```env
# IMPORTANT: Use host IP (10.27.10.104) instead of localhost
# Containers cannot access host's localhost directly
DATABASE_URL=postgresql://pm_ideas_user:PASSWORD@10.27.10.104:5433/mediavault
```

#### NAS Configuration
```env
NAS_HOST=10.27.10.11
NAS_SMB_USERNAME=ProxmoxBackupsSMB
NAS_SMB_PASSWORD=Setup123
NAS_MOUNT_PATH=/mnt/nas-media
```

#### External APIs
```env
TMDB_API_KEY=your_tmdb_api_key
AZURE_OPENAI_KEY=your_azure_key
```

### 4. Verifying Environment Variables

Check which environment variables are being used by a container:

```bash
# View backend container environment
docker exec mediavault-backend env | grep -E '(DATABASE_URL|NAS_HOST|TMDB_API_KEY)'

# View all environment variables
docker compose config
```

## Building and Running

### 1. First Time Setup

```bash
# Ensure .env file exists and is configured
cp .env.example .env
nano .env  # Edit with your actual values

# Verify GPU access
nvidia-smi

# Build and start services
docker compose up --build
```

### 2. Development Workflow

```bash
# Start services in detached mode
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild after code changes
docker compose up --build backend
docker compose up --build frontend

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v
```

### 3. Production Deployment

```bash
# Build with production environment
docker compose up -d --build

# Check service status
docker compose ps

# View resource usage
docker stats
```

## Service Details

### Backend Service
- **Container Name**: `mediavault-backend`
- **Port Mapping**: Host `8007` → Container `8000`
- **GPU Support**: Yes (CUDA 12.2)
- **Privileged Mode**: Yes (required for NAS mounting via CIFS)

### Frontend Service
- **Container Name**: `mediavault-frontend`
- **Port Mapping**: Host `3007` → Container `3000`
- **Multi-stage Build**: Yes (Node.js build → Nginx serve)

## Accessing Services

- **Frontend**: http://localhost:3007
- **Backend API**: http://localhost:8007
- **API Docs**: http://localhost:8007/docs
- **Production**: https://mediavault.orourkes.me

## NAS Mounting

The backend container has privileges to mount NAS shares internally using CIFS:

```bash
# Inside backend container
mount -t cifs //10.27.10.11/volume1 /mnt/nas-media \
  -o username=ProxmoxBackupsSMB,password=Setup123
```

This is handled automatically by the backend application on startup.

## Troubleshooting

### Container can't connect to database
```bash
# Check if PostgreSQL is accessible from host
psql -U pm_ideas_user -h 10.27.10.104 -p 5433 -d mediavault

# Verify DATABASE_URL uses host IP (10.27.10.104), not localhost
grep DATABASE_URL .env
```

### GPU not available in container
```bash
# Verify GPU is visible on host
nvidia-smi

# Check docker runtime
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Verify GPU in backend container
docker exec mediavault-backend nvidia-smi
```

### NAS mount fails
```bash
# Check container has required capabilities
docker inspect mediavault-backend | grep -A 20 CapAdd

# Verify NAS is accessible from host
ping 10.27.10.11
smbclient -L //10.27.10.11 -U ProxmoxBackupsSMB

# Check container logs
docker compose logs backend | grep -i "mount\|nas\|cifs"
```

### Frontend can't reach backend
```bash
# Verify backend is running
curl http://localhost:8007/health

# Check container network
docker network inspect media_vault_docker_mediavault-net

# Verify CORS settings in .env
grep CORS_ORIGINS .env
```

### Environment variable not loading
```bash
# Check if .env is in the correct location (project root)
ls -la .env

# Verify variable is in docker-compose.yml environment section
docker compose config | grep YOUR_VARIABLE_NAME

# Check container received the variable
docker exec mediavault-backend env | grep YOUR_VARIABLE_NAME
```

## Security Best Practices

1. **Never commit `.env` file** - It contains secrets
2. **Use strong JWT_SECRET_KEY** - Minimum 32 characters
3. **Rotate API keys regularly** - TMDb, Azure OpenAI
4. **Review CORS_ORIGINS** - Only allow trusted domains
5. **Use ALLOW_REGISTRATION=false** - After creating first user

## Updating Environment Variables

When you change values in `.env`:

```bash
# Restart services to pick up new values
docker compose down
docker compose up -d

# Or restart individual service
docker compose restart backend
```

**Note**: Some variables may require a full rebuild:

```bash
docker compose down
docker compose up --build -d
```

## Backup Considerations

### What to back up:
- `backend/app/` - Application code
- `frontend/src/` - Frontend code
- `.env.example` - Template (safe to commit)
- `docker-compose.yml` - Orchestration config

### What NOT to back up:
- `.env` - Contains secrets
- `node_modules/` - Can be reinstalled
- `backend/__pycache__/` - Generated files
- `frontend/dist/` - Build artifacts

## Next Steps

1. Configure Nginx reverse proxy (see `nginx-mediavault.conf`)
2. Set up SSL certificates for production
3. Configure backup strategy for database
4. Set up monitoring and logging (Langfuse/TraceForge)
5. Create systemd service for auto-start on boot

## Useful Commands

```bash
# View running containers
docker compose ps

# Execute command in backend container
docker compose exec backend bash

# Execute command in frontend container
docker compose exec frontend sh

# Clean up everything (DESTRUCTIVE)
docker compose down -v --remove-orphans

# View container resource usage
docker stats

# Inspect container
docker inspect mediavault-backend

# View container IP address
docker inspect mediavault-backend | grep IPAddress
```

## Environment Variables Reference

See `.env.example` for a complete list of all configurable environment variables with descriptions.

Key categories:
- **DATABASE** - PostgreSQL connection settings
- **SECURITY** - JWT secrets and registration control
- **NAS CONFIGURATION** - SMB mount settings
- **TMDB API** - Movie/TV metadata service
- **AZURE OPENAI** - Chat functionality
- **APPLICATION** - Server and CORS settings
- **FFMPEG/MEDIAINFO** - Media processing tools
- **DUPLICATE DETECTION** - Fuzzy matching thresholds
- **DELETION POLICY** - Safety controls
- **SCANNING** - File processing settings
- **LOGGING** - Log levels and rotation
- **LANGFUSE** - Observability (optional)
