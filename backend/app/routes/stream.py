"""Video streaming routes with range request support."""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import MediaFile
from app.utils.path_utils import resolve_media_path

router = APIRouter(prefix="/stream", tags=["stream"])


def range_requests_response(
    request: Request,
    file_path: str,
    content_type: str = "video/mp4"
):
    """
    Returns a StreamingResponse with support for HTTP Range requests.

    Args:
        request: FastAPI request object
        file_path: Absolute path to the media file
        content_type: MIME type of the media file

    Returns:
        StreamingResponse with proper range headers
    """
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    if range_header:
        # Parse range header (e.g., "bytes=0-1023")
        byte_range = range_header.strip().lower().replace("bytes=", "")

        if "-" not in byte_range:
            raise HTTPException(status_code=416, detail="Invalid range header")

        start_str, end_str = byte_range.split("-")

        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1

        # Ensure valid range
        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(status_code=416, detail="Range not satisfiable")

        chunk_size = end - start + 1

        def iter_file():
            """Generator to stream file chunks."""
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(8192, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type,
        }

        return StreamingResponse(
            iter_file(),
            status_code=206,  # Partial Content
            headers=headers,
        )

    else:
        # No range header - stream entire file
        def iter_full_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type,
        }

        return StreamingResponse(
            iter_full_file(),
            status_code=200,
            headers=headers,
        )


@router.get("/{file_id}")
def stream_video(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stream a video file with HTTP range request support.

    Args:
        file_id: Media file ID
        request: FastAPI request (for range headers)
        db: Database session

    Returns:
        StreamingResponse with video data
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    resolved_path = resolve_media_path(media_file.filepath)

    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Determine content type based on file extension
    ext = os.path.splitext(media_file.filename)[1].lower()
    content_type_map = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".m4v": "video/x-m4v",
        ".wmv": "video/x-ms-wmv",
        ".flv": "video/x-flv",
        ".mpg": "video/mpeg",
        ".mpeg": "video/mpeg",
        ".ts": "video/mp2t",
    }

    content_type = content_type_map.get(ext, "video/mp4")

    return range_requests_response(
        request=request,
        file_path=str(resolved_path),
        content_type=content_type
    )


@router.head("/{file_id}")
def stream_video_head(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    HEAD request for video metadata (for player preflight checks).

    Args:
        file_id: Media file ID
        db: Database session

    Returns:
        Response with headers but no body
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    resolved_path = resolve_media_path(media_file.filepath)

    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    from fastapi.responses import Response

    file_size = resolved_path.stat().st_size
    ext = os.path.splitext(media_file.filename)[1].lower()

    content_type_map = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".m4v": "video/x-m4v",
        ".wmv": "video/x-ms-wmv",
        ".flv": "video/x-flv",
        ".mpg": "video/mpeg",
        ".mpeg": "video/mpeg",
        ".ts": "video/mp2t",
    }

    content_type = content_type_map.get(ext, "video/mp4")

    return Response(
        status_code=200,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type,
        }
    )
