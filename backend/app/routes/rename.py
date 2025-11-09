"""File renaming routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import MediaFile
from app.services.rename_service import RenameService
from app.services.tmdb_service import TMDBService

router = APIRouter(prefix="/rename", tags=["rename"])


class RenameRequest(BaseModel):
    new_filename: str


class BatchRenameRequest(BaseModel):
    file_ids: List[int]
    pattern: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    replace_old: Optional[str] = None
    replace_new: Optional[str] = None


class TMDBSearchRequest(BaseModel):
    query: Optional[str] = None
    media_type: str = "multi"
    year: Optional[int] = None


class TMDBApplyRequest(BaseModel):
    tmdb_id: int
    media_type: str
    enrich_metadata: bool = True


@router.post("/{file_id}")
def rename_file(
    file_id: int,
    request: RenameRequest,
    db: Session = Depends(get_db)
):
    """Rename a single file."""
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    rename_service = RenameService(db)

    try:
        result = rename_service.rename_file(media_file, request.new_filename)
        return result
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rename failed: {str(e)}")


@router.post("/batch")
def batch_rename(
    request: BatchRenameRequest,
    db: Session = Depends(get_db)
):
    """Batch rename files."""
    rename_service = RenameService(db)

    result = rename_service.batch_rename(
        file_ids=request.file_ids,
        pattern=request.pattern,
        prefix=request.prefix,
        suffix=request.suffix,
        replace_old=request.replace_old,
        replace_new=request.replace_new
    )

    return result


@router.get("/{file_id}/history")
def get_rename_history(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Get rename history for a file."""
    rename_service = RenameService(db)
    history = rename_service.get_rename_history(file_id)

    return {"file_id": file_id, "history": history}


@router.post("/{file_id}/revert")
def revert_rename(
    file_id: int,
    history_index: int = -1,
    db: Session = Depends(get_db)
):
    """Revert to a previous filename."""
    rename_service = RenameService(db)

    try:
        result = rename_service.revert_rename(file_id, history_index)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revert failed: {str(e)}")


@router.post("/{file_id}/tmdb-search")
def tmdb_search(
    file_id: int,
    request: TMDBSearchRequest,
    db: Session = Depends(get_db)
):
    """Search TMDB for a file."""
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    tmdb_service = TMDBService()

    # Use parsed title or provided query
    query = request.query or media_file.parsed_title or media_file.filename

    results = tmdb_service.search_title(
        query=query,
        media_type=request.media_type,
        year=request.year or media_file.parsed_year
    )

    return {"query": query, "results": results}


@router.post("/{file_id}/tmdb-apply")
def tmdb_apply(
    file_id: int,
    request: TMDBApplyRequest,
    db: Session = Depends(get_db)
):
    """Apply TMDB-based rename to a file."""
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    tmdb_service = TMDBService()

    # Get TMDB details
    tmdb_data = tmdb_service.get_details(request.tmdb_id, request.media_type)

    if not tmdb_data:
        raise HTTPException(status_code=404, detail="TMDB data not found")

    # Get episode details if TV show
    episode_data = None
    if request.media_type == "tv" and media_file.parsed_season and media_file.parsed_episode:
        episode_data = tmdb_service.get_tv_episode_details(
            request.tmdb_id,
            media_file.parsed_season,
            media_file.parsed_episode
        )

    # Generate suggested filename
    suggested_filename = tmdb_service.suggest_filename(
        media_file=media_file,
        tmdb_data=tmdb_data,
        media_type=request.media_type,
        episode_data=episode_data
    )

    # Enrich metadata if requested
    if request.enrich_metadata:
        tmdb_service.enrich_metadata(media_file, request.tmdb_id, request.media_type)
        db.commit()

    # Rename the file
    rename_service = RenameService(db)

    try:
        result = rename_service.rename_file(media_file, suggested_filename)
        return {
            **result,
            "tmdb_data": {
                "id": request.tmdb_id,
                "title": tmdb_data.get("title") or tmdb_data.get("name"),
                "overview": tmdb_data.get("overview")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TMDB rename failed: {str(e)}")


@router.post("/batch/tmdb")
def batch_tmdb_rename(
    file_ids: List[int],
    auto_search: bool = True,
    enrich_metadata: bool = True,
    db: Session = Depends(get_db)
):
    """Batch TMDB rename for multiple files (e.g., entire TV season)."""
    tmdb_service = TMDBService()
    rename_service = RenameService(db)

    results = []
    failures = []

    for file_id in file_ids:
        media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

        if not media_file:
            failures.append({"file_id": file_id, "error": "File not found"})
            continue

        try:
            # Auto-search TMDB if enabled
            if auto_search:
                query = media_file.parsed_title or media_file.filename
                search_results = tmdb_service.search_title(query, media_type="tv")

                if not search_results:
                    failures.append({"file_id": file_id, "error": "No TMDB results"})
                    continue

                # Use first result
                tmdb_id = search_results[0]["id"]
                media_type = "tv"

            else:
                # Use existing TMDB ID if available
                if not media_file.tmdb_id:
                    failures.append({"file_id": file_id, "error": "No TMDB ID"})
                    continue

                tmdb_id = media_file.tmdb_id
                media_type = "tv"

            # Get details and rename
            tmdb_data = tmdb_service.get_details(tmdb_id, media_type)

            if not tmdb_data:
                failures.append({"file_id": file_id, "error": "TMDB details not found"})
                continue

            episode_data = None
            if media_file.parsed_season and media_file.parsed_episode:
                episode_data = tmdb_service.get_tv_episode_details(
                    tmdb_id,
                    media_file.parsed_season,
                    media_file.parsed_episode
                )

            suggested_filename = tmdb_service.suggest_filename(
                media_file,
                tmdb_data,
                media_type,
                episode_data
            )

            if enrich_metadata:
                tmdb_service.enrich_metadata(media_file, tmdb_id, media_type)

            result = rename_service.rename_file(media_file, suggested_filename)
            results.append(result)

        except Exception as e:
            failures.append({"file_id": file_id, "error": str(e)})

    db.commit()

    return {
        "success_count": len(results),
        "total": len(file_ids),
        "results": results,
        "failures": failures
    }
