#!/usr/bin/env python3
"""
Comprehensive CUDA Integration Test for MediaVault
Tests GPU detection, MD5 hashing, and scanner service integration
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

import tempfile
import os
from services.cuda_hash import has_cuda_available, calculate_md5
from services.ffmpeg_service import FFmpegService


def test_cuda_detection():
    """Test 1: CUDA Detection"""
    print("=" * 70)
    print("TEST 1: CUDA DETECTION")
    print("=" * 70)

    try:
        import cupy as cp
        print(f"✓ CuPy installed: version {cp.__version__}")

        cuda_version = cp.cuda.runtime.runtimeGetVersion()
        major = cuda_version // 1000
        minor = (cuda_version % 1000) // 10
        print(f"✓ CUDA runtime: {major}.{minor}")

        # Test basic GPU operation
        test_arr = cp.array([1, 2, 3, 4, 5])
        result = cp.sum(test_arr)
        print(f"✓ GPU computation test: sum([1,2,3,4,5]) = {result}")

    except ImportError:
        print("✗ CuPy not installed")
        return False
    except Exception as e:
        print(f"✗ CUDA test failed: {e}")
        return False

    # Test cuda_hash module detection
    available = has_cuda_available()
    print(f"\n{'✓' if available else '✗'} cuda_hash.has_cuda_available(): {available}")

    return available


def test_md5_calculation():
    """Test 2: MD5 Calculation"""
    print("\n" + "=" * 70)
    print("TEST 2: MD5 CALCULATION")
    print("=" * 70)

    # Create test file
    test_data = b"MediaVault GPU Test Data - " + os.urandom(1024 * 100)  # 100KB

    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
        f.write(test_data)
        test_file = f.name

    try:
        # Test MD5 calculation
        print(f"Test file: {test_file}")
        print(f"File size: {len(test_data)} bytes")

        md5_hash = calculate_md5(test_file, prefer_gpu=True)
        print(f"\n✓ MD5 Hash: {md5_hash}")

        # Verify hash is valid (32 hex characters)
        is_valid = len(md5_hash) == 32 and all(c in '0123456789abcdef' for c in md5_hash)
        print(f"{'✓' if is_valid else '✗'} Hash format valid: {is_valid}")

        return is_valid

    finally:
        os.unlink(test_file)


def test_ffmpeg_service_integration():
    """Test 3: FFmpeg Service Integration"""
    print("\n" + "=" * 70)
    print("TEST 3: FFMPEG SERVICE INTEGRATION")
    print("=" * 70)

    # Create test video file
    test_data = b"FAKE_VIDEO_DATA_" + os.urandom(1024 * 50)  # 50KB

    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.mp4') as f:
        f.write(test_data)
        test_file = f.name

    try:
        print(f"Test file: {test_file}")

        # Initialize FFmpeg service
        ffmpeg = FFmpegService()
        print("✓ FFmpegService initialized")

        # Test MD5 calculation through FFmpeg service
        md5_hash = ffmpeg.calculate_md5(test_file)

        if md5_hash:
            print(f"✓ MD5 via FFmpegService: {md5_hash}")
            return True
        else:
            print("✗ MD5 calculation failed")
            return False

    finally:
        os.unlink(test_file)


def test_cpu_fallback():
    """Test 4: CPU Fallback"""
    print("\n" + "=" * 70)
    print("TEST 4: CPU FALLBACK MECHANISM")
    print("=" * 70)

    from services.cuda_hash import calculate_md5_cpu

    test_data = b"CPU fallback test data"

    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
        f.write(test_data)
        test_file = f.name

    try:
        # Test CPU-only calculation
        cpu_hash = calculate_md5_cpu(test_file)
        print(f"✓ CPU MD5: {cpu_hash}")

        # Test automatic calculation (should match CPU)
        auto_hash = calculate_md5(test_file, prefer_gpu=True)
        print(f"✓ Auto MD5: {auto_hash}")

        if cpu_hash == auto_hash:
            print("✓ CPU and Auto hashes match")
            return True
        else:
            print("✗ Hash mismatch!")
            return False

    finally:
        os.unlink(test_file)


def print_system_info():
    """Print system information"""
    print("\n" + "=" * 70)
    print("SYSTEM INFORMATION")
    print("=" * 70)

    # Python version
    print(f"Python: {sys.version.split()[0]}")

    # Try to get GPU info
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                               '--format=csv,noheader'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            info = result.stdout.strip().split(', ')
            print(f"GPU: {info[0]}")
            print(f"Driver: {info[1]}")
            print(f"Memory: {info[2]}")
    except Exception:
        print("GPU: Unable to query (nvidia-smi not available)")

    # CuPy info
    try:
        import cupy as cp
        print(f"CuPy: {cp.__version__}")
    except ImportError:
        print("CuPy: Not installed")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("MEDIAVAULT GPU MD5 INTEGRATION TEST SUITE")
    print("=" * 70)

    print_system_info()

    # Run tests
    results = {
        "CUDA Detection": test_cuda_detection(),
        "MD5 Calculation": test_md5_calculation(),
        "FFmpeg Integration": test_ffmpeg_service_integration(),
        "CPU Fallback": test_cpu_fallback(),
    }

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {test_name}")

    all_passed = all(results.values())
    print("\n" + "=" * 70)

    if all_passed:
        print("✓ ALL TESTS PASSED - GPU MD5 INTEGRATION READY")
    else:
        print("✗ SOME TESTS FAILED - CHECK ERRORS ABOVE")

    print("=" * 70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
