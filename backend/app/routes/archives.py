"""API routes for archive management."""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.services.archive_service import ArchiveService
from app.models import ArchiveFile

router = APIRouter(prefix="/archives", tags=["archives"])


# Pydantic schemas
class ArchiveResponse(BaseModel):
    id: int
    filename: str
    filepath: str
    file_size: int
    archive_type: str
    extraction_status: str
    parsed_title: Optional[str]
    parsed_year: Optional[int]
    media_type: Optional[str]
    destination_path: Optional[str]
    extracted_to_path: Optional[str]
    mark_for_deletion_at: Optional[str]
    discovered_at: str

    class Config:
        from_attributes = True


class ArchiveListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    archives: List[ArchiveResponse]


class ScanArchivesRequest(BaseModel):
    paths: Optional[List[str]] = None


class ExtractArchiveRequest(BaseModel):
    destination: Optional[str] = None


@router.post("/scan")
def scan_for_archives(
    request: ScanArchivesRequest,
    db: Session = Depends(get_db)
):
    """Scan NAS paths for archive files (RAR, ZIP, 7z)."""
    service = ArchiveService(db)
    result = service.scan_for_archives(paths=request.paths)
    return result


@router.get("", response_model=ArchiveListResponse)
def list_archives(
    status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """List all archive files with optional filtering."""
    service = ArchiveService(db)
    result = service.list_archives(status=status, limit=limit, skip=skip)
    return result


@router.get("/{archive_id}", response_model=ArchiveResponse)
def get_archive(archive_id: int, db: Session = Depends(get_db)):
    """Get details of a specific archive."""
    archive = db.query(ArchiveFile).filter(ArchiveFile.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")
    return archive


@router.post("/{archive_id}/extract")
def extract_archive(
    archive_id: int,
    request: ExtractArchiveRequest = Body(default={"destination": None}),
    db: Session = Depends(get_db)
):
    """Extract an archive file to its destination path."""
    service = ArchiveService(db)
    success, message = service.extract_archive(archive_id, destination=request.destination)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.post("/{archive_id}/mark-for-deletion")
def mark_archive_for_deletion(archive_id: int, db: Session = Depends(get_db)):
    """Mark archive for immediate deletion (removes 6-month grace period)."""
    service = ArchiveService(db)
    success, message = service.mark_for_deletion(archive_id)

    if not success:
        raise HTTPException(status_code=404, detail=message)

    return {"success": True, "message": message}


@router.delete("/{archive_id}")
def delete_archive(archive_id: int, db: Session = Depends(get_db)):
    """Delete an archive file immediately."""
    archive = db.query(ArchiveFile).filter(ArchiveFile.id == archive_id).first()
    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    try:
        import os
        if os.path.exists(archive.filepath):
            os.remove(archive.filepath)

        db.delete(archive)
        db.commit()

        return {"success": True, "message": "Archive deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete archive: {str(e)}")


@router.post("/cleanup")
def cleanup_old_archives(db: Session = Depends(get_db)):
    """Delete archives that have passed their 6-month retention period."""
    service = ArchiveService(db)
    deleted_count = service.delete_old_archives()

    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} old archives"
    }
