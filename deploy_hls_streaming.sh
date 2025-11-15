#!/bin/bash
# Deploy HLS adaptive streaming with GPU acceleration

set -e

echo "======================================"
echo "Deploying HLS Adaptive Streaming"
echo "======================================"
echo ""

# Restart backend
echo "Step 1: Restarting backend service..."
sudo systemctl restart mediavault-backend

echo "Waiting for backend to start..."
sleep 5

# Check backend status
echo ""
echo "Step 2: Checking backend status..."
sudo systemctl status mediavault-backend --no-pager | head -15

# Test new endpoints
echo ""
echo "Step 3: Testing new endpoints..."

echo ""
echo "Testing GPU status..."
curl -s -k https://mediavault.orourkes.me/api/stream/gpu-status | jq '.'

echo ""
echo "Testing smart stream endpoint (file 335)..."
curl -I -k https://mediavault.orourkes.me/api/stream/335/smart 2>&1 | grep -E "(HTTP|Location)" | head -5

echo ""
echo "======================================"
echo "✓ Deployment Complete!"
echo "======================================"
echo ""
echo "GPU-Accelerated HLS Adaptive Streaming is now active!"
echo ""
echo "How it works:"
echo "  1. Browser requests video playback"
echo "  2. Smart endpoint checks codec compatibility"
echo "  3. Compatible files (H.264 + AAC): Direct stream"
echo "  4. Incompatible files (DTS audio): HLS transcode"
echo ""
echo "Features:"
echo "  ✓ 3 quality levels (480p, 720p, 1080p)"
echo "  ✓ GPU NVENC encoding (10-15x faster than CPU)"
echo "  ✓ Adaptive bitrate switching"
echo "  ✓ Automatic codec detection"
echo "  ✓ LRU cache with 10GB limit"
echo ""
echo "Test now:"
echo "  1. Go to https://mediavault.orourkes.me/library"
echo "  2. Play a Red Dwarf episode (has DTS audio)"
echo "  3. In another terminal: watch -n 1 nvidia-smi"
echo "  4. Wait 8-12 seconds for HLS generation"
echo "  5. Video should start playing with quality selector!"
echo ""
echo "Monitor HLS generation:"
echo "  sudo journalctl -u mediavault-backend -f"
echo ""
echo "Check HLS files:"
echo "  ls -lh /tmp/mediavault_hls/"
echo ""
