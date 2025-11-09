"""Test GPU-accelerated MD5 hashing performance."""
import sys
import time
import tempfile
import os
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from services.cuda_hash import (
    has_cuda_available,
    calculate_md5_cpu,
    calculate_md5_gpu,
    calculate_md5,
)


def create_test_file(size_mb: int = 100) -> str:
    """Create a temporary test file of given size."""
    print(f"Creating {size_mb}MB test file...")

    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
        # Write random data
        chunk_size = 1024 * 1024  # 1MB chunks
        for _ in range(size_mb):
            f.write(os.urandom(chunk_size))
        return f.name


def benchmark_md5(file_path: str):
    """Benchmark CPU vs GPU MD5 hashing."""
    print(f"\nTesting file: {file_path}")
    print(f"File size: {os.path.getsize(file_path) / (1024 * 1024):.2f} MB")
    print("-" * 60)

    # Check CUDA availability
    cuda_available = has_cuda_available()
    print(f"CUDA Available: {cuda_available}")

    if not cuda_available:
        print("\nWARNING: CUDA not available - only testing CPU")

    print()

    # Test CPU hashing
    print("Testing CPU MD5 hashing...")
    start = time.time()
    cpu_hash = calculate_md5_cpu(file_path)
    cpu_time = time.time() - start
    print(f"CPU Hash: {cpu_hash}")
    print(f"CPU Time: {cpu_time:.4f} seconds")
    print()

    if cuda_available:
        # Test GPU hashing
        print("Testing GPU MD5 hashing...")
        start = time.time()
        gpu_hash = calculate_md5_gpu(file_path)
        gpu_time = time.time() - start
        print(f"GPU Hash: {gpu_hash}")
        print(f"GPU Time: {gpu_time:.4f} seconds")
        print()

        # Verify hashes match
        if cpu_hash == gpu_hash:
            print("✓ Hash verification: PASSED (CPU and GPU hashes match)")
        else:
            print("✗ Hash verification: FAILED (CPU and GPU hashes differ!)")

        # Calculate speedup
        speedup = cpu_time / gpu_time if gpu_time > 0 else 0
        print(f"\nSpeedup: {speedup:.2f}x")

        if speedup > 1:
            print(f"GPU is {speedup:.2f}x faster than CPU")
        elif speedup < 1:
            print(f"CPU is {1/speedup:.2f}x faster than GPU")
        else:
            print("CPU and GPU are equally fast")

    # Test automatic selection
    print("\n" + "-" * 60)
    print("Testing automatic GPU/CPU selection...")
    start = time.time()
    auto_hash = calculate_md5(file_path, prefer_gpu=True)
    auto_time = time.time() - start
    print(f"Auto Hash: {auto_hash}")
    print(f"Auto Time: {auto_time:.4f} seconds")

    return cpu_hash, cpu_time


def test_with_real_video():
    """Test with a real video file if available."""
    # Common video paths on the NAS
    test_paths = [
        "/mnt/nas-synology/volume1/videos",
        "/mnt/nas-media/volume1/videos",
        "/home/mercury/Videos",
    ]

    video_file = None
    for base_path in test_paths:
        if os.path.exists(base_path):
            # Find first video file
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                        video_file = os.path.join(root, file)
                        break
                if video_file:
                    break
            if video_file:
                break

    if video_file:
        print("\n" + "=" * 60)
        print("TESTING WITH REAL VIDEO FILE")
        print("=" * 60)
        benchmark_md5(video_file)
    else:
        print("\nNo real video files found for testing")


def main():
    """Main test function."""
    print("=" * 60)
    print("GPU-ACCELERATED MD5 HASHING TEST")
    print("=" * 60)

    # Test with generated file
    print("\n" + "=" * 60)
    print("TESTING WITH GENERATED FILE (100MB)")
    print("=" * 60)

    test_file = create_test_file(size_mb=100)

    try:
        benchmark_md5(test_file)

        # Test with real video if available
        test_with_real_video()

    finally:
        # Cleanup test file
        if os.path.exists(test_file):
            os.unlink(test_file)
            print(f"\nCleaned up test file: {test_file}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
