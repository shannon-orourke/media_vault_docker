"""Quality scoring service for media files."""
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger

from app.config import get_settings


class QualityService:
    """Service for calculating media file quality scores (0-200 scale)."""

    def __init__(self):
        self.settings = get_settings()

    def calculate_quality_score(self, metadata: Dict[str, Any]) -> int:
        """
        Calculate quality score based on MediaVault scoring algorithm.

        Scoring breakdown (0-200 scale):
        - Resolution: 4K=100, 1080p=75, 720p=50, 480p=25, SD=10
        - Codec: H.265=20, H.264=15, VP9=18, AV1=22
        - Bitrate: Normalized 0-30 (based on resolution-specific ideals)
        - Audio: 5.1+=15, 2.0=10
        - Multi-audio tracks: +3 per track (max 10)
        - Subtitles: +2 per track (max 10)
        - HDR: +15 if HDR10/Dolby Vision

        Args:
            metadata: Dictionary with extracted metadata from FFprobe

        Returns:
            Quality score (0-200)
        """
        score = 0

        # Resolution score (0-100)
        height = metadata.get("height")
        if height:
            if height >= 2160:  # 4K
                score += 100
            elif height >= 1080:  # 1080p
                score += 75
            elif height >= 720:  # 720p
                score += 50
            elif height >= 480:  # 480p
                score += 25
            else:  # SD
                score += 10

        # Codec score (0-22)
        video_codec = metadata.get("video_codec", "").lower()
        if "hevc" in video_codec or "h265" in video_codec or "x265" in video_codec:
            score += 20
        elif "avc" in video_codec or "h264" in video_codec or "x264" in video_codec:
            score += 15
        elif "vp9" in video_codec:
            score += 18
        elif "av1" in video_codec:
            score += 22

        # Bitrate score (0-30)
        bitrate_score = self._calculate_bitrate_score(
            bitrate=metadata.get("bitrate", 0),
            height=height
        )
        score += bitrate_score

        # Audio channels score (0-15)
        audio_channels = metadata.get("audio_channels", 2)
        if audio_channels >= 5:  # 5.1 or higher
            score += 15
        else:  # 2.0
            score += 10

        # Multi-audio tracks score (max 10)
        audio_track_count = metadata.get("audio_track_count", 1)
        if audio_track_count > 1:
            multi_audio_score = min((audio_track_count - 1) * 3, 10)
            score += multi_audio_score

        # Subtitle tracks score (max 10)
        subtitle_track_count = metadata.get("subtitle_track_count", 0)
        if subtitle_track_count > 0:
            subtitle_score = min(subtitle_track_count * 2, 10)
            score += subtitle_score

        # HDR score (+15)
        hdr_type = metadata.get("hdr_type", "SDR")
        if hdr_type in ["HDR10", "Dolby Vision", "HDR10+", "HLG"]:
            score += 15

        # Cap at 200
        return min(score, 200)

    def rank_files(self, files_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank files by quality score, returning metadata enriched with rank values.
        """
        ranked: List[Dict[str, Any]] = []

        for meta in files_metadata:
            score = meta.get("quality_score")
            if score in (None, 0):
                score = self.calculate_quality_score(meta)
            enriched = dict(meta)
            enriched["quality_score"] = score
            ranked.append(enriched)

        ranked.sort(key=lambda item: item.get("quality_score", 0), reverse=True)

        for idx, item in enumerate(ranked, start=1):
            item["rank"] = idx

        return ranked

    def check_language_concern(self, file_meta: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if deleting this file would risk losing English audio or foreign-film coverage.
        Returns (concern, reason).
        """
        audio_langs = [lang.lower() for lang in (file_meta.get("audio_languages") or [])]
        subtitle_langs = [lang.lower() for lang in (file_meta.get("subtitle_languages") or [])]
        dominant = (file_meta.get("dominant_audio_language") or "").lower()

        if self.settings.require_english_audio and ("eng" in audio_langs or dominant == "eng"):
            return True, "File contains English audio; require manual review before deletion."

        if self.settings.trust_foreign_film_heuristic:
            if "eng" not in audio_langs and "eng" in subtitle_langs:
                return True, "Foreign-film heuristic triggered (non-English audio with English subtitles)."

        return False, ""

    def _calculate_bitrate_score(self, bitrate: int, height: Optional[int]) -> int:
        """
        Calculate bitrate score normalized to resolution.

        Ideal bitrates (kbps):
        - 4K: 50000
        - 1080p: 10000
        - 720p: 5000
        - 480p: 2500
        - SD: 1000

        Args:
            bitrate: Bitrate in kbps
            height: Video height in pixels

        Returns:
            Bitrate score (0-30)
        """
        if not bitrate or not height:
            return 0

        # Determine ideal bitrate based on resolution
        if height >= 2160:  # 4K
            ideal_bitrate = 50000
        elif height >= 1080:  # 1080p
            ideal_bitrate = 10000
        elif height >= 720:  # 720p
            ideal_bitrate = 5000
        elif height >= 480:  # 480p
            ideal_bitrate = 2500
        else:  # SD
            ideal_bitrate = 1000

        # Calculate ratio (cap at 1.0 to avoid bonus for excessively high bitrates)
        ratio = min(bitrate / ideal_bitrate, 1.0)

        # Scale to 0-30
        return int(ratio * 30)
