#!/bin/bash

# MediaVault Docker - Sync and Rebuild Script
# This script pulls the latest code and rebuilds the containers

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  MediaVault - Sync & Rebuild Script   ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo ""

# Step 1: Pull latest code
echo -e "${GREEN}[1/5]${NC} Pulling latest code from Git..."
git fetch origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "Current branch: ${YELLOW}${CURRENT_BRANCH}${NC}"
git pull origin "${CURRENT_BRANCH}"
echo -e "${GREEN}✓${NC} Code synced successfully"
echo ""

# Step 2: Stop and remove existing containers
echo -e "${GREEN}[2/5]${NC} Stopping existing containers..."
if docker compose ps -q 2>/dev/null | grep -q .; then
    docker compose down
    echo -e "${GREEN}✓${NC} Containers stopped and removed"
else
    echo -e "${YELLOW}ℹ${NC} No running containers found"
fi

# Wait for containers to fully release ports
echo -e "${BLUE}ℹ${NC} Waiting 3 seconds for containers to fully stop..."
sleep 3
echo ""

# Step 3: Clean up port 8007 and orphaned containers
echo -e "${GREEN}[3/5]${NC} Cleaning up port 8007 and orphaned containers..."

# Always kill any processes on port 8007 (try without sudo first, fallback to sudo)
PIDS=$(lsof -ti:8007 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}⚠${NC} Port 8007 is in use, killing processes..."
    echo "$PIDS" | xargs kill -9 2>/dev/null || echo "$PIDS" | xargs sudo kill -9 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Processes killed"
else
    echo -e "${GREEN}✓${NC} Port 8007 is free"
fi

# Remove orphaned mediavault containers
ORPHANED=$(docker ps -a --filter "name=mediavault" --format "{{.ID}}" 2>/dev/null || true)
if [ -n "$ORPHANED" ]; then
    echo -e "${YELLOW}⚠${NC} Found orphaned mediavault containers, removing..."
    echo "$ORPHANED" | xargs -r docker rm -f 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Orphaned containers removed"
else
    echo -e "${GREEN}✓${NC} No orphaned containers found"
fi

# Wait for port to fully release
echo -e "${BLUE}ℹ${NC} Waiting 4 seconds for port to fully release..."
sleep 4
echo -e "${GREEN}✓${NC} Port cleanup complete"
echo ""

# Step 4: Rebuild images
echo -e "${GREEN}[4/6]${NC} Rebuilding Docker images..."
docker compose build --no-cache
echo -e "${GREEN}✓${NC} Images rebuilt successfully"
echo ""

# Step 5: Final port cleanup before starting
echo -e "${GREEN}[5/6]${NC} Final port check before starting..."
PIDS=$(lsof -ti:8007 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}⚠${NC} Port 8007 is in use again, killing processes..."
    echo "$PIDS" | xargs kill -9 2>/dev/null || echo "$PIDS" | xargs sudo kill -9 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓${NC} Processes killed"
else
    echo -e "${GREEN}✓${NC} Port 8007 is still free"
fi
echo ""

# Step 6: Start containers
echo -e "${GREEN}[6/6]${NC} Starting containers..."
docker compose up -d
echo -e "${GREEN}✓${NC} Containers started"
echo ""

# Show status
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Container Status:"
docker compose ps
echo ""
echo -e "${YELLOW}Frontend:${NC} http://localhost:3007"
echo -e "${YELLOW}Backend:${NC}  http://localhost:8007"
echo -e "${YELLOW}API Docs:${NC} http://localhost:8007/docs"
echo ""
echo -e "To view logs: ${BLUE}docker compose logs -f${NC}"
echo ""
