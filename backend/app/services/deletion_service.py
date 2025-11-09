"""File deletion and archival service."""
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.config import get_settings
from app.models import MediaFile, PendingDeletion, ArchiveOperation
from app.utils.path_utils import resolve_media_path, temp_delete_roots

settings = get_settings()


class DeletionService:
    """Service for managing file deletions and archival operations."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = settings

    def stage_file_for_deletion(
        self,
        media_file: MediaFile,
        reason: str,
        duplicate_group_id: Optional[int] = None,
        better_quality_file_id: Optional[int] = None,
        quality_score_diff: Optional[int] = None,
        language_concern: bool = False,
        language_concern_reason: Optional[str] = None,
    ) -> PendingDeletion:
        """
        Stage a file for deletion by moving it to the temporary archive location.
        """
        media_type = self._normalize_media_type(media_file.media_type)
        date_dir = datetime.now().strftime("%Y-%m-%d")
        staging_dir = self._prepare_staging_directory(media_type, date_dir)
        temp_filename = Path(media_file.filename)
        temp_filepath = self._unique_temp_path(staging_dir, temp_filename)

        pending = PendingDeletion(
            media_file_id=media_file.id,
            original_filepath=media_file.filepath,
            temp_filepath=None,  # updated after successful move
            file_size=media_file.file_size,
            reason=reason,
            duplicate_group_id=duplicate_group_id,
            better_quality_file_id=better_quality_file_id,
            quality_score_diff=quality_score_diff,
            language_concern=language_concern,
            language_concern_reason=language_concern_reason,
            staged_at=datetime.now(),
            approved_for_deletion=False
        )
        self.db.add(pending)

        media_file.is_deleted = True
        media_file.deleted_at = datetime.now()

        resolved_source = resolve_media_path(media_file.filepath)

        try:
            if resolved_source and resolved_source.exists():
                logger.info(f"Moving {resolved_source} to {temp_filepath}")
                shutil.move(str(resolved_source), str(temp_filepath))
                pending.temp_filepath = str(temp_filepath)

                archive_op = ArchiveOperation(
                    media_file_id=media_file.id,
                    operation_type="move_to_temp",
                    source_path=str(resolved_source),
                    destination_path=str(temp_filepath),
                    file_size=media_file.file_size,
                    success=True,
                    performed_at=datetime.now(),
                    operation_metadata={
                        "reason": reason,
                        "duplicate_group_id": duplicate_group_id,
                        "language_concern": language_concern
                    }
                )
                self.db.add(archive_op)
            else:
                logger.warning(
                    f"Source file {media_file.filepath} not found; marking as logically deleted"
                )
                metadata = pending.deletion_metadata or {}
                metadata.update({
                    "source_missing": True,
                    "resolved_path": str(resolved_source) if resolved_source else None
                })
                pending.deletion_metadata = metadata

                archive_op = ArchiveOperation(
                    media_file_id=media_file.id,
                    operation_type="move_to_temp",
                    source_path=media_file.filepath,
                    destination_path=None,
                    file_size=media_file.file_size,
                    success=False,
                    error_message="Source file missing",
                    performed_at=datetime.now(),
                    operation_metadata={"reason": reason}
                )
                self.db.add(archive_op)

            logger.success(f"File staged for deletion: {media_file.filename}")

        except Exception as e:
            logger.error(f"Failed to move file {media_file.filepath}: {e}")

            archive_op = ArchiveOperation(
                media_file_id=media_file.id,
                operation_type="move_to_temp",
                source_path=media_file.filepath,
                destination_path=str(temp_filepath),
                file_size=media_file.file_size,
                success=False,
                error_message=str(e),
                performed_at=datetime.now()
            )
            self.db.add(archive_op)

            media_file.is_deleted = False
            media_file.deleted_at = None

            raise

        self.db.commit()
        return pending

    def approve_deletion(
        self,
        pending_deletion_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Approve a pending deletion for permanent removal.

        Args:
            pending_deletion_id: ID of pending deletion
            user_id: Optional user ID approving deletion

        Returns:
            True if successful, False otherwise
        """
        pending = self.db.query(PendingDeletion).filter(
            PendingDeletion.id == pending_deletion_id
        ).first()

        if not pending:
            logger.error(f"Pending deletion {pending_deletion_id} not found")
            return False

        # Mark as approved
        pending.approved_for_deletion = True
        pending.approved_at = datetime.now()
        pending.approved_by_user_id = user_id

        # Delete the temp file permanently
        try:
            resolved_temp = resolve_media_path(pending.temp_filepath) if pending.temp_filepath else None
            if resolved_temp and resolved_temp.exists():
                os.remove(resolved_temp)
                logger.info(f"Permanently deleted {resolved_temp}")

                archive_op = ArchiveOperation(
                    media_file_id=pending.media_file_id,
                    operation_type="permanent_delete",
                    source_path=str(resolved_temp),
                    destination_path=None,
                    file_size=pending.file_size,
                    success=True,
                    performed_at=datetime.now(),
                    performed_by_user_id=user_id
                )
                self.db.add(archive_op)

                pending.deleted_at = datetime.now()

        except Exception as e:
            logger.error(f"Failed to permanently delete {pending.temp_filepath}: {e}")

            archive_op = ArchiveOperation(
                media_file_id=pending.media_file_id,
                operation_type="permanent_delete",
                source_path=pending.temp_filepath,
                destination_path=None,
                file_size=pending.file_size,
                success=False,
                error_message=str(e),
                performed_at=datetime.now()
            )
            self.db.add(archive_op)

            self.db.commit()
            return False

        self.db.commit()
        return True

    def restore_file(
        self,
        pending_deletion_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Restore a file from pending deletion back to its original location.

        Args:
            pending_deletion_id: ID of pending deletion
            user_id: Optional user ID restoring file

        Returns:
            True if successful, False otherwise
        """
        pending = self.db.query(PendingDeletion).filter(
            PendingDeletion.id == pending_deletion_id
        ).first()

        if not pending:
            logger.error(f"Pending deletion {pending_deletion_id} not found")
            return False

        media_file = pending.media_file

        try:
            resolved_temp = resolve_media_path(pending.temp_filepath) if pending.temp_filepath else None
            if resolved_temp and resolved_temp.exists():
                logger.info(f"Restoring {resolved_temp} to {pending.original_filepath}")

                # Ensure original directory exists
                os.makedirs(os.path.dirname(pending.original_filepath), exist_ok=True)

                shutil.move(str(resolved_temp), pending.original_filepath)

                # Record operation
                archive_op = ArchiveOperation(
                    media_file_id=pending.media_file_id,
                    operation_type="restore",
                    source_path=str(resolved_temp),
                    destination_path=pending.original_filepath,
                    file_size=pending.file_size,
                    success=True,
                    performed_at=datetime.now(),
                    performed_by_user_id=user_id
                )
                self.db.add(archive_op)

                # Update media file status
                media_file.is_deleted = False
                media_file.deleted_at = None

                # Remove pending deletion record
                self.db.delete(pending)

                logger.success(f"File restored: {media_file.filename}")

        except Exception as e:
            logger.error(f"Failed to restore {pending.temp_filepath}: {e}")

            archive_op = ArchiveOperation(
                media_file_id=pending.media_file_id,
                operation_type="restore",
                source_path=pending.temp_filepath,
                destination_path=pending.original_filepath,
                file_size=pending.file_size,
                success=False,
                error_message=str(e),
                performed_at=datetime.now()
            )
            self.db.add(archive_op)

            self.db.commit()
            return False

        self.db.commit()
        return True

    def cleanup_old_pending_deletions(self) -> int:
        """
        Clean up pending deletions older than retention period.

        Returns:
            Number of records cleaned up
        """
        cutoff_date = datetime.now() - timedelta(days=settings.pending_deletion_retention_days)

        old_pending = self.db.query(PendingDeletion).filter(
            PendingDeletion.staged_at < cutoff_date,
            PendingDeletion.approved_for_deletion == False
        ).all()

        count = 0
        for pending in old_pending:
            try:
                # Delete temp file
                if pending.temp_filepath and os.path.exists(pending.temp_filepath):
                    os.remove(pending.temp_filepath)

                # Remove record
                self.db.delete(pending)
                count += 1

            except Exception as e:
                logger.error(f"Failed to cleanup pending deletion {pending.id}: {e}")

        self.db.commit()
        logger.info(f"Cleaned up {count} old pending deletions")
        return count

    def get_pending_deletions(
        self,
        skip: int = 0,
        limit: int = 50,
        language_concern: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get list of pending deletions.

        Returns:
            Dict with total count and list of pending deletions
        """
        query = self.db.query(PendingDeletion).filter(
            PendingDeletion.deleted_at.is_(None)
        )

        if language_concern is not None:
            query = query.filter(
                PendingDeletion.language_concern == int(language_concern)
            )

        total = query.count()
        pending = query.order_by(PendingDeletion.staged_at.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "pending": [
                {
                    "id": p.id,
                    "media_file_id": p.media_file_id,
                    "filename": p.media_file.filename if p.media_file else None,
                    "original_filepath": p.original_filepath,
                    "original_path": p.original_filepath,
                    "temp_filepath": p.temp_filepath,
                    "temp_path": p.temp_filepath,
                    "file_size": p.file_size,
                    "reason": p.reason,
                    "duplicate_group_id": p.duplicate_group_id,
                    "quality_score_diff": p.quality_score_diff,
                    "language_concern": bool(p.language_concern),
                    "language_concern_reason": p.language_concern_reason,
                    "staged_at": p.staged_at.isoformat() if p.staged_at else None,
                    "approved_for_deletion": bool(p.approved_for_deletion),
                }
                for p in pending
            ]
        }

    def _normalize_media_type(self, media_type: Optional[str]) -> str:
        normalized = (media_type or "other").lower()
        if normalized not in settings.temp_delete_subdirs_list:
            return "other"
        return normalized

    def _prepare_staging_directory(self, media_type: str, date_dir: str) -> Path:
        errors = []
        for root in temp_delete_roots():
            staging_dir = root / media_type / date_dir
            try:
                staging_dir.mkdir(parents=True, exist_ok=True)
                return staging_dir
            except Exception as exc:
                errors.append(f"{staging_dir}: {exc}")
                logger.warning(f"Unable to use staging dir {staging_dir}: {exc}")
        raise RuntimeError(
            f"Unable to prepare staging directory for pending deletions. Tried: {errors}"
        )

    def _unique_temp_path(self, staging_dir: Path, filename: Path) -> Path:
        candidate = staging_dir / filename
        counter = 1
        while candidate.exists():
            stem = filename.stem
            suffix = filename.suffix
            candidate = staging_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        return candidate
