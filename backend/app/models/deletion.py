"""Deletion and archive models."""
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class PendingDeletion(Base):
    """Staging area for files pending manual deletion approval."""

    __tablename__ = "pending_deletions"

    id = Column(Integer, primary_key=True, index=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    original_filepath = Column(Text, nullable=False)
    temp_filepath = Column(Text, nullable=True)  # Path in duplicates_before_purge
    file_size = Column(BigInteger, nullable=False)
    reason = Column(Text, nullable=False)
    duplicate_group_id = Column(Integer, nullable=True)
    better_quality_file_id = Column(Integer, nullable=True)  # Reference to file we're keeping
    quality_score_diff = Column(Integer, nullable=True)
    language_concern = Column(Integer, default=False)  # Flag if English audio would be lost
    language_concern_reason = Column(Text, nullable=True)
    staged_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    approved_for_deletion = Column(Integer, default=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_user_id = Column(Integer, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deletion_metadata = Column(JSON, nullable=True)

    # Relationships
    media_file = relationship("MediaFile", back_populates="pending_deletion")


class ArchiveOperation(Base):
    """Track file move/archive operations."""

    __tablename__ = "archive_operations"

    id = Column(Integer, primary_key=True, index=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type = Column(String(50), nullable=False)  # move_to_temp, restore, permanent_delete
    source_path = Column(Text, nullable=False)
    destination_path = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=False)
    success = Column(Integer, default=True)
    error_message = Column(Text, nullable=True)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    performed_by_user_id = Column(Integer, nullable=True)
    operation_metadata = Column(JSON, nullable=True)

    # Relationships
    media_file = relationship("MediaFile", back_populates="archive_operations")
