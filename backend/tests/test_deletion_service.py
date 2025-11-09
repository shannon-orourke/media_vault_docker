import importlib
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler


if not hasattr(SQLiteTypeCompiler, "visit_ARRAY"):
    def _visit_array(self, type_, **kw):
        return "TEXT"
    SQLiteTypeCompiler.visit_ARRAY = _visit_array  # type: ignore[attr-defined]
from app.config import get_settings


def setup_service(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("NAS_TEMP_DELETE_PATH", str(tmp_path / "nas-temp"))
    monkeypatch.setenv("LOCAL_TEMP_DELETE_PATH", str(tmp_path / "fallback-temp"))
    monkeypatch.setenv("NAS_MOUNT_PATH", str(tmp_path / "mount"))
    monkeypatch.setenv("NAS_SMB_SHARE", "volume1")

    get_settings.cache_clear()
    import app.services.deletion_service as deletion_service
    deletion_service = importlib.reload(deletion_service)

    from app.database import Base
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session, deletion_service.DeletionService(session)


def create_media(session, **overrides):
    from app.models import MediaFile
    defaults = {
        "filename": "demo.mkv",
        "filepath": "/volume1/video/demo.mkv",
        "file_size": 1024,
        "media_type": "tv",
        "quality_score": 10,
        "is_duplicate": False,
        "discovered_at": datetime.utcnow(),
    }
    defaults.update(overrides)
    media = MediaFile(**defaults)
    session.add(media)
    session.commit()
    session.refresh(media)
    return media


def test_stage_file_handles_missing_source(tmp_path, monkeypatch):
    session, service = setup_service(tmp_path, monkeypatch)
    media = create_media(session, filepath="/volume1/video/missing.mkv")

    pending = service.stage_file_for_deletion(media, reason="cleanup")

    assert pending.temp_filepath is None
    assert pending.deletion_metadata["source_missing"] is True


def test_stage_file_moves_existing_source(tmp_path, monkeypatch):
    session, service = setup_service(tmp_path, monkeypatch)

    mount_file = tmp_path / "mount" / "video" / "demo.mkv"
    mount_file.parent.mkdir(parents=True)
    mount_file.write_bytes(b"demo")

    media = create_media(session)
    pending = service.stage_file_for_deletion(media, reason="cleanup")

    assert pending.temp_filepath
    assert Path(pending.temp_filepath).exists()
    assert not mount_file.exists()
