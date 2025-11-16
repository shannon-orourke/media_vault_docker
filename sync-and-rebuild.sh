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
echo ""

# Step 3: Clean up port 8007 and orphaned containers
echo -e "${GREEN}[3/5]${NC} Cleaning up port 8007 and orphaned containers..."

# Kill any process using port 8007
if sudo lsof -i :8007 -t 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC} Port 8007 is in use, killing processes..."
    sudo lsof -i :8007 -t | xargs -r sudo kill -9
    echo -e "${GREEN}✓${NC} Processes killed"
else
    echo -e "${GREEN}✓${NC} Port 8007 is free"
fi

# Remove orphaned mediavault containers
ORPHANED=$(docker ps -a --filter "name=mediavault" --format "{{.ID}}" 2>/dev/null)
if [ -n "$ORPHANED" ]; then
    echo -e "${YELLOW}⚠${NC} Found orphaned mediavault containers, removing..."
    echo "$ORPHANED" | xargs -r docker rm -f
    echo -e "${GREEN}✓${NC} Orphaned containers removed"
else
    echo -e "${GREEN}✓${NC} No orphaned containers found"
fi

# Wait for port to fully release
echo -e "${BLUE}ℹ${NC} Waiting 2 seconds for port to fully release..."
sleep 2
echo -e "${GREEN}✓${NC} Port cleanup complete"
echo ""

# Step 4: Rebuild images
echo -e "${GREEN}[4/5]${NC} Rebuilding Docker images..."
docker compose build --no-cache
echo -e "${GREEN}✓${NC} Images rebuilt successfully"
echo ""

# Step 5: Start containers
echo -e "${GREEN}[5/5]${NC} Starting containers..."
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
