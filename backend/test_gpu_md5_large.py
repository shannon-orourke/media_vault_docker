"""Test GPU MD5 with larger files to see performance difference."""
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


def create_test_file(size_mb: int) -> str:
    """Create a temporary test file of given size."""
    print(f"Creating {size_mb}MB test file...")

    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
        # Write random data in larger chunks for speed
        chunk_size = 10 * 1024 * 1024  # 10MB chunks
        remaining = size_mb
        while remaining > 0:
            chunk_mb = min(10, remaining)
            f.write(os.urandom(chunk_mb * 1024 * 1024))
            remaining -= chunk_mb
        return f.name


def test_file_size(size_mb: int):
    """Test MD5 hashing with a specific file size."""
    print("\n" + "=" * 60)
    print(f"Testing with {size_mb}MB file")
    print("=" * 60)

    test_file = create_test_file(size_mb)

    try:
        print(f"File size: {os.path.getsize(test_file) / (1024 * 1024):.2f} MB")

        # Test CPU
        print("\nCPU MD5 hashing...")
        start = time.time()
        cpu_hash = calculate_md5_cpu(test_file)
        cpu_time = time.time() - start
        print(f"  Hash: {cpu_hash}")
        print(f"  Time: {cpu_time:.4f}s")
        print(f"  Speed: {size_mb / cpu_time:.2f} MB/s")

        # Test GPU
        if has_cuda_available():
            print("\nGPU MD5 hashing...")
            start = time.time()
            gpu_hash = calculate_md5_gpu(test_file)
            gpu_time = time.time() - start
            print(f"  Hash: {gpu_hash}")
            print(f"  Time: {gpu_time:.4f}s")
            print(f"  Speed: {size_mb / gpu_time:.2f} MB/s")

            # Compare
            match = "✓ MATCH" if cpu_hash == gpu_hash else "✗ MISMATCH"
            speedup = cpu_time / gpu_time if gpu_time > 0 else 0
            print(f"\n  {match}")
            print(f"  Speedup: {speedup:.2f}x")

    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)


def main():
    """Test with multiple file sizes."""
    print("=" * 60)
    print("GPU MD5 PERFORMANCE TEST - MULTIPLE FILE SIZES")
    print("=" * 60)

    # Check CUDA
    cuda_available = has_cuda_available()
    print(f"\nCUDA Available: {cuda_available}")

    if not cuda_available:
        print("ERROR: CUDA not available - cannot test GPU performance")
        return

    # Test with increasing file sizes
    file_sizes = [50, 100, 500, 1000]  # MB

    for size_mb in file_sizes:
        test_file_size(size_mb)

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
