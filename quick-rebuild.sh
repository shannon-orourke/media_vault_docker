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
echo -e "${GREEN}[2/4]${NC} Stopping containers..."
docker compose down 2>/dev/null || true
echo -e "${GREEN}✓${NC} Stopped"
echo ""

# Step 3: Rebuild (with cache)
echo -e "${GREEN}[3/4]${NC} Rebuilding (using cache)..."
docker compose build
echo -e "${GREEN}✓${NC} Built"
echo ""

# Step 4: Start
echo -e "${GREEN}[4/4]${NC} Starting..."
docker compose up -d
echo -e "${GREEN}✓${NC} Running"
echo ""

echo -e "${GREEN}✓ Ready!${NC}"
echo -e "${YELLOW}Frontend:${NC} http://localhost:3007"
echo -e "${YELLOW}Backend:${NC}  http://localhost:8007"
echo ""
