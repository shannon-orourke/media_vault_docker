#!/bin/bash
echo "Triggering stream request in background..."
timeout 10 curl -s -k "https://mediavault.orourkes.me/api/stream/335/smart" > /dev/null 2>&1 &
CURL_PID=$!

echo "Waiting 3 seconds..."
sleep 3

echo ""
echo "Backend logs (last 50 lines):"
sudo journalctl -u mediavault-backend -n 50 --no-pager | grep -E "(FFmpeg|stream|error|ERROR)" || echo "No matching logs found"

kill $CURL_PID 2>/dev/null
wait $CURL_PID 2>/dev/null
