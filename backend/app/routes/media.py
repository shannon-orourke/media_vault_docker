"""Media file routes."""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MediaFile, PendingDeletion
from app.services.deletion_service import DeletionService

router = APIRouter(prefix="/media", tags=["media"])


class BatchDeleteRequest(BaseModel):
    """Request model for staging multiple files for deletion."""
    file_ids: List[int]
    reason: Optional[str] = "Manual delete from UI"


@router.get("/")
def list_media(
    skip: int = 0,
    limit: int = 50,
    media_type: Optional[str] = None,
    is_duplicate: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List media files with optional filters."""
    query = db.query(MediaFile).filter(MediaFile.is_deleted == False)

    if media_type:
        query = query.filter(MediaFile.media_type == media_type)

    if is_duplicate is not None:
        query = query.filter(MediaFile.is_duplicate == is_duplicate)

    total = query.count()
    files = query.order_by(MediaFile.discovered_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "filepath": f.filepath,
                "file_size": f.file_size,
                "md5_hash": f.md5_hash,
                "duration": float(f.duration) if f.duration else None,
                "media_type": f.media_type,
                "quality_tier": f.quality_tier,
                "quality_score": f.quality_score,
                "resolution": f.resolution,
                "video_codec": f.video_codec,
                "audio_codec": f.audio_codec,
                "bitrate": f.bitrate,
                "audio_channels": float(f.audio_channels) if f.audio_channels else None,
                "audio_languages": f.audio_languages,
                "parsed_title": f.parsed_title,
                "parsed_year": f.parsed_year,
                "parsed_season": f.parsed_season,
                "parsed_episode": f.parsed_episode,
                "width": f.width,
                "height": f.height,
                "is_duplicate": f.is_duplicate,
                "discovered_at": f.discovered_at.isoformat(),
                "tmdb_id": f.tmdb_id,
                "tmdb_type": f.tmdb_type,
                "imdb_id": f.imdb_id,
            }
            for f in files
        ]
    }


@router.get("/{file_id}")
def get_media_file(file_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a media file."""
    file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")

    return {
        "id": file.id,
        "filename": file.filename,
        "filepath": file.filepath,
        "file_size": file.file_size,
        "md5_hash": file.md5_hash,
        "duration": float(file.duration) if file.duration else None,
        "format": file.format,
        "video_codec": file.video_codec,
        "audio_codec": file.audio_codec,
        "resolution": file.resolution,
        "width": file.width,
        "height": file.height,
        "bitrate": file.bitrate,
        "framerate": float(file.framerate) if file.framerate else None,
        "quality_tier": file.quality_tier,
        "quality_score": file.quality_score,
        "hdr_type": file.hdr_type,
        "audio_channels": float(file.audio_channels) if file.audio_channels else None,
        "audio_track_count": file.audio_track_count,
        "subtitle_track_count": file.subtitle_track_count,
        "audio_languages": file.audio_languages,
        "subtitle_languages": file.subtitle_languages,
        "dominant_audio_language": file.dominant_audio_language,
        "parsed_title": file.parsed_title,
        "parsed_year": file.parsed_year,
        "media_type": file.media_type,
        "is_duplicate": file.is_duplicate,
        "discovered_at": file.discovered_at.isoformat(),
    }


@router.delete("/{file_id}")
def delete_media_file(file_id: int, db: Session = Depends(get_db)):
    """Stage a media file for deletion by moving it to temp archive."""
    file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not file:
        raise HTTPException(status_code=404, detail="Media file not found")

    if file.pending_deletion:
        return {"status": "pending", "message": "File already pending deletion"}

    # Use deletion service to move file to temp archive
    deletion_service = DeletionService(db)

    try:
        pending = deletion_service.stage_file_for_deletion(
            media_file=file,
            reason="Manual delete from API"
        )

        return {
            "status": "staged",
            "message": f"File moved to {pending.temp_filepath}",
            "pending_deletion_id": pending.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stage file: {str(e)}")


@router.post("/batch-delete")
def batch_delete_files(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """Stage multiple media files for deletion."""
    if not request.file_ids:
        raise HTTPException(status_code=400, detail="file_ids cannot be empty")

    deletion_service = DeletionService(db)
    staged = []
    failures = []

    for file_id in request.file_ids:
        media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

        if not media_file:
            failures.append({"file_id": file_id, "error": "Media file not found"})
            continue

        if media_file.pending_deletion:
            failures.append({"file_id": file_id, "error": "File already pending deletion"})
            continue

        try:
            pending = deletion_service.stage_file_for_deletion(
                media_file=media_file,
                reason=request.reason or "Batch delete via API"
            )
            staged.append({
                "file_id": file_id,
                "pending_deletion_id": pending.id,
                "temp_path": pending.temp_filepath
            })
        except Exception as exc:
            failures.append({"file_id": file_id, "error": str(exc)})

    return {
        "success": len(failures) == 0,
        "staged_count": len(staged),
        "deleted_count": len(staged),
        "failed_count": len(failures),
        "staged": staged,
        "failures": failures
    }


@router.get("/stats/summary")
def get_stats(db: Session = Depends(get_db)):
    """Get library statistics."""
    from sqlalchemy import func

    total_files = db.query(func.count(MediaFile.id)).filter(MediaFile.is_deleted == False).scalar()
    total_size = db.query(func.sum(MediaFile.file_size)).filter(MediaFile.is_deleted == False).scalar() or 0

    by_type = (
        db.query(MediaFile.media_type, func.count(MediaFile.id))
        .filter(MediaFile.is_deleted == False)
        .group_by(MediaFile.media_type)
        .all()
    )

    by_quality = (
        db.query(MediaFile.quality_tier, func.count(MediaFile.id))
        .filter(MediaFile.is_deleted == False)
        .group_by(MediaFile.quality_tier)
        .all()
    )

    duplicates = db.query(func.count(MediaFile.id)).filter(MediaFile.is_duplicate == True).scalar()

    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_gb": round(total_size / (1024**3), 2),
        "by_type": {media_type: count for media_type, count in by_type},
        "by_quality": {quality: count for quality, count in by_quality},
        "duplicates": duplicates,
    }
