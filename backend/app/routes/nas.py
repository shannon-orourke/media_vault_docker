"""NAS file browser and scan control endpoints."""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.services.nas_service import NASService
from app.services.scanner_service import ScannerService
from app.models.media import ScanHistory

router = APIRouter(prefix="/nas", tags=["nas"])


class FileItem(BaseModel):
    """File or directory item."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    video_count: Optional[int] = None  # For directories


class BrowseResponse(BaseModel):
    """Response for browsing NAS folders."""
    current_path: str
    parent_path: Optional[str]
    items: List[FileItem]


class ScanRequest(BaseModel):
    """Request to start a scan."""
    paths: List[str]
    scan_type: str = "full"  # full or incremental


class ScanStatusResponse(BaseModel):
    """Scan progress status."""
    scan_id: int
    status: str  # running, completed, failed
    files_found: int
    files_new: int
    files_updated: int
    errors_count: int
    scan_started_at: str
    scan_completed_at: Optional[str]


@router.get("/browse", response_model=BrowseResponse)
async def browse_nas(
    path: str = "/volume1",
    db: Session = Depends(get_db)
):
    """
    Browse NAS folders starting from a given path.

    Args:
        path: Path to browse (relative to NAS mount)

    Returns:
        List of directories and files with metadata
    """
    nas_service = NASService()

    # Get effective path (mount point + relative path)
    effective_path = nas_service.get_effective_path(path, use_nas=False)

    # If path starts with / but doesn't include mount point, prepend it
    if path.startswith("/volume1"):
        effective_path = os.path.join("/mnt/nas-media", path.lstrip("/"))
    elif not path.startswith("/mnt"):
        effective_path = os.path.join("/mnt/nas-media", path.lstrip("/"))

    logger.info(f"Browsing: {effective_path}")

    # Check if path exists
    if not os.path.exists(effective_path):
        raise HTTPException(
            status_code=404,
            detail=f"Path not found: {path}"
        )

    # Check if path is a directory
    if not os.path.isdir(effective_path):
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {path}"
        )

    # Get parent path
    parent_path = None
    if path != "/volume1" and path != "/":
        parent_parts = path.rstrip("/").split("/")
        if len(parent_parts) > 1:
            parent_path = "/".join(parent_parts[:-1]) or "/"

    # List directory contents
    items: List[FileItem] = []
    video_extensions = ['.mkv', '.mp4', '.avi', '.m4v', '.mov', '.wmv', '.flv', '.webm', '.mpg', '.mpeg', '.ts']

    try:
        for entry in sorted(os.listdir(effective_path)):
            # Skip hidden files and system folders
            if entry.startswith('.') or entry in ['@eaDir', '#recycle', 'lost+found']:
                continue

            entry_path = os.path.join(effective_path, entry)
            relative_path = os.path.join(path, entry).replace("/mnt/nas-media", "")

            is_dir = os.path.isdir(entry_path)
            size = None
            video_count = None

            if is_dir:
                # Count video files in directory (non-recursive, for performance)
                try:
                    video_count = sum(
                        1 for f in os.listdir(entry_path)
                        if os.path.isfile(os.path.join(entry_path, f))
                        and any(f.lower().endswith(ext) for ext in video_extensions)
                    )
                except (PermissionError, OSError):
                    video_count = 0
            else:
                try:
                    size = os.path.getsize(entry_path)
                except (PermissionError, OSError):
                    size = 0

            items.append(FileItem(
                name=entry,
                path=relative_path,
                is_directory=is_dir,
                size=size,
                video_count=video_count if is_dir else None
            ))

    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {path}"
        )
    except Exception as e:
        logger.error(f"Error browsing {effective_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error browsing directory: {str(e)}"
        )

    return BrowseResponse(
        current_path=path,
        parent_path=parent_path,
        items=items
    )


@router.post("/scan", response_model=ScanStatusResponse)
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start a scan of selected folders.

    Args:
        request: Scan request with paths and scan type

    Returns:
        Scan status with scan_id
    """
    logger.info(f"Starting scan of {len(request.paths)} paths: {request.paths}")

    # Convert relative paths to absolute if needed
    absolute_paths = []
    for path in request.paths:
        if path.startswith("/volume1"):
            abs_path = os.path.join("/mnt/nas-media", path.lstrip("/"))
        elif path.startswith("/mnt/nas-media"):
            abs_path = path
        else:
            abs_path = os.path.join("/mnt/nas-media", path.lstrip("/"))

        # Verify path exists
        if not os.path.exists(abs_path):
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {path}"
            )

        absolute_paths.append(abs_path)

    # Start scan in background
    scanner = ScannerService(db)

    try:
        scan_history = scanner.scan_nas(
            paths=absolute_paths,
            scan_type=request.scan_type
        )

        return ScanStatusResponse(
            scan_id=scan_history.id,
            status=scan_history.status,
            files_found=scan_history.files_found or 0,
            files_new=scan_history.files_new or 0,
            files_updated=scan_history.files_updated or 0,
            errors_count=scan_history.errors_count or 0,
            scan_started_at=scan_history.scan_started_at.isoformat(),
            scan_completed_at=scan_history.scan_completed_at.isoformat() if scan_history.scan_completed_at else None
        )

    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error starting scan: {str(e)}"
        )


@router.get("/scan/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: int,
    db: Session = Depends(get_db)
):
    """
    Get status of a running or completed scan.

    Args:
        scan_id: Scan history ID

    Returns:
        Scan status
    """
    scan_history = db.query(ScanHistory).filter(ScanHistory.id == scan_id).first()

    if not scan_history:
        raise HTTPException(
            status_code=404,
            detail=f"Scan not found: {scan_id}"
        )

    return ScanStatusResponse(
        scan_id=scan_history.id,
        status=scan_history.status,
        files_found=scan_history.files_found or 0,
        files_new=scan_history.files_new or 0,
        files_updated=scan_history.files_updated or 0,
        errors_count=scan_history.errors_count or 0,
        scan_started_at=scan_history.scan_started_at.isoformat(),
        scan_completed_at=scan_history.scan_completed_at.isoformat() if scan_history.scan_completed_at else None
    )


@router.get("/scan-history", response_model=List[ScanStatusResponse])
async def get_scan_history(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get recent scan history.

    Args:
        limit: Maximum number of scans to return

    Returns:
        List of recent scans
    """
    scans = (
        db.query(ScanHistory)
        .order_by(ScanHistory.scan_started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        ScanStatusResponse(
            scan_id=scan.id,
            status=scan.status,
            files_found=scan.files_found or 0,
            files_new=scan.files_new or 0,
            files_updated=scan.files_updated or 0,
            errors_count=scan.errors_count or 0,
            scan_started_at=scan.scan_started_at.isoformat(),
            scan_completed_at=scan.scan_completed_at.isoformat() if scan.scan_completed_at else None
        )
        for scan in scans
    ]
