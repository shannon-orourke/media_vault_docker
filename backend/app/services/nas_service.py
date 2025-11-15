"""NAS/SMB storage service for mounting and file operations."""
import os
import subprocess
from typing import Tuple, Optional
from loguru import logger

from app.config import get_settings

settings = get_settings()


class NASService:
    """Service for managing NAS/SMB storage connections."""

    def __init__(self):
        self.is_mounted = False
        self.mount_point = settings.nas_mount_path
        self.nas_host = settings.nas_host

    def check_cifs_utils_installed(self) -> bool:
        """Check if cifs-utils is installed."""
        try:
            result = subprocess.run(
                ["which", "mount.cifs"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking cifs-utils: {e}")
            return False

    def install_cifs_utils(self) -> Tuple[bool, str]:
        """Attempt to install cifs-utils (requires sudo)."""
        try:
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "cifs-utils"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return True, "cifs-utils installed successfully"
            else:
                return False, f"Installation failed: {result.stderr}"
        except Exception as e:
            return False, f"Installation error: {str(e)}"

    def ensure_mount_point_exists(self, mount_point: str) -> bool:
        """Create mount point directory if it doesn't exist."""
        try:
            if not os.path.exists(mount_point):
                os.makedirs(mount_point, mode=0o755, exist_ok=True)
                logger.info(f"Created mount point: {mount_point}")
            return True
        except Exception as e:
            logger.error(f"Failed to create mount point {mount_point}: {e}")
            return False

    def is_mount_active(self, mount_point: Optional[str] = None) -> bool:
        """Check if mount point is currently mounted."""
        if mount_point is None:
            mount_point = self.mount_point

        try:
            # Check if the mount_point itself is a mountpoint
            result = subprocess.run(
                ["mountpoint", "-q", mount_point],
                timeout=5
            )
            if result.returncode == 0:
                self.is_mounted = True
                return True

            # If parent is not a mountpoint, check if volume subdirectories are mounted
            # This handles the case where individual volumes are mounted separately
            volume_paths = [
                os.path.join(mount_point, "volume1", "docker"),
                os.path.join(mount_point, "volume1", "videos")
            ]

            for vol_path in volume_paths:
                if os.path.exists(vol_path) and os.path.isdir(vol_path):
                    # Check if this is a mountpoint or if we can access it
                    try:
                        os.listdir(vol_path)
                        self.is_mounted = True
                        logger.debug(f"NAS mount detected via accessible path: {vol_path}")
                        return True
                    except (PermissionError, OSError):
                        continue

            self.is_mounted = False
            return False
        except Exception as e:
            logger.error(f"Error checking mount status: {e}")
            return False

    def mount_smb_share(
        self,
        host: Optional[str] = None,
        share: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        mount_point: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Mount SMB share using cifs-utils.

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Use settings defaults if not provided
        host = host or settings.nas_host
        share = share or settings.nas_smb_share
        username = username or settings.nas_smb_username
        password = password or settings.nas_smb_password
        mount_point = mount_point or self.mount_point

        # Check if already mounted
        if self.is_mount_active(mount_point):
            logger.info(f"Already mounted at {mount_point}")
            return True, f"Already mounted at {mount_point}"

        # Check/install cifs-utils
        if not self.check_cifs_utils_installed():
            logger.warning("cifs-utils not found, attempting to install...")
            success, msg = self.install_cifs_utils()
            if not success:
                return False, f"cifs-utils not available: {msg}"

        # Create mount point
        if not self.ensure_mount_point_exists(mount_point):
            return False, f"Failed to create mount point: {mount_point}"

        # Build mount command
        smb_path = f"//{host}/{share}"
        mount_options = (
            f"username={username},"
            f"password={password},"
            f"uid={os.getuid()},"
            f"gid={os.getgid()},"
            f"file_mode=0644,"
            f"dir_mode=0755"
        )

        mount_cmd = [
            "sudo", "mount", "-t", "cifs",
            smb_path,
            mount_point,
            "-o", mount_options
        ]

        # Execute mount
        try:
            logger.info(f"Mounting {smb_path} to {mount_point}...")
            result = subprocess.run(
                mount_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.is_mounted = True
                logger.success(f"✓ Mounted {smb_path} to {mount_point}")
                return True, f"Mounted {smb_path} to {mount_point}"
            else:
                error = result.stderr or result.stdout
                logger.error(f"✗ Mount failed: {error}")
                return False, f"Mount failed: {error}"

        except subprocess.TimeoutExpired:
            return False, "Mount operation timed out"
        except Exception as e:
            logger.error(f"Mount exception: {e}")
            return False, f"Mount exception: {str(e)}"

    def unmount_smb_share(self, mount_point: Optional[str] = None) -> Tuple[bool, str]:
        """Unmount SMB share."""
        mount_point = mount_point or self.mount_point

        if not self.is_mount_active(mount_point):
            return True, "Not mounted"

        try:
            logger.info(f"Unmounting {mount_point}...")
            result = subprocess.run(
                ["sudo", "umount", mount_point],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.is_mounted = False
                logger.success(f"✓ Unmounted {mount_point}")
                return True, f"Unmounted {mount_point}"
            else:
                error = result.stderr or result.stdout
                logger.error(f"✗ Unmount failed: {error}")
                return False, f"Unmount failed: {error}"

        except Exception as e:
            logger.error(f"Unmount exception: {e}")
            return False, f"Unmount exception: {str(e)}"

    def get_effective_path(
        self,
        relative_path: str,
        use_nas: bool = True
    ) -> str:
        """
        Get effective path based on NAS mount status.

        Args:
            relative_path: Path relative to NAS root (e.g., "/volume1/videos")
            use_nas: Whether to use NAS path or fallback to local

        Returns:
            Full path to use
        """
        if use_nas and self.is_mount_active():
            # Strip leading slash from relative_path if present
            rel_path = relative_path.lstrip("/")
            return os.path.join(self.mount_point, rel_path)
        else:
            # Fallback to treating as local path
            return relative_path

    def list_files(
        self,
        path: str,
        recursive: bool = False,
        extensions: Optional[list] = None
    ) -> list:
        """
        List files in a directory.

        Args:
            path: Directory path to list
            recursive: Whether to recurse into subdirectories
            extensions: List of file extensions to filter (e.g., ['.mkv', '.mp4'])

        Returns:
            List of file paths
        """
        files = []

        # Patterns to exclude (TypeScript files, node_modules, etc.)
        exclude_patterns = [
            '/node_modules/',
            '/.git/',
            '/.venv/',
            '/dist/',
            '/build/',
            '.d.ts',  # TypeScript definition files
            '.test.ts',  # TypeScript test files
            '.spec.ts',  # TypeScript spec files
        ]

        try:
            if recursive:
                for root, dirs, filenames in os.walk(path):
                    # Skip excluded directories
                    dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '.venv', 'dist', 'build', '__pycache__']]

                    for filename in filenames:
                        full_path = os.path.join(root, filename)

                        # Check if path matches any exclude pattern
                        if any(pattern in full_path for pattern in exclude_patterns):
                            continue

                        # Check if it's a TypeScript source file (but not MPEG-TS video)
                        if filename.endswith('.ts') and not self._is_likely_video_ts(full_path):
                            continue

                        if extensions is None or any(filename.lower().endswith(ext) for ext in extensions):
                            files.append(full_path)
            else:
                for filename in os.listdir(path):
                    full_path = os.path.join(path, filename)
                    if os.path.isfile(full_path):
                        # Check if path matches any exclude pattern
                        if any(pattern in full_path for pattern in exclude_patterns):
                            continue

                        # Check if it's a TypeScript source file (but not MPEG-TS video)
                        if filename.endswith('.ts') and not self._is_likely_video_ts(full_path):
                            continue

                        if extensions is None or any(filename.lower().endswith(ext) for ext in extensions):
                            files.append(full_path)

            return files

        except Exception as e:
            logger.error(f"Error listing files in {path}: {e}")
            return []

    def _is_likely_video_ts(self, filepath: str) -> bool:
        """
        Check if a .ts file is likely a video transport stream vs TypeScript source.

        Args:
            filepath: Path to the .ts file

        Returns:
            True if likely a video file, False if likely TypeScript
        """
        # TypeScript files are usually small (<10MB) and in source directories
        try:
            file_size = os.path.getsize(filepath)

            # TypeScript files are typically very small
            if file_size < 10 * 1024 * 1024:  # Less than 10MB
                return False

            # If in typical video directories, likely a video
            video_keywords = ['/videos/', '/movies/', '/tv/', '/media/', '/downloads/']
            if any(keyword in filepath.lower() for keyword in video_keywords):
                return True

            # If in typical source directories, definitely not a video
            source_keywords = ['/src/', '/lib/', '/types/', '/frontend/', '/backend/', '/node_modules/']
            if any(keyword in filepath.lower() for keyword in source_keywords):
                return False

            # Large files are more likely to be videos
            return file_size > 10 * 1024 * 1024  # Greater than 10MB

        except Exception:
            # If we can't check, assume it's TypeScript to be safe
            return False

    def get_file_info(self, filepath: str) -> Optional[dict]:
        """Get basic file information."""
        try:
            stat = os.stat(filepath)
            return {
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "file_size": stat.st_size,
                "modified_at": stat.st_mtime,
                "created_at": stat.st_ctime,
            }
        except Exception as e:
            logger.error(f"Error getting file info for {filepath}: {e}")
            return None
