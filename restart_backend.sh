#!/bin/bash
# Quick backend restart

echo "Restarting backend..."
sudo systemctl restart mediavault-backend
sleep 3
echo "Backend status:"
systemctl status mediavault-backend --no-pager | head -10
echo ""
echo "Test HLS endpoint:"
curl -s -k https://mediavault.orourkes.me/api/stream/335/hls/master.m3u8
echo ""
