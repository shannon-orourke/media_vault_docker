#!/usr/bin/env python3
"""Test GPU-accelerated video streaming functionality."""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.ffmpeg_service import FFmpegService
from loguru import logger

def test_gpu_availability():
    """Test if GPU encoding is available."""
    print("\n" + "="*60)
    print("TEST 1: GPU Encoding Availability")
    print("="*60)

    ffmpeg = FFmpegService()
    gpu_available = ffmpeg.check_gpu_encoding_available()

    if gpu_available:
        print("✓ PASS: NVENC GPU encoding is available")
        return True
    else:
        print("✗ FAIL: NVENC GPU encoding not available")
        return False


def test_gpu_transcode():
    """Test GPU transcoding with a sample video."""
    print("\n" + "="*60)
    print("TEST 2: GPU Transcoding Performance")
    print("="*60)

    # Find a video file from the database
    from app.database import get_db
    from app.models import MediaFile

    db = next(get_db())
    sample_file = db.query(MediaFile).filter(
        MediaFile.media_type == "movie"
    ).first()

    if not sample_file:
        print("⚠ SKIP: No video files found in database")
        return None

    print(f"Using test file: {sample_file.filename}")
    print(f"Original resolution: {sample_file.width}x{sample_file.height}")
    print(f"Original codec: {sample_file.video_codec}")

    # Test paths
    from app.utils.path_utils import resolve_media_path
    input_path = resolve_media_path(sample_file.filepath)

    if not input_path or not input_path.exists():
        print(f"✗ FAIL: Source file not found: {sample_file.filepath}")
        return False

    output_gpu = Path("/tmp/test_gpu_transcode.mp4")
    output_cpu = Path("/tmp/test_cpu_transcode.mp4")

    ffmpeg = FFmpegService()

    # Test GPU transcoding
    print("\n--- GPU Transcoding Test ---")
    import time

    start = time.time()
    success_gpu = ffmpeg.transcode_for_streaming_gpu(
        input_path=str(input_path),
        output_path=str(output_gpu),
        width=1280,
        height=720,
        use_gpu=True
    )
    gpu_time = time.time() - start

    if success_gpu:
        gpu_size = output_gpu.stat().st_size / (1024 * 1024)  # MB
        print(f"✓ GPU transcode completed in {gpu_time:.2f}s")
        print(f"  Output size: {gpu_size:.2f} MB")
        print(f"  Output file: {output_gpu}")
    else:
        print("✗ GPU transcode failed")
        return False

    # Test CPU transcoding for comparison
    print("\n--- CPU Transcoding Test (for comparison) ---")

    start = time.time()
    success_cpu = ffmpeg.transcode_for_streaming_gpu(
        input_path=str(input_path),
        output_path=str(output_cpu),
        width=1280,
        height=720,
        use_gpu=False
    )
    cpu_time = time.time() - start

    if success_cpu:
        cpu_size = output_cpu.stat().st_size / (1024 * 1024)  # MB
        print(f"✓ CPU transcode completed in {cpu_time:.2f}s")
        print(f"  Output size: {cpu_size:.2f} MB")
        print(f"  Output file: {output_cpu}")
    else:
        print("✗ CPU transcode failed")

    # Compare performance
    if success_gpu and success_cpu:
        speedup = cpu_time / gpu_time
        print(f"\n🚀 GPU Speedup: {speedup:.2f}x faster than CPU")

        if speedup > 1.5:
            print("✓ EXCELLENT: GPU acceleration working well!")
        elif speedup > 1.0:
            print("✓ GOOD: GPU is faster than CPU")
        else:
            print("⚠ WARNING: GPU not faster than CPU (check drivers)")

    # Cleanup
    for f in [output_gpu, output_cpu]:
        if f.exists():
            f.unlink()
            print(f"Cleaned up: {f}")

    return success_gpu


def test_preview_clip():
    """Test GPU preview clip generation."""
    print("\n" + "="*60)
    print("TEST 3: GPU Preview Clip Generation")
    print("="*60)

    from app.database import get_db
    from app.models import MediaFile
    from app.utils.path_utils import resolve_media_path

    db = next(get_db())
    sample_file = db.query(MediaFile).first()

    if not sample_file:
        print("⚠ SKIP: No video files found")
        return None

    input_path = resolve_media_path(sample_file.filepath)
    if not input_path or not input_path.exists():
        print("✗ FAIL: Source file not found")
        return False

    output_preview = Path("/tmp/test_preview.mp4")

    ffmpeg = FFmpegService()

    import time
    start = time.time()

    success = ffmpeg.create_preview_clip_gpu(
        input_path=str(input_path),
        output_path=str(output_preview),
        start_time="00:00:05",
        duration=10,  # 10 second preview
        use_gpu=True
    )

    elapsed = time.time() - start

    if success and output_preview.exists():
        size = output_preview.stat().st_size / (1024 * 1024)
        print(f"✓ Preview clip generated in {elapsed:.2f}s")
        print(f"  Size: {size:.2f} MB")
        print(f"  Duration: 10 seconds")
        print(f"  Output: {output_preview}")

        # Cleanup
        output_preview.unlink()
        print(f"Cleaned up: {output_preview}")
        return True
    else:
        print("✗ Preview generation failed")
        return False


def main():
    """Run all GPU streaming tests."""
    print("\n" + "="*60)
    print("MediaVault GPU Streaming Test Suite")
    print("="*60)

    results = {}

    # Test 1: GPU availability
    results['gpu_available'] = test_gpu_availability()

    if not results['gpu_available']:
        print("\n⚠ GPU not available - skipping transcode tests")
        return

    # Test 2: GPU transcoding
    results['transcode'] = test_gpu_transcode()

    # Test 3: Preview clips
    results['preview'] = test_preview_clip()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⚠ SKIP"

        print(f"{status:8} {test_name}")

    all_passed = all(r in [True, None] for r in results.values())

    if all_passed:
        print("\n✓ All tests passed! GPU acceleration is working.")
    else:
        print("\n✗ Some tests failed. Check the output above.")


if __name__ == "__main__":
    main()
