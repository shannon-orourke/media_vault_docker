import os
import sys
import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def env_settings(monkeypatch):
    """Provide required environment variables for settings during tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("NAS_SMB_PASSWORD", "password")
    monkeypatch.setenv("NAS_TEMP_DELETE_PATH", "/tmp/mediavault-temp")
    monkeypatch.setenv("NAS_MOUNT_PATH", "/mnt/nas-media")
    monkeypatch.setenv("LOCAL_TEMP_DELETE_PATH", "/tmp/mediavault-local")
    monkeypatch.setenv("NAS_SMB_SHARE", "volume1")
    monkeypatch.setenv("TMDB_API_KEY", "tmdb-key")
    monkeypatch.setenv("TMDB_READ_ACCESS_TOKEN", "token")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "azure-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com")
