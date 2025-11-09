"""FFmpeg/FFprobe service for media metadata extraction."""
import subprocess
import json
from typing import Optional, Dict, Any
from loguru import logger

from app.config import get_settings
from app.services import cuda_hash

settings = get_settings()


class FFmpegService:
    """Service for extracting media file metadata using FFprobe."""

    def __init__(self):
        self.ffprobe_path = settings.ffprobe_path
        self.md5_chunk_size = settings.md5_chunk_size

    def check_ffprobe_installed(self) -> bool:
        """Check if FFprobe is installed."""
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def extract_metadata(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Extract complete metadata from media file using FFprobe.

        Returns:
            Dictionary with extracted metadata or None on error
        """
        if not self.check_ffprobe_installed():
            logger.error("FFprobe not installed")
            return None

        try:
            # Run ffprobe with JSON output
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                filepath
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"FFprobe failed for {filepath}: {result.stderr}")
                return None

            # Parse JSON output
            data = json.loads(result.stdout)

            # Extract relevant information
            metadata = self._parse_ffprobe_output(data, filepath)
            return metadata

        except subprocess.TimeoutExpired:
            logger.error(f"FFprobe timeout for {filepath}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FFprobe output: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting metadata from {filepath}: {e}")
            return None

    def _parse_ffprobe_output(self, data: dict, filepath: str) -> Dict[str, Any]:
        """Parse FFprobe JSON output into MediaVault metadata format."""
        format_info = data.get("format", {})
        streams = data.get("streams", [])

        # Find video and audio streams
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

        metadata = {
            # File info
            "filepath": filepath,
            "format": format_info.get("format_name", "").split(",")[0],
            "duration": float(format_info.get("duration", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)) // 1000,  # Convert to kbps
        }

        # Video metadata
        if video_stream:
            metadata.update({
                "video_codec": video_stream.get("codec_name"),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "resolution": f"{video_stream.get('width')}x{video_stream.get('height')}",
                "framerate": self._parse_framerate(video_stream.get("r_frame_rate", "0/1")),
                "quality_tier": self._determine_quality_tier(video_stream.get("height")),
            })

            # HDR detection
            color_space = video_stream.get("color_space", "")
            color_transfer = video_stream.get("color_transfer", "")
            if "bt2020" in color_space or "smpte2084" in color_transfer:
                metadata["hdr_type"] = "HDR10"
            elif "arib-std-b67" in color_transfer:
                metadata["hdr_type"] = "HLG"
            else:
                metadata["hdr_type"] = "SDR"

        # Audio metadata
        if audio_streams:
            primary_audio = audio_streams[0]
            metadata.update({
                "audio_codec": primary_audio.get("codec_name"),
                "audio_channels": float(primary_audio.get("channels", 2)),
                "audio_track_count": len(audio_streams),
            })

            # Extract audio languages
            audio_languages = []
            for stream in audio_streams:
                lang = stream.get("tags", {}).get("language", "und")
                if lang and lang not in audio_languages:
                    audio_languages.append(lang)
            metadata["audio_languages"] = audio_languages
            metadata["dominant_audio_language"] = audio_languages[0] if audio_languages else "und"

        # Subtitle metadata
        if subtitle_streams:
            metadata["subtitle_track_count"] = len(subtitle_streams)

            # Extract subtitle languages
            subtitle_languages = []
            for stream in subtitle_streams:
                lang = stream.get("tags", {}).get("language", "und")
                if lang and lang not in subtitle_languages:
                    subtitle_languages.append(lang)
            metadata["subtitle_languages"] = subtitle_languages
        else:
            metadata["subtitle_track_count"] = 0
            metadata["subtitle_languages"] = []

        return metadata

    def _parse_framerate(self, framerate_str: str) -> float:
        """Parse framerate from fraction string (e.g., '24000/1001')."""
        try:
            if "/" in framerate_str:
                numerator, denominator = framerate_str.split("/")
                return round(float(numerator) / float(denominator), 3)
            return float(framerate_str)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _determine_quality_tier(self, height: Optional[int]) -> str:
        """Determine quality tier based on video height."""
        if height is None:
            return "unknown"
        elif height >= 2160:
            return "4K"
        elif height >= 1080:
            return "1080p"
        elif height >= 720:
            return "720p"
        elif height >= 480:
            return "480p"
        else:
            return "SD"

    def calculate_md5(self, filepath: str) -> Optional[str]:
        """
        Calculate MD5 hash of file for exact duplicate detection.
        Uses GPU acceleration if available, falls back to CPU.

        Args:
            filepath: Path to file

        Returns:
            MD5 hash string or None on error
        """
        try:
            # Use GPU-accelerated MD5 if available, CPU fallback
            return cuda_hash.calculate_md5(filepath, chunk_size=self.md5_chunk_size)

        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            return None
        except PermissionError:
            logger.error(f"Permission denied: {filepath}")
            return None
        except Exception as e:
            logger.error(f"Error calculating MD5 for {filepath}: {e}")
            return None

    def get_video_thumbnail(
        self,
        filepath: str,
        output_path: str,
        timestamp: str = "00:00:05"
    ) -> bool:
        """
        Generate video thumbnail at specified timestamp.

        Args:
            filepath: Source video file
            output_path: Output image path
            timestamp: Timestamp in format HH:MM:SS

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                settings.ffmpeg_path,
                "-ss", timestamp,
                "-i", filepath,
                "-vframes", "1",
                "-q:v", "2",
                "-y",  # Overwrite output
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return False
