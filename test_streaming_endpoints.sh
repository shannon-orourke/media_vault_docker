#!/bin/bash
# Test streaming endpoints directly

echo "======================================"
echo "Testing Streaming Endpoints"
echo "======================================"
echo ""

FILE_ID=335

echo "Test 1: Health Check"
curl -s -k https://mediavault.orourkes.me/api/health | jq '.'

echo ""
echo "Test 2: GPU Status"
curl -s -k https://mediavault.orourkes.me/api/stream/gpu-status | jq '.'

echo ""
echo "Test 3: Media File Info"
curl -s -k "https://mediavault.orourkes.me/api/media/${FILE_ID}" | jq '{id, filename, video_codec, audio_codec, format}'

echo ""
echo "Test 4: Smart Stream Endpoint (should redirect)"
curl -I -k "https://mediavault.orourkes.me/api/stream/${FILE_ID}/smart" 2>&1 | grep -E "(HTTP|Location|Content)"

echo ""
echo "Test 5: Progressive Stream (first 1KB)"
echo "Starting progressive stream test..."
timeout 5 curl -k "https://mediavault.orourkes.me/api/stream/${FILE_ID}/progressive?use_gpu=true" -o /tmp/progressive_test.mp4 2>&1 | tail -3
ls -lh /tmp/progressive_test.mp4 2>&1

echo ""
echo "Test 6: Check browser console"
echo "Open browser DevTools (F12) → Network tab"
echo "Filter: /stream/"
echo "Look for red errors or failed requests"
echo ""
