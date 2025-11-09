"""File renaming service with history tracking."""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from app.models import MediaFile


class RenameService:
    """Service for renaming media files with history tracking."""

    def __init__(self, db: Session):
        self.db = db

    def rename_file(
        self,
        media_file: MediaFile,
        new_filename: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Rename a single file and track history.

        Args:
            media_file: MediaFile to rename
            new_filename: New filename (without path)
            user_id: Optional user ID performing rename

        Returns:
            Dict with old_path, new_path, and status
        """
        old_filepath = media_file.filepath
        old_filename = media_file.filename

        # Build new path (same directory, new filename)
        directory = os.path.dirname(old_filepath)
        new_filepath = os.path.join(directory, new_filename)

        # Check if new path already exists
        if os.path.exists(new_filepath):
            raise FileExistsError(f"File already exists: {new_filepath}")

        # Get or create rename history
        rename_history = media_file.deletion_metadata or {}
        if "rename_history" not in rename_history:
            rename_history["rename_history"] = []

        # Add current rename to history
        rename_history["rename_history"].append({
            "old_filename": old_filename,
            "old_filepath": old_filepath,
            "new_filename": new_filename,
            "new_filepath": new_filepath,
            "renamed_at": datetime.now().isoformat(),
            "renamed_by_user_id": user_id
        })

        try:
            # Rename file on disk
            logger.info(f"Renaming: {old_filepath} -> {new_filepath}")
            os.rename(old_filepath, new_filepath)

            # Update database
            media_file.filename = new_filename
            media_file.filepath = new_filepath
            media_file.deletion_metadata = rename_history
            media_file.metadata_updated_at = datetime.now()

            self.db.commit()

            logger.success(f"File renamed: {old_filename} -> {new_filename}")

            return {
                "status": "success",
                "old_path": old_filepath,
                "new_path": new_filepath,
                "old_filename": old_filename,
                "new_filename": new_filename
            }

        except Exception as e:
            logger.error(f"Failed to rename file: {e}")
            self.db.rollback()
            raise

    def batch_rename(
        self,
        file_ids: List[int],
        pattern: Optional[str] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        replace_old: Optional[str] = None,
        replace_new: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Batch rename files using pattern or simple transformations.

        Args:
            file_ids: List of file IDs to rename
            pattern: Optional pattern like "{title} S{season}E{episode}"
            prefix: Optional prefix to add
            suffix: Optional suffix to add (before extension)
            replace_old: String to replace in filename
            replace_new: Replacement string
            user_id: Optional user ID

        Returns:
            Dict with success count, failures, and results
        """
        results = []
        success_count = 0
        failures = []

        for file_id in file_ids:
            media_file = self.db.query(MediaFile).filter(MediaFile.id == file_id).first()

            if not media_file:
                failures.append({"file_id": file_id, "error": "File not found"})
                continue

            try:
                # Generate new filename
                new_filename = self._generate_filename(
                    media_file=media_file,
                    pattern=pattern,
                    prefix=prefix,
                    suffix=suffix,
                    replace_old=replace_old,
                    replace_new=replace_new
                )

                # Rename the file
                result = self.rename_file(media_file, new_filename, user_id)
                results.append(result)
                success_count += 1

            except Exception as e:
                logger.error(f"Failed to rename file {file_id}: {e}")
                failures.append({
                    "file_id": file_id,
                    "filename": media_file.filename,
                    "error": str(e)
                })

        return {
            "success_count": success_count,
            "total": len(file_ids),
            "results": results,
            "failures": failures
        }

    def _generate_filename(
        self,
        media_file: MediaFile,
        pattern: Optional[str] = None,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None,
        replace_old: Optional[str] = None,
        replace_new: Optional[str] = None
    ) -> str:
        """
        Generate new filename based on transformation rules.
        """
        old_filename = media_file.filename
        name_without_ext = os.path.splitext(old_filename)[0]
        extension = os.path.splitext(old_filename)[1]

        # Pattern-based rename
        if pattern:
            new_name = pattern.format(
                title=media_file.parsed_title or "Unknown",
                year=media_file.parsed_year or "",
                season=str(media_file.parsed_season).zfill(2) if media_file.parsed_season else "",
                episode=str(media_file.parsed_episode).zfill(2) if media_file.parsed_episode else "",
                resolution=media_file.resolution or "",
                codec=media_file.video_codec or "",
                quality=media_file.quality_score or 0
            )
            return new_name + extension

        # Simple transformations
        new_name = name_without_ext

        if replace_old and replace_new:
            new_name = new_name.replace(replace_old, replace_new)

        if prefix:
            new_name = prefix + new_name

        if suffix:
            new_name = new_name + suffix

        return new_name + extension

    def get_rename_history(self, file_id: int) -> List[Dict[str, Any]]:
        """Get rename history for a file."""
        media_file = self.db.query(MediaFile).filter(MediaFile.id == file_id).first()

        if not media_file or not media_file.deletion_metadata:
            return []

        return media_file.deletion_metadata.get("rename_history", [])

    def revert_rename(
        self,
        file_id: int,
        history_index: int = -1,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Revert a file to a previous name from history."""
        media_file = self.db.query(MediaFile).filter(MediaFile.id == file_id).first()

        if not media_file:
            raise ValueError("File not found")

        history = self.get_rename_history(file_id)

        if not history:
            raise ValueError("No rename history available")

        # Get the target rename operation
        if history_index < 0:
            history_index = len(history) + history_index

        if history_index < 0 or history_index >= len(history):
            raise ValueError("Invalid history index")

        target_rename = history[history_index]
        old_filename = target_rename["old_filename"]

        # Rename back to old name
        return self.rename_file(media_file, old_filename, user_id)
