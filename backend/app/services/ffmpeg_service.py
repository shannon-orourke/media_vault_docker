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

    def transcode_for_streaming_gpu(
        self,
        input_path: str,
        output_path: str,
        width: int = 1280,
        height: int = 720,
        crf: int = 23,
        use_gpu: bool = True
    ) -> bool:
        """
        Transcode video for web streaming using GPU acceleration (NVENC).

        Uses NVIDIA NVENC for hardware encoding which is much faster than CPU
        and enables smooth streaming for comparison views.

        Args:
            input_path: Source video file path
            output_path: Output video file path (should be .mp4)
            width: Target width (default 1280)
            height: Target height (default 720)
            crf: Quality (18-28, lower is better quality, default 23)
            use_gpu: Use GPU acceleration if True, CPU if False

        Returns:
            True if successful, False otherwise
        """
        try:
            if use_gpu:
                # GPU-accelerated transcoding with NVENC
                cmd = [
                    settings.ffmpeg_path,
                    "-hwaccel", "cuda",           # Use CUDA hardware acceleration
                    "-hwaccel_output_format", "cuda",  # Keep frames on GPU
                    "-i", input_path,
                    "-vf", f"scale_cuda={width}:{height}",  # GPU-based scaling
                    "-c:v", "h264_nvenc",         # NVIDIA H.264 encoder
                    "-preset", "p4",              # NVENC preset (p1=fastest, p7=slowest/best)
                    "-cq", str(crf),              # Constant quality mode
                    "-c:a", "aac",                # AAC audio codec
                    "-b:a", "128k",               # Audio bitrate
                    "-movflags", "+faststart",    # Enable fast start for web streaming
                    "-y",                         # Overwrite output
                    output_path
                ]
            else:
                # CPU fallback (slower but works without GPU)
                cmd = [
                    settings.ffmpeg_path,
                    "-i", input_path,
                    "-vf", f"scale={width}:{height}",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", str(crf),
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-y",
                    output_path
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.success(f"{'GPU' if use_gpu else 'CPU'} transcoding complete: {output_path}")
                return True
            else:
                logger.error(f"Transcode failed: {result.stderr.decode()}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Transcode timeout for {input_path}")
            return False
        except Exception as e:
            logger.error(f"Error transcoding video: {e}")
            return False

    def create_preview_clip_gpu(
        self,
        input_path: str,
        output_path: str,
        start_time: str = "00:00:10",
        duration: int = 30,
        use_gpu: bool = True
    ) -> bool:
        """
        Create a short preview clip from video using GPU acceleration.

        Useful for generating quick previews for comparison without
        transcoding the entire file.

        Args:
            input_path: Source video file
            output_path: Output preview file path
            start_time: Start timestamp (HH:MM:SS)
            duration: Clip duration in seconds
            use_gpu: Use GPU acceleration

        Returns:
            True if successful
        """
        try:
            if use_gpu:
                cmd = [
                    settings.ffmpeg_path,
                    "-hwaccel", "cuda",
                    "-ss", start_time,
                    "-i", input_path,
                    "-t", str(duration),
                    "-c:v", "h264_nvenc",
                    "-preset", "p4",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-y",
                    output_path
                ]
            else:
                cmd = [
                    settings.ffmpeg_path,
                    "-ss", start_time,
                    "-i", input_path,
                    "-t", str(duration),
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-y",
                    output_path
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error creating preview clip: {e}")
            return False

    def check_gpu_encoding_available(self) -> bool:
        """
        Check if GPU encoding (NVENC) is available in FFmpeg.

        Returns:
            True if NVENC encoders are available
        """
        try:
            result = subprocess.run(
                [settings.ffmpeg_path, "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "h264_nvenc" in result.stdout

        except Exception:
            return False

    def is_browser_compatible(self, video_codec: Optional[str], audio_codec: Optional[str],
                             container_format: Optional[str]) -> dict:
        """
        Check if media file codecs are browser-compatible for direct streaming.

        Browser compatibility:
        - Video: H.264, VP8, VP9, AV1
        - Audio: AAC, MP3, Opus, Vorbis
        - Container: MP4, WebM

        Args:
            video_codec: Video codec name (e.g., 'h264', 'hevc')
            audio_codec: Audio codec name (e.g., 'aac', 'dts')
            container_format: Container format (e.g., 'mp4', 'mkv')

        Returns:
            Dict with compatibility info and recommendations
        """
        # Browser-compatible codecs
        COMPATIBLE_VIDEO = ['h264', 'vp8', 'vp9', 'av1']
        COMPATIBLE_AUDIO = ['aac', 'mp3', 'opus', 'vorbis']
        COMPATIBLE_CONTAINERS = ['mp4', 'webm']

        # Incompatible audio codecs that require transcoding
        INCOMPATIBLE_AUDIO = ['dts', 'ac3', 'eac3', 'truehd', 'dca', 'flac', 'pcm_s16le', 'pcm_s24le']

        # Normalize codec names (lowercase, remove variants)
        video_codec = (video_codec or '').lower().split('(')[0].strip()
        audio_codec = (audio_codec or '').lower().split('(')[0].strip()
        container_format = (container_format or '').lower().split(',')[0].strip()

        # Check video compatibility
        video_compatible = video_codec in COMPATIBLE_VIDEO

        # Check audio compatibility
        audio_compatible = audio_codec in COMPATIBLE_AUDIO
        audio_needs_transcode = audio_codec in INCOMPATIBLE_AUDIO

        # Check container compatibility
        container_compatible = container_format in COMPATIBLE_CONTAINERS

        # Overall compatibility
        fully_compatible = video_compatible and audio_compatible and container_compatible

        return {
            'compatible': fully_compatible,
            'video_compatible': video_compatible,
            'audio_compatible': audio_compatible,
            'container_compatible': container_compatible,
            'needs_video_transcode': not video_compatible,
            'needs_audio_transcode': audio_needs_transcode or not audio_compatible,
            'needs_remux': video_compatible and audio_compatible and not container_compatible,
            'recommendation': self._get_streaming_recommendation(
                fully_compatible, video_compatible, audio_compatible, container_compatible
            )
        }

    def _get_streaming_recommendation(self, fully_compatible: bool, video_ok: bool,
                                      audio_ok: bool, container_ok: bool) -> str:
        """Get streaming method recommendation based on compatibility."""
        if fully_compatible:
            return "direct_stream"  # Use existing range request streaming
        elif video_ok and audio_ok and not container_ok:
            return "remux_only"  # Fast container change, no transcode
        else:
            return "hls_transcode"  # Full transcode with adaptive streaming
