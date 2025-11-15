"""Media file and scan history models."""
from sqlalchemy import Column, Integer, String, BigInteger, Numeric, DateTime, Text, Boolean, JSON, Index, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class MediaFile(Base):
    """Media file inventory with complete metadata."""

    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)

    # File identification
    filename = Column(String(500), nullable=False)
    filepath = Column(Text, nullable=False, unique=True, index=True)
    file_size = Column(BigInteger, nullable=False)
    md5_hash = Column(String(32), nullable=True, index=True)

    # Media metadata
    duration = Column(Numeric(10, 2), nullable=True)
    format = Column(String(50), nullable=True)
    video_codec = Column(String(50), nullable=True)
    audio_codec = Column(String(50), nullable=True)
    resolution = Column(String(20), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    bitrate = Column(Integer, nullable=True)
    framerate = Column(Numeric(6, 2), nullable=True)

    # Quality indicators
    quality_tier = Column(String(20), nullable=True)
    hdr_type = Column(String(20), nullable=True)
    audio_channels = Column(Numeric(3, 1), nullable=True)
    audio_track_count = Column(Integer, default=1)
    subtitle_track_count = Column(Integer, default=0)

    # Language tracking (NEW in schema update)
    audio_languages = Column(ARRAY(String), nullable=True)  # ["eng", "spa"]
    subtitle_languages = Column(ARRAY(String), nullable=True)  # ["eng", "fra"]
    dominant_audio_language = Column(String(10), nullable=True)

    # Parsed metadata (guessit)
    parsed_title = Column(String(500), nullable=True)
    parsed_year = Column(Integer, nullable=True)
    parsed_season = Column(Integer, nullable=True)
    parsed_episode = Column(Integer, nullable=True)
    parsed_release_group = Column(String(100), nullable=True)
    media_type = Column(String(50), nullable=True)  # movie, tv, documentary

    # TMDb metadata
    tmdb_id = Column(Integer, nullable=True, index=True)
    tmdb_type = Column(String(20), nullable=True)  # "movie" or "tv"
    tmdb_title = Column(String(500), nullable=True)
    tmdb_year = Column(Integer, nullable=True)
    tmdb_overview = Column(Text, nullable=True)
    tmdb_poster_path = Column(String(500), nullable=True)
    tmdb_rating = Column(Numeric(3, 1), nullable=True)
    tmdb_genres = Column(JSON, nullable=True)
    tmdb_last_updated = Column(DateTime(timezone=True), nullable=True)
    imdb_id = Column(String(20), nullable=True, index=True)

    # Quality score
    quality_score = Column(Integer, nullable=True, index=True)

    # Status
    is_duplicate = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deletion_metadata = Column(JSON, nullable=True)  # For rename history and other metadata

    # Timestamps
    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    duplicate_memberships = relationship("DuplicateMember", back_populates="media_file", cascade="all, delete-orphan")
    pending_deletion = relationship("PendingDeletion", back_populates="media_file", uselist=False)
    archive_operations = relationship("ArchiveOperation", back_populates="media_file")

    # Composite indexes
    __table_args__ = (
        Index("idx_media_parsed_movie", "parsed_title", "parsed_year"),
        Index("idx_media_parsed_tv", "parsed_title", "parsed_season", "parsed_episode"),
        Index("idx_media_type_quality", "media_type", "quality_score"),
    )


class ScanHistory(Base):
    """Track scanning operations."""

    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(String(20), nullable=True)
    nas_paths = Column(ARRAY(String), nullable=True)  # Array of paths
    scan_started_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    scan_completed_at = Column(DateTime(timezone=False), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    files_found = Column(Integer, default=0)
    files_new = Column(Integer, default=0)
    files_updated = Column(Integer, default=0)
    files_deleted = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(JSON, nullable=True)
    status = Column(String(20), default="running", index=True)
    triggered_by = Column(String(50), nullable=True)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
