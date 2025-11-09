"""SQLAlchemy models for archive management."""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class ArchiveFile(Base):
    """Model for tracking RAR/ZIP archives."""

    __tablename__ = "archive_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    filepath = Column(Text, nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    archive_type = Column(String(20), nullable=False)  # 'rar', 'zip', '7z'

    # Extraction status
    extraction_status = Column(String(20), default="pending")  # 'pending', 'extracted', 'failed', 'skipped'
    extracted_at = Column(DateTime, nullable=True)
    extraction_error = Column(Text, nullable=True)

    # Parsed metadata
    parsed_title = Column(String(500), nullable=True)
    parsed_year = Column(Integer, nullable=True)
    parsed_season = Column(Integer, nullable=True)
    parsed_episode = Column(Integer, nullable=True)
    media_type = Column(String(50), nullable=True)  # 'movie', 'tv', 'unknown'

    # Destination paths
    destination_path = Column(Text, nullable=True)
    extracted_to_path = Column(Text, nullable=True)

    # Retention tracking
    mark_for_deletion_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    keep_for_seeding = Column(Boolean, default=True)

    # Timestamps
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contents = relationship("ArchiveContent", back_populates="archive", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("media_type IN ('movie', 'tv', 'unknown')", name="check_media_type"),
    )

    def set_deletion_date(self, months: int = 6):
        """Set deletion date to N months from now (default 6 for seeding quota)."""
        self.mark_for_deletion_at = datetime.utcnow() + timedelta(days=30 * months)

    def __repr__(self):
        return f"<ArchiveFile {self.filename} ({self.extraction_status})>"


class ArchiveContent(Base):
    """Model for tracking individual files extracted from archives."""

    __tablename__ = "archive_contents"

    id = Column(Integer, primary_key=True, index=True)
    archive_id = Column(Integer, ForeignKey("archive_files.id", ondelete="CASCADE"), nullable=False)

    # File information
    filename = Column(String(500), nullable=False)
    relative_path = Column(Text, nullable=True)
    extracted_path = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=True)

    # Link to media_files if it's a video
    media_file_id = Column(Integer, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    extracted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    archive = relationship("ArchiveFile", back_populates="contents")
    media_file = relationship("MediaFile")

    def __repr__(self):
        return f"<ArchiveContent {self.filename} from archive {self.archive_id}>"
