import importlib
from pathlib import Path

from app.config import get_settings


def reload_path_utils():
    get_settings.cache_clear()
    import app.utils.path_utils as path_utils
    importlib.reload(path_utils)
    return path_utils


def test_resolve_media_path_maps_to_mount(tmp_path, monkeypatch):
    mount_root = tmp_path / "mnt"
    actual_file = mount_root / "video" / "demo.mkv"
    actual_file.parent.mkdir(parents=True)
    actual_file.write_bytes(b"demo")

    monkeypatch.setenv("NAS_MOUNT_PATH", str(mount_root))
    monkeypatch.setenv("NAS_SMB_SHARE", "volume1")
    monkeypatch.setenv("NAS_TEMP_DELETE_PATH", str(tmp_path / "nas-temp"))
    monkeypatch.setenv("LOCAL_TEMP_DELETE_PATH", str(tmp_path / "local-temp"))

    path_utils = reload_path_utils()
    resolved = path_utils.resolve_media_path("/volume1/video/demo.mkv")
    assert resolved == actual_file


def test_temp_delete_roots_includes_local_fallback(tmp_path, monkeypatch):
    preferred = tmp_path / "preferred"
    monkeypatch.setenv("NAS_TEMP_DELETE_PATH", str(preferred))
    monkeypatch.setenv("LOCAL_TEMP_DELETE_PATH", str(tmp_path / "fallback"))
    monkeypatch.setenv("NAS_SMB_SHARE", "volume1")
    monkeypatch.setenv("NAS_MOUNT_PATH", str(tmp_path / "mount"))

    path_utils = reload_path_utils()
    roots = list(path_utils.temp_delete_roots())
    assert roots[0] == preferred
    assert Path(tmp_path / "fallback") in roots
