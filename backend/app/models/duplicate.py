"""Duplicate detection models."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class DuplicateGroup(Base):
    """Group of duplicate media files."""

    __tablename__ = "duplicate_groups"

    id = Column(Integer, primary_key=True, index=True)
    group_hash = Column(String(128), unique=True, nullable=False, index=True)
    duplicate_type = Column(String(20), nullable=False, index=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    title = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    season = Column(Integer, nullable=True)
    episode = Column(Integer, nullable=True)
    media_type = Column(String(20), nullable=True)
    member_count = Column(Integer, default=0)
    recommended_action = Column(String(20), nullable=True)
    action_reason = Column(Text, nullable=True)
    reviewed = Column(Boolean, default=False, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    members = relationship("DuplicateMember", back_populates="duplicate_group", cascade="all, delete-orphan")
    user_decisions = relationship("UserDecision", back_populates="duplicate_group")


class DuplicateMember(Base):
    """Many-to-many relationship between duplicate groups and media files."""

    __tablename__ = "duplicate_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("duplicate_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=True)
    recommended_action = Column(String(20), nullable=True)
    action_reason = Column(Text, nullable=True)
    quality_score = Column(Numeric(6, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    duplicate_group = relationship("DuplicateGroup", back_populates="members")
    media_file = relationship("MediaFile", back_populates="duplicate_memberships")


class UserDecision(Base):
    """Manual user decisions for duplicate handling."""

    __tablename__ = "user_decisions"

    id = Column(Integer, primary_key=True, index=True)
    duplicate_group_id = Column(Integer, ForeignKey("duplicate_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    action_taken = Column(String(50), nullable=True)
    files_archived = Column(ARRAY(Integer), nullable=True)
    files_deleted = Column(ARRAY(Integer), nullable=True)
    primary_file_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    confidence = Column(String(20), nullable=True)
    decided_at = Column(DateTime(timezone=False), server_default=func.now())

    # Relationships
    duplicate_group = relationship("DuplicateGroup", back_populates="user_decisions")
