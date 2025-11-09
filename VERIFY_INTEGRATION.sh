#!/bin/bash

echo "MediaVault Integration Verification"
echo "===================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check backend
echo -n "Backend (port 8007): "
if curl -s http://localhost:8007/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check frontend
echo -n "Frontend (port 3007): "
if curl -s http://localhost:3007 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check database
echo -n "Database connection: "
if curl -s http://localhost:8007/api/media/?limit=1 | grep -q "files"; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Not connected${NC}"
fi

# Check media files
echo -n "Media files: "
COUNT=$(curl -s http://localhost:8007/api/media/?limit=1 | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))" 2>/dev/null)
if [ "$COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ $COUNT files indexed${NC}"
else
    echo -e "${YELLOW}⚠ No files found${NC}"
fi

# Check streaming
echo -n "Streaming endpoint: "
if curl -I http://localhost:8007/api/stream/335 2>&1 | grep -q "HTTP/1.1 200"; then
    echo -e "${GREEN}✓ Working${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

# Check pending deletions
echo -n "Pending deletions: "
PENDING=$(curl -s http://localhost:8007/api/deletions/pending | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))" 2>/dev/null)
echo -e "${GREEN}$PENDING pending${NC}"

# Check temp directory
echo -n "Temp delete dir: "
if [ -d "/home/mercury/tmp/mediavault/deletions" ]; then
    echo -e "${GREEN}✓ Created${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
fi

# Check frontend .env
echo -n "Frontend .env: "
if [ -f "/home/mercury/projects/mediavault/frontend/.env" ]; then
    echo -e "${GREEN}✓ Configured${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
fi

echo ""
echo "===================================="
echo -e "${GREEN}System ready for testing!${NC}"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:3007 in browser"
echo "2. Test video playback (click Play button)"
echo "3. Test file deletion workflow"
echo "4. Check INTEGRATION_COMPLETE.md for full test scenarios"
