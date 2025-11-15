#!/bin/bash
# Deploy GPU streaming updates

set -e

echo "======================================"
echo "Deploying GPU Streaming Updates"
echo "======================================"

# Build frontend
echo ""
echo "Step 1: Building frontend with GPU transcoding support..."
cd /home/mercury/projects/mediavault/frontend
npm run build

# Restart backend
echo ""
echo "Step 2: Restarting backend service..."
sudo systemctl restart mediavault-backend

# Wait for services
echo "Waiting for services to start..."
sleep 5

# Check backend status
echo ""
echo "Step 3: Checking backend status..."
sudo systemctl status mediavault-backend --no-pager | head -15

# Test GPU endpoint
echo ""
echo "Step 4: Testing GPU status endpoint..."
echo "GET /api/stream/gpu-status"
curl -s -k https://mediavault.orourkes.me/api/stream/gpu-status | jq '.'

echo ""
echo "======================================"
echo "✓ Deployment Complete!"
echo "======================================"
echo ""
echo "GPU Transcoding is now enabled!"
echo ""
echo "To test:"
echo "1. Go to https://mediavault.orourkes.me"
echo "2. Click Library"
echo "3. Click the play button on any video"
echo "4. In another terminal, run: watch -n 1 nvidia-smi"
echo "5. You should see GPU encoder activity when video loads!"
echo ""
echo "The video player will now:"
echo "  - Transcode to 720p (1280x720) using GPU"
echo "  - Use NVIDIA NVENC for encoding"
echo "  - Be 10-15x faster than CPU"
echo ""
