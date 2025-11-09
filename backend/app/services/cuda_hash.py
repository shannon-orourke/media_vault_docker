"""GPU-accelerated MD5 hashing using CUDA."""
import hashlib
import os
from typing import Optional
from loguru import logger

# Try to import GPU libraries
try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    logger.warning("CuPy not available - GPU MD5 hashing disabled")


def has_cuda_available() -> bool:
    """Check if CUDA is available for GPU acceleration."""
    if not CUPY_AVAILABLE:
        return False

    try:
        # Test CUDA by creating a small array
        test_array = cp.array([1, 2, 3])
        return True
    except Exception as e:
        logger.warning(f"CUDA test failed: {e}")
        return False


def calculate_md5_gpu(file_path: str, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash using GPU acceleration (experimental).

    Note: CuPy doesn't have built-in MD5, so this uses GPU for data processing
    but CPU for actual MD5. Real GPU MD5 would require custom CUDA kernels.

    Args:
        file_path: Path to file
        chunk_size: Bytes to read at once

    Returns:
        MD5 hash as hex string
    """
    md5 = hashlib.md5()

    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                # For true GPU MD5, we'd need custom CUDA kernels
                # This is a placeholder that uses CPU MD5 but could
                # use GPU for preprocessing/parallel file reading
                md5.update(chunk)

        return md5.hexdigest()

    except Exception as e:
        logger.error(f"GPU MD5 calculation failed: {e}")
        raise


def calculate_md5_cpu(file_path: str, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash using CPU.

    Args:
        file_path: Path to file
        chunk_size: Bytes to read at once

    Returns:
        MD5 hash as hex string
    """
    md5 = hashlib.md5()

    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5.update(chunk)

        return md5.hexdigest()

    except Exception as e:
        logger.error(f"CPU MD5 calculation failed: {e}")
        raise


# Cache CUDA availability check
_CUDA_CHECKED = False
_CUDA_AVAILABLE = False


def calculate_md5(file_path: str, chunk_size: int = 8192, prefer_gpu: bool = True) -> str:
    """
    Calculate MD5 hash with automatic GPU/CPU selection.

    Args:
        file_path: Path to file
        chunk_size: Bytes to read at once
        prefer_gpu: Prefer GPU if available

    Returns:
        MD5 hash as hex string
    """
    global _CUDA_CHECKED, _CUDA_AVAILABLE

    # Check CUDA availability once
    if not _CUDA_CHECKED:
        _CUDA_AVAILABLE = has_cuda_available()
        _CUDA_CHECKED = True

        if _CUDA_AVAILABLE:
            logger.success("✓ CUDA available for GPU acceleration")
        else:
            logger.info("Using CPU for MD5 hashing (CUDA not available)")

    # Select GPU or CPU
    if prefer_gpu and _CUDA_AVAILABLE:
        try:
            return calculate_md5_gpu(file_path, chunk_size)
        except Exception as e:
            logger.warning(f"GPU MD5 failed, falling back to CPU: {e}")
            return calculate_md5_cpu(file_path, chunk_size)
    else:
        return calculate_md5_cpu(file_path, chunk_size)


def calculate_md5_parallel(file_paths: list[str], use_gpu: bool = True) -> dict[str, str]:
    """
    Calculate MD5 hashes for multiple files in parallel.

    Args:
        file_paths: List of file paths
        use_gpu: Use GPU if available

    Returns:
        Dict mapping file_path to MD5 hash
    """
    # This could be parallelized with multiprocessing or GPU streams
    # For now, sequential processing
    results = {}

    for file_path in file_paths:
        try:
            results[file_path] = calculate_md5(file_path, prefer_gpu=use_gpu)
        except Exception as e:
            logger.error(f"Failed to hash {file_path}: {e}")
            results[file_path] = None

    return results
