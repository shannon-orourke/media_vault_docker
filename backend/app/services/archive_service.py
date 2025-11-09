"""Archive service for RAR/ZIP file detection and extraction."""
import os
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import guessit

from sqlalchemy.orm import Session
from app.models import ArchiveFile, ArchiveContent, MediaFile
from app.services.nas_service import NASService
from app.config import get_settings

settings = get_settings()


class ArchiveService:
    """Service for managing archive files (RAR, ZIP, 7z)."""

    def __init__(self, db: Session):
        self.db = db
        self.nas_service = NASService()
        self.archive_extensions = ['.rar', '.zip', '.7z', '.tar', '.gz', '.bz2']

        # Destination paths from settings
        self.movie_dest = "/volume1/videos/movies"
        self.tv_dest = "/volume1/videos/tv"

    def scan_for_archives(
        self,
        paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Scan NAS paths for archive files.

        Args:
            paths: List of paths to scan (defaults to settings)

        Returns:
            Dict with scan results
        """
        if paths is None:
            paths = settings.nas_scan_paths_list

        logger.info(f"Scanning for archives in {len(paths)} paths...")

        found_count = 0
        new_count = 0
        updated_count = 0

        for scan_path in paths:
            effective_path = self.nas_service.get_effective_path(scan_path)
            logger.info(f"Scanning for archives: {effective_path}")

            # List archive files
            archive_files = self.nas_service.list_files(
                path=effective_path,
                recursive=True,
                extensions=self.archive_extensions
            )

            found_count += len(archive_files)
            logger.info(f"Found {len(archive_files)} archive files in {scan_path}")

            # Process each archive
            for filepath in archive_files:
                try:
                    # Check if already exists
                    existing = self.db.query(ArchiveFile).filter(
                        ArchiveFile.filepath == filepath
                    ).first()

                    if existing:
                        updated_count += 1
                        continue

                    # Get file info
                    file_info = self.nas_service.get_file_info(filepath)
                    if not file_info:
                        continue

                    # Parse filename for metadata
                    parsed = self._parse_filename(file_info['filename'])

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
                        media_type=parsed.get('type', 'unknown'),
                        discovered_at=datetime.utcnow()
                    )

                    # Set destination path based on media type
                    archive.destination_path = self._get_destination_path(parsed)

                    # Set deletion date to 6 months from now
                    archive.set_deletion_date(months=6)

                    self.db.add(archive)
                    new_count += 1

                except Exception as e:
                    logger.error(f"Error processing archive {filepath}: {e}")
                    continue

        # Commit all changes
        try:
            self.db.commit()
            logger.info(f"Archive scan complete: {new_count} new, {updated_count} updated")
        except Exception as e:
            logger.error(f"Error committing archive records: {e}")
            self.db.rollback()

        return {
            "found": found_count,
            "new": new_count,
            "updated": updated_count
        }

    def _parse_filename(self, filename: str) -> Dict[str, Any]:
        """Parse filename using guessit to extract metadata."""
        try:
            parsed = guessit(filename)
            return {
                'title': parsed.get('title'),
                'year': parsed.get('year'),
                'season': parsed.get('season'),
                'episode': parsed.get('episode'),
                'type': 'movie' if parsed.get('type') == 'movie' else ('tv' if 'season' in parsed or 'episode' in parsed else 'unknown')
            }
        except Exception as e:
            logger.error(f"Error parsing filename {filename}: {e}")
            return {}

    def _get_destination_path(self, parsed: Dict[str, Any]) -> str:
        """Determine destination path based on media type."""
        media_type = parsed.get('type', 'unknown')

        if media_type == 'movie':
            title = parsed.get('title', 'Unknown')
            year = parsed.get('year', '')
            year_str = f" ({year})" if year else ""
            return f"{self.movie_dest}/{title}{year_str}"
        elif media_type == 'tv':
            title = parsed.get('title', 'Unknown')
            return f"{self.tv_dest}/{title}"
        else:
            return f"{self.movie_dest}/Unknown"

    def check_unrar_installed(self) -> bool:
        """Check if unrar is installed."""
        try:
            result = subprocess.run(
                ["which", "unrar"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def extract_archive(
        self,
        archive_id: int,
        destination: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Extract archive file.

        Args:
            archive_id: Archive file ID
            destination: Optional custom destination (uses archive.destination_path if not provided)

        Returns:
            Tuple of (success: bool, message: str)
        """
        archive = self.db.query(ArchiveFile).filter(ArchiveFile.id == archive_id).first()
        if not archive:
            return False, f"Archive {archive_id} not found"

        # Determine destination
        dest = destination or archive.destination_path
        if not dest:
            return False, "No destination path specified"

        # Ensure destination exists
        os.makedirs(dest, exist_ok=True)

        logger.info(f"Extracting {archive.filename} to {dest}")

        try:
            # Extract based on archive type
            if archive.archive_type == 'rar':
                success, message = self._extract_rar(archive.filepath, dest)
            elif archive.archive_type == 'zip':
                success, message = self._extract_zip(archive.filepath, dest)
            elif archive.archive_type == '7z':
                success, message = self._extract_7z(archive.filepath, dest)
            else:
                return False, f"Unsupported archive type: {archive.archive_type}"

            if success:
                # Update archive status
                archive.extraction_status = 'extracted'
                archive.extracted_at = datetime.utcnow()
                archive.extracted_to_path = dest

                # TODO: Scan extracted files and link to media_files table
                # This would require calling the scanner service on the destination

                self.db.commit()
                return True, f"Successfully extracted to {dest}"
            else:
                archive.extraction_status = 'failed'
                archive.extraction_error = message
                self.db.commit()
                return False, message

        except Exception as e:
            error_msg = f"Extraction failed: {str(e)}"
            logger.error(error_msg)
            archive.extraction_status = 'failed'
            archive.extraction_error = error_msg
            self.db.commit()
            return False, error_msg

    def _extract_rar(self, filepath: str, destination: str) -> Tuple[bool, str]:
        """Extract RAR archive using unrar."""
        try:
            result = subprocess.run(
                ["unrar", "x", "-o+", filepath, destination],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )

            if result.returncode == 0:
                return True, "RAR extracted successfully"
            else:
                return False, f"unrar error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Extraction timeout (5 minutes)"
        except Exception as e:
            return False, f"Extraction error: {str(e)}"

    def _extract_zip(self, filepath: str, destination: str) -> Tuple[bool, str]:
        """Extract ZIP archive using unzip."""
        try:
            result = subprocess.run(
                ["unzip", "-o", filepath, "-d", destination],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return True, "ZIP extracted successfully"
            else:
                return False, f"unzip error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Extraction timeout (5 minutes)"
        except Exception as e:
            return False, f"Extraction error: {str(e)}"

    def _extract_7z(self, filepath: str, destination: str) -> Tuple[bool, str]:
        """Extract 7z archive using 7z."""
        try:
            result = subprocess.run(
                ["7z", "x", filepath, f"-o{destination}", "-y"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return True, "7z extracted successfully"
            else:
                return False, f"7z error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Extraction timeout (5 minutes)"
        except Exception as e:
            return False, f"Extraction error: {str(e)}"

    def move_archive_to_seed_location(
        self,
        archive_id: int,
        seed_location: str = "/volume1/downloads/complete"
    ) -> Tuple[bool, str]:
        """
        Move archive to seeding location after extraction.

        Args:
            archive_id: Archive file ID
            seed_location: Path to move archive for continued seeding

        Returns:
            Tuple of (success: bool, message: str)
        """
        archive = self.db.query(ArchiveFile).filter(ArchiveFile.id == archive_id).first()
        if not archive:
            return False, f"Archive {archive_id} not found"

        if archive.extraction_status != 'extracted':
            return False, "Archive not yet extracted"

        try:
            # Create seed location if it doesn't exist
            os.makedirs(seed_location, exist_ok=True)

            # Move file
            new_path = os.path.join(seed_location, archive.filename)
            os.rename(archive.filepath, new_path)

            # Update archive record
            archive.filepath = new_path
            self.db.commit()

            return True, f"Moved to {new_path}"

        except Exception as e:
            error_msg = f"Failed to move archive: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def list_archives(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        List archive files with optional filtering.

        Args:
            status: Filter by extraction status ('pending', 'extracted', 'failed')
            limit: Maximum number of results
            skip: Number of results to skip

        Returns:
            Dict with total count and archives list
        """
        query = self.db.query(ArchiveFile)

        if status:
            query = query.filter(ArchiveFile.extraction_status == status)

        total = query.count()
        archives = query.order_by(ArchiveFile.discovered_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "archives": archives
        }

    def mark_for_deletion(self, archive_id: int) -> Tuple[bool, str]:
        """Mark archive for immediate deletion (removes 6-month grace period)."""
        archive = self.db.query(ArchiveFile).filter(ArchiveFile.id == archive_id).first()
        if not archive:
            return False, f"Archive {archive_id} not found"

        archive.mark_for_deletion_at = datetime.utcnow()
        archive.keep_for_seeding = False
        self.db.commit()

        return True, "Archive marked for deletion"

    def delete_old_archives(self) -> int:
        """Delete archives that have passed their retention period."""
        archives_to_delete = self.db.query(ArchiveFile).filter(
            ArchiveFile.mark_for_deletion_at <= datetime.utcnow(),
            ArchiveFile.deleted_at.is_(None)
        ).all()

        deleted_count = 0
        for archive in archives_to_delete:
            try:
                # Delete physical file
                if os.path.exists(archive.filepath):
                    os.remove(archive.filepath)

                # Mark as deleted
                archive.deleted_at = datetime.utcnow()
                deleted_count += 1

            except Exception as e:
                logger.error(f"Failed to delete archive {archive.id}: {e}")

        self.db.commit()
        return deleted_count
