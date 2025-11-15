#!/bin/bash
# Manual GPU transcode test with local file

set -e

TEST_VIDEO="/home/mercury/projects/mediavault/backend/tmp/duplicates_before_purge/other/2025-11-08/test-video.mp4"
OUTPUT_GPU="/tmp/gpu_test_output.mp4"
OUTPUT_CPU="/tmp/cpu_test_output.mp4"

echo "======================================"
echo "GPU Transcoding Test"
echo "======================================"
echo ""

# Check if test file exists
if [ ! -f "$TEST_VIDEO" ]; then
    echo "❌ Test video not found: $TEST_VIDEO"
    exit 1
fi

echo "✓ Test video found: $TEST_VIDEO"
ls -lh "$TEST_VIDEO"
echo ""

# Test GPU transcode
echo "Testing GPU transcode (NVENC)..."
echo "Command: ffmpeg -hwaccel cuda -i input -vf scale_cuda=640:360 -c:v h264_nvenc ..."
echo ""

time ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda \
    -i "$TEST_VIDEO" \
    -vf scale_cuda=640:360 \
    -c:v h264_nvenc -preset p4 -cq 23 \
    -c:a aac -b:a 128k \
    -movflags +faststart \
    "$OUTPUT_GPU" 2>&1 | grep -E "(frame=|speed=|time=|encoder|NVENC)" || true

echo ""
if [ -f "$OUTPUT_GPU" ]; then
    echo "✓ GPU transcode complete!"
    ls -lh "$OUTPUT_GPU"
else
    echo "❌ GPU transcode failed!"
    exit 1
fi

echo ""
echo "Testing CPU transcode (libx264) for comparison..."
echo ""

time ffmpeg -y -i "$TEST_VIDEO" \
    -vf scale=640:360 \
    -c:v libx264 -preset medium -crf 23 \
    -c:a aac -b:a 128k \
    -movflags +faststart \
    "$OUTPUT_CPU" 2>&1 | grep -E "(frame=|speed=|time=)" || true

echo ""
if [ -f "$OUTPUT_CPU" ]; then
    echo "✓ CPU transcode complete!"
    ls -lh "$OUTPUT_CPU"
else
    echo "❌ CPU transcode failed!"
fi

echo ""
echo "======================================"
echo "Results:"
echo "======================================"
echo "GPU output: $OUTPUT_GPU"
echo "CPU output: $OUTPUT_CPU"
echo ""
echo "To see GPU activity during transcode, run in another terminal:"
echo "  watch -n 1 nvidia-smi"
echo ""
echo "Cleanup:"
echo "  rm $OUTPUT_GPU $OUTPUT_CPU"
echo ""
