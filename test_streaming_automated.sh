#!/bin/bash
# Automated Video Streaming Test Suite
# This runs comprehensive tests without requiring manual browser interaction!

set -e

cd /home/mercury/projects/mediavault/backend

echo "========================================"
echo "MediaVault Streaming Test Suite"
echo "========================================"
echo ""
echo "This will test:"
echo "  ✓ API endpoints return valid MP4"
echo "  ✓ Video actually plays in browser"
echo "  ✓ GPU transcoding is triggered"
echo ""
echo "No manual clicking required!"
echo ""
echo "========================================"
echo ""

# Make sure Playwright browsers are installed
echo "Checking Playwright browser installation..."
python -m playwright install chromium 2>&1 | grep -v "is already installed" || true
echo ""

# Run the tests
echo "Running tests..."
echo ""

pytest tests/test_streaming_e2e.py -v -s --tb=short

echo ""
echo "========================================"
echo "Test Results Summary"
echo "========================================"
echo ""

# Check if screenshots were generated
if [ -f /tmp/video_playing.png ]; then
    echo "✓✓✓ SUCCESS: Video is playing!"
    echo "    Proof: /tmp/video_playing.png"
elif [ -f /tmp/video_stuck.png ]; then
    echo "✗✗✗ FAILURE: Video is stuck (not loading data)"
    echo "    Screenshot: /tmp/video_stuck.png"
    echo ""
    echo "This means:"
    echo "  - GPU spins up (FFmpeg starts)"
    echo "  - But stream doesn't reach browser"
    echo "  - Likely issue: Fragmented MP4 format, headers, or timeout"
else
    echo "⚠ Tests completed but no screenshots generated"
    echo "  Check test output above for details"
fi

echo ""
