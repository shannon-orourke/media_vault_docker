"""Pending deletion management routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.deletion_service import DeletionService

router = APIRouter(prefix="/deletions", tags=["deletions"])


@router.get("/pending")
def list_pending_deletions(
    skip: int = 0,
    limit: int = 50,
    language_concern: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all pending deletions."""
    deletion_service = DeletionService(db)
    return deletion_service.get_pending_deletions(
        skip=skip,
        limit=limit,
        language_concern=language_concern
    )


@router.post("/{pending_id}/approve")
def approve_deletion(
    pending_id: int,
    db: Session = Depends(get_db)
):
    """Approve a pending deletion for permanent removal."""
    deletion_service = DeletionService(db)

    success = deletion_service.approve_deletion(pending_id, user_id=None)

    if not success:
        raise HTTPException(status_code=404, detail="Pending deletion not found or approval failed")

    return {"status": "approved", "message": "File will be permanently deleted"}


@router.post("/{pending_id}/restore")
def restore_file(
    pending_id: int,
    db: Session = Depends(get_db)
):
    """Restore a file from pending deletion."""
    deletion_service = DeletionService(db)

    success = deletion_service.restore_file(pending_id, user_id=None)

    if not success:
        raise HTTPException(status_code=404, detail="Pending deletion not found or restore failed")

    return {"status": "restored", "message": "File restored to original location"}


@router.post("/cleanup")
def cleanup_old_pending(db: Session = Depends(get_db)):
    """Clean up old pending deletions past retention period."""
    deletion_service = DeletionService(db)
    count = deletion_service.cleanup_old_pending_deletions()

    return {
        "status": "cleaned",
        "deleted": count,
        "message": f"Cleaned up {count} old pending deletions"
    }
