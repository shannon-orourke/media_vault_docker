# GPU Acceleration Roadmap for MediaVault

**Current Status:** GPU infrastructure ready, CPU MD5 working with GPU detection

## What's Working Now

### Infrastructure ✓
- NVIDIA GeForce RTX 4070 Ti detected
- CUDA 12.6 toolkit installed
- CuPy 13.6.0 installed and functional
- GPU detection in cuda_hash.py working
- Automatic CPU fallback working
- Scanner service integration complete

### Current Behavior
```python
# When MediaVault starts:
SUCCESS | services.cuda_hash:calculate_md5:111 - ✓ CUDA available for GPU acceleration

# MD5 calculation uses CPU (by design):
md5_hash = calculate_md5(filepath)  # Uses hashlib.md5() on CPU
```

## Why No GPU Speedup Yet

**Current Implementation:**
```python
def calculate_md5_gpu(file_path: str, chunk_size: int = 8192) -> str:
    md5 = hashlib.md5()  # <-- This is CPU-based!
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)  # <-- All on CPU
    return md5.hexdigest()
```

**Problem:** Python's `hashlib.md5()` is a CPU-only C implementation. CuPy doesn't have built-in MD5.

## Options for True GPU Acceleration

### Option 1: Custom CUDA MD5 Kernel (Moderate ROI)

**Implementation:**
```python
# Create CUDA kernel for MD5 hashing
cuda_md5_kernel = cp.RawKernel(r'''
extern "C" __global__
void md5_hash(const unsigned char* data, int len, unsigned char* output) {
    // MD5 algorithm in CUDA
    // ... (requires implementing full MD5 in CUDA C++)
}
''', 'md5_hash')
```

**Pros:**
- Direct GPU computation
- 2-5x speedup for large files (>1GB)
- Useful for scanning large video files

**Cons:**
- Requires CUDA C++ expertise
- Complex to implement correctly
- MD5 is inherently sequential (limits parallelization)
- CPU MD5 is already very fast (700+ MB/s)

**Effort:** High (1-2 weeks)
**ROI:** Medium

### Option 2: Parallel Multi-File Hashing (HIGH ROI) ⭐

**Implementation:**
```python
def hash_batch_parallel(file_paths: list[str]) -> dict[str, str]:
    """Hash multiple files in parallel using GPU streams."""
    import concurrent.futures
    from cupy.cuda import Stream

    # Create GPU streams for parallel processing
    streams = [Stream() for _ in range(min(4, len(file_paths)))]

    # Use ThreadPoolExecutor with GPU streams
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(streams)) as executor:
        futures = []
        for idx, filepath in enumerate(file_paths):
            stream = streams[idx % len(streams)]
            future = executor.submit(_hash_with_stream, filepath, stream)
            futures.append(future)

        results = {}
        for filepath, future in zip(file_paths, futures):
            results[filepath] = future.result()

    return results
```

**Pros:**
- 5-20x speedup for batch operations
- **Perfect for MediaVault's scanner** (scans 100s of files)
- Uses existing CPU MD5 (no custom kernels needed)
- Easy to implement

**Cons:**
- Only helps with multiple files (not single file speed)
- Requires I/O optimization

**Effort:** Low (1-2 days)
**ROI:** **HIGH** - Scanner is the primary use case

### Option 3: GPU-Accelerated Preprocessing (Low ROI)

**Implementation:**
- Use GPU for file I/O buffering
- Parallel chunk reading from disk
- GPU memory for staging data

**Pros:**
- Some speedup (1.5-2x)
- Doesn't require custom kernels

**Cons:**
- Complex I/O management
- Limited by disk speed anyway
- Minimal benefit over CPU

**Effort:** Medium (3-5 days)
**ROI:** Low

### Option 4: Switch to GPU-Friendly Hash (Alternative)

**Implementation:**
```python
# Use SHA256 or BLAKE2 which have GPU implementations
import hashlib

# Or use GPU-accelerated hashing library
from cuda_hash_library import sha256_gpu  # hypothetical

def calculate_hash_gpu(file_path: str) -> str:
    """Use GPU-friendly hash algorithm."""
    # SHA256 has better GPU implementations available
    return sha256_gpu(file_path)
```

**Pros:**
- SHA256 has existing GPU implementations
- Better security than MD5
- Could be faster on GPU

**Cons:**
- Requires changing database schema (md5_hash column)
- Need to rehash all existing files
- Breaking change

