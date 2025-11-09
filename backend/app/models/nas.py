"""NAS configuration model."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func

from app.database import Base


class NASConfig(Base):
    """NAS connection configuration."""

    __tablename__ = "nas_config"

    id = Column(Integer, primary_key=True, index=True)
    nas_name = Column(String(100), nullable=False)
    nas_host = Column(String(255), nullable=False)
    nas_port = Column(Integer, default=445)
    nas_share = Column(String(255), nullable=False)
    nas_username = Column(String(255), nullable=False)
    nas_password_encrypted = Column(Text, nullable=True)  # Store encrypted
    mount_point = Column(String(500), nullable=True)
    is_mounted = Column(Boolean, default=False)
    last_mount_attempt = Column(DateTime(timezone=True), nullable=True)
    scan_paths = Column(JSON, nullable=True)  # Array of paths to scan
    archive_path = Column(String(500), nullable=True)
    connection_status = Column(String(50), default="not_tested")
    last_connection_test = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
