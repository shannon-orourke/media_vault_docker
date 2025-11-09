#!/bin/bash
# MediaVault Production Deployment Script
# Run this script to deploy MediaVault to production

set -e  # Exit on error

echo "=== MediaVault Production Deployment ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run with sudo${NC}"
    echo "Usage: sudo bash deploy-production.sh"
    exit 1
fi

echo -e "${YELLOW}Step 1: Verifying SSL certificates...${NC}"
if [ -f "/home/mercury/projects/domain_certificates/orourkes.me-wildcard.crt" ] && \
   [ -f "/home/mercury/projects/domain_certificates/orourkes.me-wildcard.key" ]; then
    echo -e "${GREEN}✓ SSL certificates found${NC}"
else
    echo -e "${RED}✗ SSL certificates not found!${NC}"
    echo "Expected files:"
    echo "  /home/mercury/projects/domain_certificates/orourkes.me-wildcard.crt"
    echo "  /home/mercury/projects/domain_certificates/orourkes.me-wildcard.key"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 2: Building frontend assets...${NC}"
pushd /home/mercury/projects/mediavault/frontend >/dev/null
sudo -u mercury npm ci
sudo -u mercury npm run build
popd >/dev/null
echo -e "${GREEN}✓ Frontend built${NC}"

echo ""
echo -e "${YELLOW}Step 3: Installing nginx configuration...${NC}"
cp /home/mercury/projects/mediavault/nginx-mediavault-production.conf \
   /etc/nginx/sites-available/mediavault.orourkes.me
ln -sf /etc/nginx/sites-available/mediavault.orourkes.me \
   /etc/nginx/sites-enabled/
echo -e "${GREEN}✓ nginx config installed${NC}"

echo ""
echo -e "${YELLOW}Step 4: Testing nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ nginx config valid${NC}"
else
    echo -e "${RED}✗ nginx config invalid!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 5: Reloading nginx...${NC}"
systemctl reload nginx
echo -e "${GREEN}✓ nginx reloaded${NC}"

echo ""
echo -e "${YELLOW}Step 6: Installing systemd service...${NC}"
cp /home/mercury/projects/mediavault/mediavault-backend.service \
   /etc/systemd/system/
systemctl daemon-reload
echo -e "${GREEN}✓ systemd service installed${NC}"

echo ""
echo -e "${YELLOW}Step 7: Stopping dev servers (if running)...${NC}"
pkill -f "uvicorn app.main:app --host 0.0.0.0 --port 8007" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
echo -e "${GREEN}✓ Dev servers stopped${NC}"

echo ""
echo -e "${YELLOW}Step 8: Starting production backend...${NC}"
systemctl enable mediavault-backend
systemctl restart mediavault-backend
sleep 3
if systemctl is-active --quiet mediavault-backend; then
    echo -e "${GREEN}✓ Backend service started${NC}"
else
    echo -e "${RED}✗ Backend service failed to start!${NC}"
    echo "Check logs: sudo journalctl -u mediavault-backend -n 50"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 9: Verifying deployment...${NC}"

# Test backend health
if curl -sf http://localhost:8007/api/health > /dev/null; then
    echo -e "${GREEN}✓ Backend health check passed${NC}"
else
    echo -e "${RED}✗ Backend health check failed!${NC}"
    exit 1
fi

# Test HTTPS
if curl -sf -I https://mediavault.orourkes.me > /dev/null; then
    echo -e "${GREEN}✓ HTTPS is working${NC}"
else
    echo -e "${YELLOW}⚠ HTTPS check failed (might be DNS propagation)${NC}"
fi

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Access your application at:"
echo "  https://mediavault.orourkes.me"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status mediavault-backend  # Check backend status"
echo "  sudo systemctl restart mediavault-backend # Restart backend"
echo "  sudo journalctl -u mediavault-backend -f  # View backend logs"
echo "  sudo tail -f /var/log/nginx/mediavault-access.log  # View access logs"
echo ""