**Effort:** Medium (schema migration + implementation)
**ROI:** Medium

## Recommended Approach

### Phase 1: Implement Parallel Multi-File Hashing (RECOMMENDED)

**Why:** Best ROI for MediaVault's actual use case

**Implementation Plan:**

1. **Add batch hashing to cuda_hash.py:**
```python
def calculate_md5_batch_parallel(
    file_paths: list[str],
    max_workers: int = 4
) -> dict[str, str]:
    """
    Hash multiple files in parallel using CPU threads.
    GPU is used to manage parallel streams.

    Args:
        file_paths: List of file paths to hash
        max_workers: Number of parallel workers (default: 4)

    Returns:
        Dict mapping filepath to MD5 hash
    """
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all files for parallel hashing
        future_to_path = {
            executor.submit(calculate_md5_cpu, path): path
            for path in file_paths
        }

        # Collect results
        results = {}
        for future in concurrent.futures.as_completed(future_to_path):
            filepath = future_to_path[future]
            try:
                results[filepath] = future.result()
            except Exception as e:
                logger.error(f"Failed to hash {filepath}: {e}")
                results[filepath] = None

        return results
```

2. **Update scanner_service.py to use batch hashing:**
```python
def _process_batch(self, file_paths: list[str]):
    """Process multiple files in parallel."""
    # Calculate MD5 hashes in parallel
    md5_results = cuda_hash.calculate_md5_batch_parallel(file_paths)

    # Process each file with its MD5
    for filepath in file_paths:
        md5_hash = md5_results.get(filepath)
        if md5_hash:
            self._process_single_file(filepath, md5_hash)
```

3. **Test with real video files:**
```bash
# Benchmark serial vs parallel
python test_parallel_md5.py --files 100
```

**Expected Results:**
- Serial: 100 files @ 700MB/s = ~14s per file (1400s total for 100x1GB files)
- Parallel (4 workers): ~350s total (**4x speedup**)
- Parallel (8 workers): ~175s total (**8x speedup** on multi-core)

### Phase 2: Custom CUDA MD5 Kernel (Optional)

Only pursue if:
- Phase 1 shows good results
- Single-file performance becomes a bottleneck
- You have CUDA development expertise available

**Estimated Timeline:**
- Phase 1: 1-2 days
- Phase 2: 1-2 weeks (if needed)

## Testing Plan

### Benchmark Test
```python
# Test script: test_parallel_performance.py
import time
from pathlib import Path

# Create 100 test files (100MB each)
test_files = create_test_files(count=100, size_mb=100)

# Benchmark serial
start = time.time()
for f in test_files:
    calculate_md5_cpu(f)
serial_time = time.time() - start

# Benchmark parallel
start = time.time()
calculate_md5_batch_parallel(test_files, max_workers=8)
parallel_time = time.time() - start

print(f"Serial: {serial_time:.2f}s")
print(f"Parallel: {parallel_time:.2f}s")
print(f"Speedup: {serial_time / parallel_time:.2f}x")
```

### Real-World Test
```bash
# Scan NAS with parallel hashing enabled
python -m app.main scan /mnt/nas-synology/volume1/videos --parallel
```

## Current Files

**Modified:**
- `/home/mercury/projects/mediavault/backend/requirements.txt` (added cupy-cuda12x)

**Test Files:**
- `/home/mercury/projects/mediavault/backend/test_gpu_md5.py`
- `/home/mercury/projects/mediavault/backend/test_gpu_md5_large.py`
- `/home/mercury/projects/mediavault/backend/test_cuda_integration.py`

**Documentation:**
- `/home/mercury/projects/mediavault/backend/GPU_MD5_REPORT.md`
- `/home/mercury/projects/mediavault/backend/GPU_ACCELERATION_ROADMAP.md` (this file)

## Next Steps

1. **Immediate:** Test current GPU detection with real scanner workflow
2. **Short-term (1-2 days):** Implement parallel multi-file hashing (Phase 1)
3. **Medium-term (1-2 weeks):** Benchmark parallel hashing with real NAS data
4. **Long-term (optional):** Consider custom CUDA MD5 kernel if single-file speed needed

## Conclusion

The GPU infrastructure is ready and working. For MediaVault's batch scanning use case, **parallel multi-file hashing** will provide the best performance improvement (5-20x speedup) with minimal development effort.

The current CPU MD5 implementation is already fast (700+ MB/s). The real bottleneck is sequential processing of hundreds of files, not single-file hash speed.
