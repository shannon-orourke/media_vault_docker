"""Duplicate management routes."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DuplicateGroup, DuplicateMember, MediaFile, UserDecision

router = APIRouter(prefix="/duplicates", tags=["duplicates"])


def serialize_group(group: DuplicateGroup) -> dict:
    """Serialize a duplicate group with minimal metadata."""
    return {
        "id": group.id,
        "title": group.title,
        "year": group.year,
        "media_type": group.media_type,
        "duplicate_type": group.duplicate_type,
        "confidence": float(group.confidence) if group.confidence is not None else None,
        "member_count": group.member_count,
        "recommended_action": group.recommended_action,
        "action_reason": group.action_reason,
        "detected_at": group.detected_at.isoformat() if group.detected_at else None,
    }


def serialize_member(member: DuplicateMember, file: MediaFile) -> dict:
    """Serialize a duplicate member with associated media file info."""
    return {
        "rank": member.rank or 0,
        "recommended_action": member.recommended_action or "review",
        "action_reason": member.action_reason,
        "file": {
            "id": file.id,
            "filename": file.filename,
            "filepath": file.filepath,
            "file_size": file.file_size,
            "quality_tier": file.quality_tier,
            "quality_score": file.quality_score,
            "resolution": file.resolution,
            "video_codec": file.video_codec,
            "audio_codec": file.audio_codec,
            "hdr_type": file.hdr_type,
            "audio_languages": file.audio_languages,
        },
    }


@router.get("/groups")
def list_duplicate_groups(
    skip: int = 0,
    limit: int = 50,
    recommended_action: str = None,
    db: Session = Depends(get_db)
):
    """List duplicate groups."""
    query = db.query(DuplicateGroup)

    if recommended_action:
        query = query.filter(DuplicateGroup.recommended_action == recommended_action)

    total = query.count()
    groups = query.order_by(DuplicateGroup.detected_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "groups": [serialize_group(g) for g in groups]
    }


@router.get("/groups/{group_id}")
def get_duplicate_group(group_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a duplicate group."""
    group = db.query(DuplicateGroup).filter(DuplicateGroup.id == group_id).first()

    if not group:
        raise HTTPException(status_code=404, detail="Duplicate group not found")

    # Get members with media file details
    members = (
        db.query(DuplicateMember, MediaFile)
        .join(MediaFile, DuplicateMember.file_id == MediaFile.id)
        .filter(DuplicateMember.group_id == group_id)
        .order_by(DuplicateMember.quality_rank)
        .all()
    )

    return {
        **serialize_group(group),
        "members": [
            serialize_member(member, file)
            for member, file in members
        ],
    }


@router.post("/{group_id}/keep/{file_id}")
def mark_keeper(group_id: int, file_id: int, db: Session = Depends(get_db)):
    """Mark a file as the keeper within a duplicate group."""
    group = (
        db.query(DuplicateGroup)
        .filter(DuplicateGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(status_code=404, detail="Duplicate group not found")

    members = (
        db.query(DuplicateMember)
        .filter(DuplicateMember.group_id == group_id)
        .all()
    )

    if not any(m.file_id == file_id for m in members):
        raise HTTPException(status_code=404, detail="File not part of duplicate group")

    for member in members:
        if member.file_id == file_id:
            member.recommended_action = "keep"
            member.action_reason = "Marked as keeper by user"
        else:
            member.recommended_action = "delete"
            member.action_reason = "Lower ranked duplicate after manual review"

    group.recommended_action = "manual_review"
    group.action_reason = "User selected keeper"
    group.reviewed = True
    group.reviewed_at = datetime.utcnow()

    decision = UserDecision(
        duplicate_group_id=group_id,
        user_id=None,
        action_taken="keeper_selected",
        files_deleted=[m.file_id for m in members if m.file_id != file_id],
        primary_file_id=file_id,
        notes="Manual keeper selection",
        confidence="reviewed"
    )
    db.add(decision)
    db.commit()

    return {"status": "ok"}


@router.delete("/{group_id}")
def dismiss_group(group_id: int, db: Session = Depends(get_db)):
    """Dismiss a duplicate group from further review."""
    group = db.query(DuplicateGroup).filter(DuplicateGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Duplicate group not found")

    group.reviewed = True
    group.reviewed_at = datetime.utcnow()
    group.recommended_action = "dismissed"
    group.action_reason = "Dismissed by user"

    decision = UserDecision(
        duplicate_group_id=group_id,
        user_id=None,
        action_taken="dismissed",
        files_archived=[],
        files_deleted=[],
        notes="Dismissed via UI",
        confidence="acknowledged"
    )
    db.add(decision)
    db.commit()

    return {"status": "ok"}
