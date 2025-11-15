"""HLS (HTTP Live Streaming) service with GPU-accelerated transcoding."""
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, List
from loguru import logger
import time
import threading

from app.config import get_settings

settings = get_settings()


class HLSService:
    """Service for generating HLS adaptive streaming segments with GPU acceleration."""

    def __init__(self):
        self.ffmpeg_path = settings.ffmpeg_path
        self.hls_output_dir = Path("/tmp/mediavault_hls")
        self.hls_output_dir.mkdir(exist_ok=True)

        # Cache to track active generation sessions
        self._generating = {}  # file_id -> thread
        self._generation_lock = threading.Lock()

    def get_hls_directory(self, file_id: int) -> Path:
        """Get HLS output directory for a specific file."""
        output_dir = self.hls_output_dir / str(file_id)
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def is_hls_ready(self, file_id: int) -> bool:
        """
        Check if HLS segments have been generated for this file.

        Returns:
            True if master playlist exists
        """
        master_playlist = self.get_hls_directory(file_id) / "master.m3u8"
        return master_playlist.exists()

    def is_generating(self, file_id: int) -> bool:
        """Check if HLS generation is currently in progress."""
        with self._generation_lock:
            return file_id in self._generating

    def generate_hls_adaptive(
        self,
        input_path: str,
        file_id: int,
        qualities: Optional[List[Dict]] = None,
        use_gpu: bool = True
    ) -> bool:
        """
        Generate HLS adaptive streaming with multiple quality levels using GPU.

        Creates master playlist and quality-specific playlists with segments.

        Args:
            input_path: Source video file path
            file_id: Media file ID (used for output directory)
            qualities: List of quality settings (default: 480p, 720p, 1080p)
            use_gpu: Use GPU acceleration (NVENC)

        Returns:
            True if generation successful
        """
        # Default quality levels for adaptive streaming
        if qualities is None:
            qualities = [
                {"name": "480p", "width": 854, "height": 480, "bitrate": "2000k"},
                {"name": "720p", "width": 1280, "height": 720, "bitrate": "4000k"},
                {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "8000k"},
            ]

        output_dir = self.get_hls_directory(file_id)

        # Mark as generating
        with self._generation_lock:
            if file_id in self._generating:
                logger.warning(f"HLS generation already in progress for file {file_id}")
                return False
            self._generating[file_id] = threading.current_thread()

        try:
            # Build complex FFmpeg command for multi-quality HLS
            cmd = self._build_hls_command(
                input_path=input_path,
                output_dir=output_dir,
                qualities=qualities,
                use_gpu=use_gpu
            )

            logger.info(f"Starting HLS generation for file {file_id} ({len(qualities)} qualities)")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            # Run FFmpeg
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600  # 10 minute timeout
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                logger.success(f"HLS generation complete for file {file_id} in {elapsed:.1f}s")
                return True
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"HLS generation failed for file {file_id}: {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"HLS generation timeout for file {file_id}")
            return False
        except Exception as e:
            logger.error(f"HLS generation error for file {file_id}: {e}")
            return False
        finally:
            # Remove from generating set
            with self._generation_lock:
                self._generating.pop(file_id, None)

    def _build_hls_command(
        self,
        input_path: str,
        output_dir: Path,
        qualities: List[Dict],
        use_gpu: bool
    ) -> List[str]:
        """
        Build FFmpeg command for multi-quality HLS generation.

        Uses GPU acceleration for multiple quality encodes simultaneously.
        """
        cmd = [self.ffmpeg_path, "-y"]

        # Input with hardware acceleration
        if use_gpu:
            cmd.extend([
                "-hwaccel", "cuda",
                "-hwaccel_output_format", "cuda"
            ])

        cmd.extend(["-i", input_path])

        # Map streams for each quality
        for idx, quality in enumerate(qualities):
            # Video mapping
            cmd.extend(["-map", "0:v:0"])
            # Audio mapping
            cmd.extend(["-map", "0:a:0"])

        # Encode each quality
        for idx, quality in enumerate(qualities):
            # Video encoding
            if use_gpu:
                cmd.extend([
                    f"-c:v:{idx}", "h264_nvenc",
                    f"-preset:v:{idx}", "p4",  # NVENC preset (p1=fastest, p7=best)
                    f"-b:v:{idx}", quality["bitrate"],
                    f"-maxrate:v:{idx}", quality["bitrate"],
                    f"-bufsize:v:{idx}", str(int(quality["bitrate"].replace("k", "")) * 2) + "k",
                    f"-vf:v:{idx}", f"scale_cuda={quality['width']}:{quality['height']}",
                    f"-g:v:{idx}", "48",  # Keyframe interval (2 seconds @ 24fps)
                ])
            else:
                # CPU fallback
                cmd.extend([
                    f"-c:v:{idx}", "libx264",
                    f"-preset:v:{idx}", "medium",
                    f"-b:v:{idx}", quality["bitrate"],
                    f"-maxrate:v:{idx}", quality["bitrate"],
                    f"-bufsize:v:{idx}", str(int(quality["bitrate"].replace("k", "")) * 2) + "k",
                    f"-vf:v:{idx}", f"scale={quality['width']}:{quality['height']}",
                    f"-g:v:{idx}", "48",
                ])

            # Audio encoding (AAC for all qualities)
            cmd.extend([
                f"-c:a:{idx}", "aac",
                f"-b:a:{idx}", "128k",
                f"-ar:a:{idx}", "48000",
                f"-ac:a:{idx}", "2",  # Stereo
            ])

        # HLS settings
        cmd.extend([
            "-f", "hls",
            "-hls_time", "4",  # 4-second segments
            "-hls_list_size", "0",  # Keep all segments
            "-hls_segment_type", "mpegts",
            "-hls_flags", "independent_segments+program_date_time",
        ])

        # Variant streams for adaptive streaming
        var_stream_map = []
        for idx, quality in enumerate(qualities):
            quality_dir = output_dir / quality["name"]
            quality_dir.mkdir(exist_ok=True)

            var_stream_map.append(f"v:{idx},a:{idx},name:{quality['name']}")

            cmd.extend([
                f"-hls_segment_filename", str(quality_dir / "segment_%03d.ts"),
            ])

        # Master playlist
        cmd.extend([
            "-var_stream_map", " ".join(var_stream_map),
            "-master_pl_name", "master.m3u8",
            str(output_dir / "%v/playlist.m3u8")
        ])

        return cmd

    def cleanup_old_segments(self, max_age_hours: int = 1, max_total_gb: float = 10.0):
        """
        Clean up old HLS segments to save disk space.

        Args:
            max_age_hours: Remove segments older than this (default: 1 hour)
            max_total_gb: Maximum total HLS storage (default: 10GB)
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            max_bytes = max_total_gb * 1024 * 1024 * 1024

            # Collect all file info
            files_info = []
            total_size = 0

            for file_dir in self.hls_output_dir.iterdir():
                if not file_dir.is_dir():
                    continue

                for filepath in file_dir.rglob("*"):
                    if filepath.is_file():
                        stat = filepath.stat()
                        files_info.append({
                            "path": filepath,
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "age": current_time - stat.st_mtime
                        })
                        total_size += stat.st_size

            # Sort by modification time (oldest first)
            files_info.sort(key=lambda x: x["mtime"])

            deleted_count = 0
            freed_bytes = 0

            # Remove old files
            for file_info in files_info:
                should_delete = False

                # Delete if too old
                if file_info["age"] > max_age_seconds:
                    should_delete = True

                # Delete oldest files if over size limit
                if total_size > max_bytes:
                    should_delete = True
                    total_size -= file_info["size"]

                if should_delete:
                    try:
                        file_info["path"].unlink()
                        deleted_count += 1
                        freed_bytes += file_info["size"]
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_info['path']}: {e}")

            # Remove empty directories
            for file_dir in self.hls_output_dir.iterdir():
                if file_dir.is_dir():
                    try:
                        # Remove empty quality subdirectories
                        for subdir in file_dir.iterdir():
                            if subdir.is_dir() and not any(subdir.iterdir()):
                                subdir.rmdir()

                        # Remove empty file directory
                        if not any(file_dir.iterdir()):
                            file_dir.rmdir()
                    except Exception:
                        pass

            if deleted_count > 0:
                logger.info(f"HLS cleanup: deleted {deleted_count} files, freed {freed_bytes / 1024 / 1024:.1f}MB")

        except Exception as e:
            logger.error(f"HLS cleanup error: {e}")

    def get_segment_file(self, file_id: int, quality: str, segment: str) -> Optional[Path]:
        """
        Get path to HLS segment file.

        Args:
            file_id: Media file ID
            quality: Quality level (480p, 720p, 1080p)
            segment: Segment filename

        Returns:
            Path to segment file or None if not found
        """
        segment_path = self.get_hls_directory(file_id) / quality / segment

        if segment_path.exists() and segment_path.is_file():
            return segment_path

        return None

    def get_playlist_file(self, file_id: int, quality: Optional[str] = None) -> Optional[Path]:
        """
        Get path to HLS playlist file.

        Args:
            file_id: Media file ID
            quality: Quality level (or None for master playlist)

        Returns:
            Path to playlist file or None if not found
        """
        if quality is None:
            # Master playlist
            playlist_path = self.get_hls_directory(file_id) / "master.m3u8"
        else:
            # Quality-specific playlist
            playlist_path = self.get_hls_directory(file_id) / quality / "playlist.m3u8"

        if playlist_path.exists() and playlist_path.is_file():
            return playlist_path

        return None
