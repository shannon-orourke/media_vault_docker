#!/usr/bin/env python3
"""Test HLS generation directly."""

import sys
sys.path.insert(0, '/home/mercury/projects/mediavault/backend')

from app.services.hls_service import HLSService
from pathlib import Path

# Initialize service
hls = HLSService()

# Test file
test_file = "/mnt/nas-synology/docker/transmission/downloads/complete/tv/Red.Dwarf.COMPLETE.DVD.BluRay.REMUX.DD2.0.DTS/10x06 - The Beginning.mkv"
test_id = 999

print("Testing HLS generation...")
print(f"Input: {test_file}")
print(f"Output: {hls.get_hls_directory(test_id)}")
print("")

# Check if file exists
if not Path(test_file).exists():
    print(f"ERROR: File not found: {test_file}")
    sys.exit(1)

print("Starting HLS generation...")
success = hls.generate_hls_adaptive(
    input_path=test_file,
    file_id=test_id,
    use_gpu=True
)

if success:
    print("\n✓ HLS generation successful!")
    print(f"\nGenerated files:")
    output_dir = hls.get_hls_directory(test_id)
    for f in sorted(output_dir.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(output_dir)} ({f.stat().st_size / 1024 / 1024:.1f}MB)")
else:
    print("\n✗ HLS generation failed!")
    print("\nCheck FFmpeg output above for errors.")
