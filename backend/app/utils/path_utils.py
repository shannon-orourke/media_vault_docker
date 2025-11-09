"""Helpers for resolving NAS/local file system paths."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger

from app.config import get_settings


def _share_root() -> Optional[Path]:
    """Return the root path representing the NAS share (e.g., /volume1)."""
    settings = get_settings()
    share = settings.nas_smb_share.strip("/") if settings.nas_smb_share else ""
    if not share:
        return None
    return Path("/") / share


def resolve_media_path(original_path: str) -> Optional[Path]:
    """
    Resolve a media file path to a concrete file on disk.

    The scanner records NAS-style paths (e.g., /volume1/video/show.mkv). On
    developer machines the share is usually mounted at ``settings.nas_mount_path``.
    This helper attempts to map the stored path to whichever location currently
    exists.
    """
    settings = get_settings()
    path_obj = Path(original_path)
    candidates: List[Path] = [path_obj]

    share_root = _share_root()
    mount_base = Path(settings.nas_mount_path) if settings.nas_mount_path else None

    if share_root and mount_base and path_obj.is_absolute():
        try:
            relative = path_obj.relative_to(share_root)
            candidates.append(mount_base / relative)
        except ValueError:
            # Path is not under the share root; ignore.
            pass

    dev_fallback = settings.dev_media_fallback_path.strip()
    if dev_fallback:
        fallback_base = Path(dev_fallback)
        if path_obj.is_absolute():
            relative = Path(*path_obj.parts[1:])  # drop leading '/'
            candidates.append(fallback_base / relative)
        else:
            candidates.append(fallback_base / path_obj)

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            if candidate.exists():
                if candidate != path_obj:
                    logger.debug(f"Resolved {original_path} -> {candidate}")
                return candidate
        except Exception as exc:  # pragma: no cover - safety net
            logger.warning(f"Failed to inspect {candidate}: {exc}")
            continue

    return None


def temp_delete_roots() -> Iterable[Path]:
    """
    Generate candidate roots for pending-deletion staging.

    Order:
        1. Configured NAS temp path (e.g., /volume1/video/duplicates_before_purge)
        2. The same path rewritten to the local NAS mount (if applicable)
        3. Local fallback path (LOCAL_TEMP_DELETE_PATH)
    """
    settings = get_settings()
    configured = Path(settings.nas_temp_delete_path)
    candidates: List[Path] = [configured]

    share_root = _share_root()
    mount_base = Path(settings.nas_mount_path) if settings.nas_mount_path else None

    if share_root and mount_base:
        try:
            relative = configured.relative_to(share_root)
            candidates.append(mount_base / relative)
        except ValueError:
            # Configured path is outside of the share root
            pass

    if settings.local_temp_delete_path:
        candidates.append(Path(settings.local_temp_delete_path))

    seen = set()
    for root in candidates:
        if root in seen:
            continue
        seen.add(root)
        yield root
