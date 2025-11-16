# MediaVault - Deployment Guide

## Remote Machine Workflow

This guide explains how to sync and rebuild MediaVault containers on your remote Ubuntu machine.

### Quick Start

```bash
# Clone the repository (first time only)
git clone https://github.com/shannon-orourke/media_vault_docker.git
cd media_vault_docker

# Run the sync and rebuild script
./sync-and-rebuild.sh
```

### Available Scripts

#### 1. **sync-and-rebuild.sh** (Full Rebuild)
Complete rebuild with no cache - use this for clean deployments.

```bash
./sync-and-rebuild.sh
```

**What it does:**
1. Pulls latest code from Git
2. Stops and removes existing containers
3. Rebuilds Docker images (no cache)
4. Starts containers in detached mode
5. Shows container status and URLs

**Use when:**
- First deployment
- Major changes
- Troubleshooting issues
- Need clean build

#### 2. **quick-rebuild.sh** (Fast Rebuild)
Quick rebuild using Docker cache - faster for development iterations.

```bash
./quick-rebuild.sh
```

**What it does:**
1. Syncs latest code
2. Stops containers
3. Rebuilds with cache (faster)
4. Starts containers
5. Shows URLs

**Use when:**
- Testing frontend changes
- Rapid development cycles
- Minor code updates
- Cache is still valid

### Workflow Example

```bash
# On your local machine (using Claude Code web):
# - Make changes to code
# - Claude commits and pushes to branch

# On your remote Ubuntu machine:
cd /path/to/media_vault_docker
./quick-rebuild.sh

# Test the changes at:
# Frontend: http://localhost:3007
# Backend:  http://localhost:8007
# API Docs: http://localhost:8007/docs
```

### Viewing Logs

```bash
# Follow all logs
docker-compose logs -f

# Follow specific service
docker-compose logs -f frontend
docker-compose logs -f backend

# View recent logs
docker-compose logs --tail=100
```

### Troubleshooting

#### Containers won't start
```bash
# Check status
docker-compose ps

# View logs
docker-compose logs

# Full cleanup and rebuild
docker-compose down -v  # WARNING: Removes volumes
./sync-and-rebuild.sh
```

#### Port conflicts
```bash
# Check what's using the ports
sudo lsof -i :3007
sudo lsof -i :8007

# Stop containers
docker-compose down
```

#### Out of disk space
```bash
# Clean up unused Docker resources
docker system prune -a

# Remove unused volumes
docker volume prune
```

### Environment Setup

Ensure `.env` file exists with correct values:

```bash
# Check if .env exists
ls -la .env

# If not, copy from template
cp .env.example .env

# Edit with your values
nano .env
```

### Production Deployment

For production with nginx (mediavault.orourkes.me):

```bash
# 1. Sync and rebuild
./sync-and-rebuild.sh

# 2. Install nginx config (first time only)
sudo cp nginx-mediavault.conf /etc/nginx/sites-available/mediavault.orourkes.me
sudo ln -s /etc/nginx/sites-available/mediavault.orourkes.me /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 3. Access via domain
# https://mediavault.orourkes.me
```

### Script Customization

Both scripts support these modifications:

```bash
# Pull from different branch
git pull origin main

# Skip git pull (use current code)
# Comment out the git pull line in the script

# Keep containers running (no rebuild)
docker-compose up -d

# Rebuild only one service
docker-compose build frontend
docker-compose up -d frontend
```

### Common Commands

```bash
# Stop containers
docker-compose down

# Start containers (without rebuild)
docker-compose up -d

# Restart a service
docker-compose restart frontend

# Check status
docker-compose ps

# Shell into container
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Port Reference

- **3007**: Frontend (React/Vite)
- **8007**: Backend (FastAPI)
- **5433**: PostgreSQL (shared container: pm-ideas-postgres)

### Next Steps

1. Set up environment variables in `.env`
2. Ensure PostgreSQL is running (`pm-ideas-postgres` container)
3. Run `./sync-and-rebuild.sh` for first deployment
4. Use `./quick-rebuild.sh` for subsequent updates
5. Access frontend at http://localhost:3007

---

**Questions?** Check INFRASTRUCTURE.md for detailed setup information.
