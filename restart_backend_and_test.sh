#!/bin/bash
echo "Restarting backend with HEAD request fix..."
sudo systemctl restart mediavault-backend
sleep 3

echo ""
echo "Testing HEAD request to progressive endpoint..."
curl -I -k "https://mediavault.orourkes.me/api/stream/335/progressive" 2>&1 | grep -E "(HTTP|Content-Type)"

echo ""
echo "Testing HEAD request to smart endpoint..."
curl -I -k "https://mediavault.orourkes.me/api/stream/335/smart" 2>&1 | grep -E "(HTTP|Content-Type)"

echo ""
echo "Running automated tests..."
cd /home/mercury/projects/mediavault/backend
python -m pytest tests/test_streaming_e2e.py::TestStreamAPIValidation::test_response_headers -v -s
echo ""
python -m pytest tests/test_streaming_e2e.py::TestBrowserPlayback::test_video_actually_plays -v -s --tb=short
