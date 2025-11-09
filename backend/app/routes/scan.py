"""Scan routes for NAS file discovery."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.services.scanner_service import ScannerService
from app.services.dedup_service import DeduplicationService
from app.models import ScanHistory

router = APIRouter(prefix="/scan", tags=["scan"])


class ScanRequest(BaseModel):
    """Request model for starting a scan."""
    paths: Optional[List[str]] = None
    scan_type: str = "full"  # full or incremental


class ScanResponse(BaseModel):
    """Response model for scan operation."""
    scan_id: int
    scan_type: str
    status: str
    files_found: int
    files_new: int
    files_updated: int
    errors_count: int
    message: str


@router.post("/start", response_model=ScanResponse)
def start_scan(
    request: ScanRequest,
    db: Session = Depends(get_db)
):
    """Start a NAS scan operation."""
    try:
        scanner = ScannerService(db)
        scan_history = scanner.scan_nas(
            paths=request.paths,
            scan_type=request.scan_type
        )

        return ScanResponse(
            scan_id=scan_history.id,
            scan_type=scan_history.scan_type,
            status=scan_history.status,
            files_found=scan_history.files_found,
            files_new=scan_history.files_new,
            files_updated=scan_history.files_updated,
            errors_count=scan_history.errors_count,
            message=f"Scan completed: {scan_history.files_new} new, {scan_history.files_updated} updated"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deduplicate")
def run_deduplication(db: Session = Depends(get_db)):
    """Run duplicate detection on scanned files."""
    try:
        dedup = DeduplicationService(db)

        # Find exact duplicates
        exact_groups = dedup.find_exact_duplicates()

        # Find fuzzy duplicates
        fuzzy_groups = dedup.find_fuzzy_duplicates()

        total_groups = len(exact_groups) + len(fuzzy_groups)
        total_members = sum(group.member_count or 0 for group in exact_groups + fuzzy_groups)

        return {
            "exact_duplicates": len(exact_groups),
            "fuzzy_duplicates": len(fuzzy_groups),
            "groups_created": total_groups,
            "total_members": total_members,
            "message": f"Found {len(exact_groups)} exact and {len(fuzzy_groups)} fuzzy duplicate groups"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_scan_history(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get scan history."""
    scans = (
        db.query(ScanHistory)
        .order_by(ScanHistory.scan_started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": scan.id,
            "scan_type": scan.scan_type,
            "nas_paths": scan.nas_paths,
            "scan_started_at": scan.scan_started_at.isoformat(),
            "scan_completed_at": scan.scan_completed_at.isoformat() if scan.scan_completed_at else None,
            "status": scan.status,
            "files_found": scan.files_found,
            "files_new": scan.files_new,
            "files_updated": scan.files_updated,
            "errors_count": scan.errors_count,
        }
        for scan in scans
    ]
