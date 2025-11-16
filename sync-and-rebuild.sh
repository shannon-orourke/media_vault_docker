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
echo -e "${GREEN}[1/4]${NC} Pulling latest code from Git..."
git fetch origin
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "Current branch: ${YELLOW}${CURRENT_BRANCH}${NC}"
git pull origin "${CURRENT_BRANCH}"
echo -e "${GREEN}✓${NC} Code synced successfully"
echo ""

# Step 2: Stop and remove existing containers
echo -e "${GREEN}[2/4]${NC} Stopping existing containers..."
if docker compose ps -q 2>/dev/null | grep -q .; then
    docker compose down
    echo -e "${GREEN}✓${NC} Containers stopped and removed"
else
    echo -e "${YELLOW}ℹ${NC} No running containers found"
fi
echo ""

# Step 3: Rebuild images
echo -e "${GREEN}[3/4]${NC} Rebuilding Docker images..."
docker compose build --no-cache
echo -e "${GREEN}✓${NC} Images rebuilt successfully"
echo ""

# Step 4: Start containers
echo -e "${GREEN}[4/4]${NC} Starting containers..."
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
