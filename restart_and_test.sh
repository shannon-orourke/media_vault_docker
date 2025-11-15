#!/bin/bash
echo "Restarting MediaVault backend..."
sudo systemctl restart mediavault-backend
sleep 3

echo ""
echo "Checking backend status..."
sudo systemctl status mediavault-backend --no-pager | head -15

echo ""
echo "Testing progressive endpoint..."
timeout 5 curl -s -k "https://mediavault.orourkes.me/api/stream/335/progressive?use_gpu=true" 2>&1 | head -c 100 | xxd

echo ""
echo ""
echo "If you see binary data (00 00 00...), the endpoint is working!"
echo "If you still see 'Internal Server Error', check logs with:"
echo "  sudo journalctl -u mediavault-backend -n 50 --no-pager"
