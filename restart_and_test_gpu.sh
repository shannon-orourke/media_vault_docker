#!/bin/bash
# Restart MediaVault backend and test GPU acceleration

set -e

echo "======================================"
echo "MediaVault GPU Setup - Restart & Test"
echo "======================================"

# Restart backend service
echo ""
echo "Step 1: Restarting backend service..."
sudo systemctl restart mediavault-backend

# Wait for service to start
echo "Waiting for service to start..."
sleep 5

# Check service status
echo ""
echo "Step 2: Checking service status..."
sudo systemctl status mediavault-backend --no-pager | head -15

# Test GPU status endpoint
echo ""
echo "Step 3: Testing GPU status endpoint..."
echo "GET https://mediavault.orourkes.me/api/stream/gpu-status"

curl -s -k https://mediavault.orourkes.me/api/stream/gpu-status | jq '.'

# Run Python GPU tests
echo ""
echo "Step 4: Running GPU transcoding tests..."
cd /home/mercury/projects/mediavault/backend
python3 test_gpu_streaming.py

echo ""
echo "======================================"
echo "GPU Setup Complete!"
echo "======================================"
echo ""
echo "New GPU-accelerated endpoints available:"
echo "  - GET /api/stream/gpu-status"
echo "  - GET /api/stream/{file_id}/transcode?width=1280&height=720&use_gpu=true"
echo "  - GET /api/stream/{file_id}/preview?start_time=00:00:10&duration=30&use_gpu=true"
echo ""
echo "Test in browser:"
echo "  https://mediavault.orourkes.me/api/stream/gpu-status"
echo ""
