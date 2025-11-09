"""Scanner service for NAS file discovery and metadata extraction."""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
import guessit

from sqlalchemy.orm import Session
from app.models import MediaFile, ScanHistory, ArchiveFile
from app.services.nas_service import NASService
from app.services.ffmpeg_service import FFmpegService
from app.services.quality_service import QualityService
from app.config import get_settings

settings = get_settings()


class ScannerService:
    """Service for scanning NAS and extracting media file metadata."""

    def __init__(self, db: Session):
        self.db = db
        self.nas_service = NASService()
        self.ffmpeg_service = FFmpegService()
        self.quality_service = QualityService()
        self.video_extensions = settings.video_extensions_list
        self.archive_extensions = ['.rar', '.zip', '.7z', '.tar', '.gz', '.bz2']

    def scan_nas(
        self,
        paths: Optional[List[str]] = None,
        scan_type: str = "full"
    ) -> ScanHistory:
        """
        Scan NAS for media files and extract metadata.

        Args:
            paths: List of paths to scan (defaults to settings)
            scan_type: "full" or "incremental"

        Returns:
            ScanHistory object
        """
        if paths is None:
            paths = settings.nas_scan_paths_list

        # Create scan history entry
        scan_history = ScanHistory(
            scan_type=scan_type,
            nas_paths=paths,
            scan_started_at=datetime.now(),
            status="running",
        )
        self.db.add(scan_history)
        self.db.commit()
        self.db.refresh(scan_history)  # Ensure we have the latest data

        logger.info(f"Starting {scan_type} scan of {len(paths)} paths...")

        files_found = 0
        files_new = 0
        files_updated = 0
        errors_count = 0
        archives_found = 0
        archives_new = 0

        try:
            for scan_path in paths:
                # Get effective path (considering NAS mount)
                effective_path = self.nas_service.get_effective_path(scan_path)

                logger.info(f"Scanning: {effective_path}")

                # List video files
                video_files = self.nas_service.list_files(
                    path=effective_path,
                    recursive=True,
                    extensions=self.video_extensions
                )

                files_found += len(video_files)
                logger.info(f"Found {len(video_files)} video files in {scan_path}")

                # Also scan for archives in the same pass
                archive_files = self.nas_service.list_files(
                    path=effective_path,
                    recursive=True,
                    extensions=self.archive_extensions
                )

                archives_found += len(archive_files)
                logger.info(f"Found {len(archive_files)} archive files in {scan_path}")

                # Process video files
                for filepath in video_files:
                    try:
                        # Check if file already exists
                        existing_file = (
                            self.db.query(MediaFile)
                            .filter(MediaFile.filepath == filepath)
                            .first()
                        )

                        if existing_file and scan_type == "incremental":
                            logger.debug(f"Skipping existing file: {filepath}")
                            continue

                        # Process file
                        media_file = self._process_file(filepath, existing_file)

                        if media_file:
                            if existing_file:
                                files_updated += 1
                            else:
                                files_new += 1

                            if (files_new + files_updated) % 10 == 0:
                                logger.info(f"Processed {files_new + files_updated}/{files_found} files...")
                        else:
                            errors_count += 1

                    except Exception as e:
                        logger.error(f"Error processing {filepath}: {e}")
                        errors_count += 1
                        self.db.rollback()  # Rollback failed transaction

                # Process archive files
                for filepath in archive_files:
                    try:
                        # Check if archive already exists
                        existing_archive = (
                            self.db.query(ArchiveFile)
                            .filter(ArchiveFile.filepath == filepath)
                            .first()
                        )

                        if existing_archive:
                            continue  # Skip existing archives

                        # Get file info
                        file_info = self.nas_service.get_file_info(filepath)
                        if not file_info:
                            continue

                        # Parse filename for metadata
                        parsed = guessit.guessit(file_info['filename'])

                        # Determine archive type
                        archive_type = os.path.splitext(filepath)[1][1:]  # Remove leading dot

                        # Create archive record
                        archive = ArchiveFile(
                            filename=file_info['filename'],
                            filepath=filepath,
                            file_size=file_info['file_size'],
                            archive_type=archive_type,
                            extraction_status='pending',
                            parsed_title=parsed.get('title'),
                            parsed_year=parsed.get('year'),
                            parsed_season=parsed.get('season'),
                            parsed_episode=parsed.get('episode'),
                            media_type='movie' if parsed.get('type') == 'movie' else ('tv' if 'season' in parsed or 'episode' in parsed else 'unknown'),
                            discovered_at=datetime.utcnow()
                        )

                        # Set destination path
                        if archive.media_type == 'movie':
                            title = parsed.get('title', 'Unknown')
                            year = parsed.get('year', '')
                            year_str = f" ({year})" if year else ""
                            archive.destination_path = f"/volume1/videos/movies/{title}{year_str}"
                        elif archive.media_type == 'tv':
                            title = parsed.get('title', 'Unknown')
                            archive.destination_path = f"/volume1/videos/tv/{title}"
                        else:
                            archive.destination_path = "/volume1/videos/movies/Unknown"

                        # Set deletion date to 6 months from now
                        archive.set_deletion_date(months=6)

                        self.db.add(archive)
                        archives_new += 1

                    except Exception as e:
                        logger.error(f"Error processing archive {filepath}: {e}")
                        self.db.rollback()

            # Commit archives
            try:
                self.db.commit()
                if archives_new > 0:
                    logger.info(f"Added {archives_new} archives to database")
            except Exception as e:
                logger.error(f"Error committing archives: {e}")
                self.db.rollback()

            # Update scan history
            scan_history.scan_completed_at = datetime.now()
            scan_history.duration_seconds = int((scan_history.scan_completed_at - scan_history.scan_started_at).total_seconds())
            scan_history.status = "completed"
            scan_history.files_found = files_found
            scan_history.files_new = files_new
            scan_history.files_updated = files_updated
            scan_history.errors_count = errors_count
            self.db.commit()

            logger.success(
                f"✓ Scan completed: {files_new} new, {files_updated} updated, "
                f"{errors_count} errors, {files_found} total"
            )

        except Exception as e:
            self.db.rollback()  # Rollback any pending changes
            scan_history.scan_completed_at = datetime.now()
            scan_history.duration_seconds = int((scan_history.scan_completed_at - scan_history.scan_started_at).total_seconds())
            scan_history.status = "failed"
            scan_history.error_details = {"error": str(e)}
            scan_history.files_found = files_found
            scan_history.files_new = files_new
            scan_history.files_updated = files_updated
            scan_history.errors_count = errors_count
            self.db.commit()

            logger.error(f"✗ Scan failed: {e}")

        return scan_history

    def _process_file(
        self,
        filepath: str,
        existing_file: Optional[MediaFile] = None
    ) -> Optional[MediaFile]:
        """
        Process a single media file: extract metadata, parse filename, calculate hash.

        Returns:
            MediaFile object or None on error
        """
        try:
            # Get file info
            file_info = self.nas_service.get_file_info(filepath)
            if not file_info:
                return None

            # Extract metadata with FFprobe
            metadata = self.ffmpeg_service.extract_metadata(filepath)
            if not metadata:
                logger.warning(f"Failed to extract metadata: {filepath}")
                return None

            # Parse filename with guessit
            parsed = guessit.guessit(file_info["filename"])

            # Calculate MD5 hash (expensive, but necessary)
            md5_hash = self.ffmpeg_service.calculate_md5(filepath)

            # Create or update media file
            if existing_file:
                media_file = existing_file
            else:
                media_file = MediaFile()

            # Update fields
            media_file.filename = file_info["filename"]
            media_file.filepath = filepath
            media_file.file_size = file_info["file_size"]
            media_file.md5_hash = md5_hash

            # Metadata from FFprobe
            media_file.duration = metadata.get("duration")
            media_file.format = metadata.get("format")
            media_file.video_codec = metadata.get("video_codec")
            media_file.audio_codec = metadata.get("audio_codec")
            media_file.resolution = metadata.get("resolution")
            media_file.width = metadata.get("width")
            media_file.height = metadata.get("height")
            media_file.bitrate = metadata.get("bitrate")
            media_file.framerate = metadata.get("framerate")
            media_file.quality_tier = metadata.get("quality_tier")
            media_file.hdr_type = metadata.get("hdr_type")
            media_file.audio_channels = metadata.get("audio_channels")
            media_file.audio_track_count = metadata.get("audio_track_count", 1)
            media_file.subtitle_track_count = metadata.get("subtitle_track_count", 0)
            media_file.audio_languages = metadata.get("audio_languages", [])
            media_file.subtitle_languages = metadata.get("subtitle_languages", [])
            media_file.dominant_audio_language = metadata.get("dominant_audio_language")

            # Calculate quality score (0-200 scale)
            media_file.quality_score = self.quality_service.calculate_quality_score(metadata)

            # Parsed metadata from guessit
            media_file.parsed_title = parsed.get("title")
            media_file.parsed_year = parsed.get("year")
            media_file.parsed_season = parsed.get("season")
            media_file.parsed_episode = parsed.get("episode")
            media_file.parsed_release_group = parsed.get("release_group")

            # Determine media type
            if "episode" in parsed:
                media_file.media_type = "tv"
            elif "documentary" in str(parsed.get("other", "")).lower():
                media_file.media_type = "documentary"
            else:
                media_file.media_type = "movie"

            # Timestamps
            media_file.last_scanned_at = datetime.now()
            media_file.metadata_updated_at = datetime.now()

            if not existing_file:
                media_file.discovered_at = datetime.now()
                self.db.add(media_file)

            self.db.commit()

            logger.debug(f"Processed: {media_file.filename}")
            return media_file

        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
            self.db.rollback()
            return None
