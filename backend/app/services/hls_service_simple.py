"""Simplified HLS service for testing - single quality only."""
import subprocess
import os
from pathlib import Path
from typing import Optional
from loguru import logger
import time
import threading

from app.config import get_settings

settings = get_settings()


class HLSServiceSimple:
    """Simplified HLS service - single quality for testing."""

    def __init__(self):
        self.ffmpeg_path = settings.ffmpeg_path
        self.hls_output_dir = Path("/tmp/mediavault_hls")
        self.hls_output_dir.mkdir(exist_ok=True)
        self._generating = {}
        self._generation_lock = threading.Lock()

    def get_hls_directory(self, file_id: int) -> Path:
        output_dir = self.hls_output_dir / str(file_id)
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def is_hls_ready(self, file_id: int) -> bool:
        master_playlist = self.get_hls_directory(file_id) / "playlist.m3u8"
        return master_playlist.exists()

    def is_generating(self, file_id: int) -> bool:
        with self._generation_lock:
            return file_id in self._generating

    def generate_hls_simple(
        self,
        input_path: str,
        file_id: int,
        width: int = 1280,
        height: int = 720,
        bitrate: str = "4000k",
        use_gpu: bool = True
    ) -> bool:
        """Generate simple single-quality HLS stream."""

        output_dir = self.get_hls_directory(file_id)

        with self._generation_lock:
            if file_id in self._generating:
                return False
            self._generating[file_id] = threading.current_thread()

        try:
            # Simple HLS command
            cmd = [
                self.ffmpeg_path,
                "-y",
            ]

            if use_gpu:
                cmd.extend([
                    "-hwaccel", "cuda",
                    "-hwaccel_output_format", "cuda",
                ])

            cmd.extend([
                "-i", input_path,
            ])

            if use_gpu:
                cmd.extend([
                    "-vf", f"scale_cuda={width}:{height}",
                    "-c:v", "h264_nvenc",
                    "-preset", "p4",
                ])
            else:
                cmd.extend([
                    "-vf", f"scale={width}:{height}",
                    "-c:v", "libx264",
                    "-preset", "medium",
                ])

            cmd.extend([
                "-b:v", bitrate,
                "-maxrate", bitrate,
                "-bufsize", str(int(bitrate.replace("k", "")) * 2) + "k",
                "-g", "48",  # Keyframe every 2 seconds
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "48000",
                "-ac", "2",
                "-f", "hls",
                "-hls_time", "4",
                "-hls_list_size", "0",
                "-hls_segment_type", "mpegts",
                "-hls_flags", "independent_segments",
                "-hls_segment_filename", str(output_dir / "segment_%03d.ts"),
                str(output_dir / "playlist.m3u8")
            ])

            logger.info(f"Starting HLS generation for file {file_id}")
            logger.debug(f"Command: {' '.join(cmd)}")

            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                logger.success(f"HLS generation complete in {elapsed:.1f}s")
                return True
            else:
                error = result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"HLS generation failed: {error[-500:]}")  # Last 500 chars
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"HLS generation timeout")
            return False
        except Exception as e:
            logger.error(f"HLS generation error: {e}")
            return False
        finally:
            with self._generation_lock:
                self._generating.pop(file_id, None)

    def get_playlist_file(self, file_id: int) -> Optional[Path]:
        playlist_path = self.get_hls_directory(file_id) / "playlist.m3u8"
        if playlist_path.exists():
            return playlist_path
        return None

    def get_segment_file(self, file_id: int, segment: str) -> Optional[Path]:
        segment_path = self.get_hls_directory(file_id) / segment
        if segment_path.exists() and segment_path.is_file():
            return segment_path
        return None

    def cleanup_old_segments(self, max_age_hours: int = 1, max_total_gb: float = 10.0):
        """Clean up old HLS segments."""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            max_bytes = max_total_gb * 1024 * 1024 * 1024

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

            files_info.sort(key=lambda x: x["mtime"])

            deleted_count = 0
            freed_bytes = 0

            for file_info in files_info:
                should_delete = False

                if file_info["age"] > max_age_seconds:
                    should_delete = True

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

            for file_dir in self.hls_output_dir.iterdir():
                if file_dir.is_dir() and not any(file_dir.iterdir()):
                    file_dir.rmdir()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} files, freed {freed_bytes / 1024 / 1024:.1f}MB")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")
