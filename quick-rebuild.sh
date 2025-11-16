#!/bin/bash

# MediaVault Docker - Quick Rebuild Script (uses cache)
# Faster version for development iterations

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}⚡ Quick Rebuild (with cache)${NC}"
echo ""

# Step 1: Pull latest code
echo -e "${GREEN}[1/4]${NC} Syncing code..."
git fetch origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git pull origin "${CURRENT_BRANCH}"
echo -e "${GREEN}✓${NC} Synced"
echo ""

# Step 2: Stop containers
echo -e "${GREEN}[2/5]${NC} Stopping containers..."
docker compose down 2>/dev/null || true
echo -e "${GREEN}✓${NC} Stopped"

# Wait for containers to fully release ports
echo -e "${BLUE}ℹ${NC} Waiting 3 seconds for containers to fully stop..."
sleep 3
echo ""

# Step 3: Clean up port 8007 and orphaned containers
echo -e "${GREEN}[3/5]${NC} Cleaning up port 8007 and orphaned containers..."

# Always kill any processes on port 8007 (don't just check)
PIDS=$(lsof -ti:8007 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}⚠${NC} Port 8007 is in use, killing processes..."
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
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

# Step 4: Rebuild (with cache)
echo -e "${GREEN}[4/5]${NC} Rebuilding (using cache)..."
docker compose build
echo -e "${GREEN}✓${NC} Built"
echo ""

# Step 5: Final port cleanup before starting
echo -e "${GREEN}[5/6]${NC} Final port check before starting..."
PIDS=$(lsof -ti:8007 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}⚠${NC} Port 8007 is in use again, killing processes..."
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓${NC} Processes killed"
else
    echo -e "${GREEN}✓${NC} Port 8007 is still free"
fi
echo ""

# Step 6: Start
echo -e "${GREEN}[6/6]${NC} Starting..."
docker compose up -d
echo -e "${GREEN}✓${NC} Running"
echo ""

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Ready!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "🚀 Docker is up and running!"
echo ""
echo -e "Available Services:"
echo -e "  Frontend:  http://localhost:3007"
echo -e "  Backend:   http://localhost:8007"
echo -e "  API Docs:  http://localhost:8007/docs"
echo ""
