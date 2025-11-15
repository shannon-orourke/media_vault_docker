#!/bin/bash
echo "Testing smart endpoint and checking backend logs..."
echo ""

# Clear recent logs
echo "1. Testing smart endpoint..."
timeout 5 curl -v -k "https://mediavault.orourkes.me/api/stream/335/smart" > /dev/null 2>&1 &
CURL_PID=$!

sleep 2

echo ""
echo "2. Backend logs from the last 10 seconds:"
sudo journalctl -u mediavault-backend --since "10 seconds ago" --no-pager | tail -20

# Kill curl if still running
kill $CURL_PID 2>/dev/null

echo ""
echo "3. Testing if the redirect URL works directly:"
timeout 3 curl -s -k "https://mediavault.orourkes.me/api/stream/335/progressive?use_gpu=true" | head -c 100 | xxd
