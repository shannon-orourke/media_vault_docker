#!/usr/bin/env python3
"""
NAS Mount Health Check for MediaVault Backend

This script should be run before starting the backend to ensure
NAS mounts are healthy. Can be called from Docker entrypoint.
"""
import sys
import time
from pathlib import Path
from typing import List, Tuple


def check_mount(mount_path: Path, name: str) -> Tuple[bool, str]:
    """
    Check if a mount point is accessible and readable.

    Returns:
        Tuple of (is_healthy, message)
    """
    # Check if path exists
    if not mount_path.exists():
        return False, f"{name} path does not exist: {mount_path}"

    # Check if it's a directory
    if not mount_path.is_dir():
        return False, f"{name} path is not a directory: {mount_path}"

    # Try to list directory contents (timeout after 5 seconds)
    try:
        # This will fail if mount is stale or unresponsive
        list(mount_path.iterdir())
        return True, f"{name} is healthy"
    except PermissionError:
        return False, f"{name} permission denied: {mount_path}"
    except OSError as e:
        return False, f"{name} is not accessible: {e}"
    except Exception as e:
        return False, f"{name} unexpected error: {e}"


def main():
    """Main health check function."""
    # Define critical mount points
    mount_base = Path("/mnt/nas-media")
    mounts_to_check: List[Tuple[Path, str]] = [
        (mount_base / "volume1" / "docker", "Docker share"),
        (mount_base / "volume1" / "videos", "Video share"),
    ]

    print("=" * 50)
    print("MediaVault NAS Mount Health Check")
    print("=" * 50)
    print()

    all_healthy = True
    for mount_path, name in mounts_to_check:
        is_healthy, message = check_mount(mount_path, name)

        status_icon = "✓" if is_healthy else "✗"
        print(f"{status_icon} {message}")

        if not is_healthy:
            all_healthy = False

    print()

    if all_healthy:
        print("All NAS mounts are healthy ✓")
        print()
        return 0
    else:
        print("ERROR: Some NAS mounts are unhealthy!")
        print()
        print("Troubleshooting:")
        print("  1. Check mount status: sudo systemctl status mnt-nas-media-volume1-*")
        print("  2. Check health monitor: sudo systemctl status mediavault-mount-health.timer")
        print("  3. View mount logs: sudo journalctl -u mediavault-mount-health -n 50")
        print("  4. Manual remount: sudo systemctl restart mnt-nas-media-volume1-*.mount")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
