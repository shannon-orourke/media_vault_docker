"""Video streaming routes with range request support."""
import os
import tempfile
import subprocess
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.database import get_db
from app.models import MediaFile
from app.utils.path_utils import resolve_media_path
from app.services.ffmpeg_service import FFmpegService
from app.services.hls_service_simple import HLSServiceSimple
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/stream", tags=["stream"])

# Initialize services
ffmpeg_service = FFmpegService()
hls_service = HLSServiceSimple()  # Using simple version for testing


@router.get("/gpu-status")
def get_gpu_status():
    """
    Check if GPU encoding (NVENC) is available.

    Returns:
        GPU status information
    """
    gpu_available = ffmpeg_service.check_gpu_encoding_available()

    return {
        "gpu_encoding_available": gpu_available,
        "encoder": "h264_nvenc" if gpu_available else "libx264 (CPU)",
        "hardware": "NVIDIA NVENC" if gpu_available else "CPU",
        "status": "ready" if gpu_available else "cpu_fallback"
    }


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


@router.get("/{file_id}/transcode")
def stream_transcoded_video(
    file_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    width: int = 1280,
    height: int = 720,
    use_gpu: bool = True,
    db: Session = Depends(get_db)
):
    """
    Stream a GPU-transcoded version of the video for smooth web playback.

    This endpoint transcodes the video on-the-fly using NVIDIA NVENC
    hardware acceleration, which is much faster than CPU encoding.

    Args:
        file_id: Media file ID
        width: Target width (default 1280)
        height: Target height (default 720)
        use_gpu: Use GPU acceleration (default True)
        request: FastAPI request
        background_tasks: Background task handler
        db: Database session

    Returns:
        StreamingResponse with transcoded H.264 video
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    resolved_path = resolve_media_path(media_file.filepath)

    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Create temporary output file
    temp_dir = Path(tempfile.gettempdir()) / "mediavault_transcodes"
    temp_dir.mkdir(exist_ok=True)

    output_file = temp_dir / f"transcode_{file_id}_{width}x{height}.mp4"

    # Transcode with GPU acceleration
    logger.info(f"Transcoding {media_file.filename} with {'GPU' if use_gpu else 'CPU'}...")

    success = ffmpeg_service.transcode_for_streaming_gpu(
        input_path=str(resolved_path),
        output_path=str(output_file),
        width=width,
        height=height,
        use_gpu=use_gpu
    )

    if not success:
        raise HTTPException(status_code=500, detail="Transcoding failed")

    # Schedule cleanup of temp file after streaming completes
    def cleanup():
        try:
            if output_file.exists():
                output_file.unlink()
                logger.info(f"Cleaned up temp file: {output_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file: {e}")

    background_tasks.add_task(cleanup)

    # Stream the transcoded file with range support
    return range_requests_response(
        request=request,
        file_path=str(output_file),
        content_type="video/mp4"
    )


@router.get("/{file_id}/preview")
def stream_preview_clip(
    file_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    start_time: str = "00:00:10",
    duration: int = 30,
    use_gpu: bool = True,
    db: Session = Depends(get_db)
):
    """
    Generate and stream a short preview clip with GPU acceleration.

    Creates a 30-second clip from the video, useful for quick previews
    in the comparison UI without transcoding the entire file.

    Args:
        file_id: Media file ID
        start_time: Start timestamp (HH:MM:SS)
        duration: Clip duration in seconds (default 30)
        use_gpu: Use GPU acceleration (default True)
        request: FastAPI request
        background_tasks: Background task handler
        db: Database session

    Returns:
        StreamingResponse with preview clip
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    resolved_path = resolve_media_path(media_file.filepath)

    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Create temporary preview file
    temp_dir = Path(tempfile.gettempdir()) / "mediavault_previews"
    temp_dir.mkdir(exist_ok=True)

    preview_file = temp_dir / f"preview_{file_id}_{start_time.replace(':', '-')}_{duration}s.mp4"

    # Generate preview with GPU
    logger.info(f"Generating preview for {media_file.filename} with {'GPU' if use_gpu else 'CPU'}...")

    success = ffmpeg_service.create_preview_clip_gpu(
        input_path=str(resolved_path),
        output_path=str(preview_file),
        start_time=start_time,
        duration=duration,
        use_gpu=use_gpu
    )

    if not success:
        raise HTTPException(status_code=500, detail="Preview generation failed")

    # Schedule cleanup
    def cleanup():
        try:
            if preview_file.exists():
                preview_file.unlink()
                logger.info(f"Cleaned up preview file: {preview_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup preview: {e}")

    background_tasks.add_task(cleanup)

    return range_requests_response(
        request=request,
        file_path=str(preview_file),
        content_type="video/mp4"
    )


@router.get("/{file_id}/hls/master.m3u8")
def serve_hls_master_playlist(
    file_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Serve HLS master playlist for adaptive streaming.

    Automatically generates HLS segments if not already available.
    Supports multiple quality levels (480p, 720p, 1080p).

    Args:
        file_id: Media file ID
        background_tasks: Background task handler
        db: Database session

    Returns:
        Master playlist (.m3u8) for adaptive streaming
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    resolved_path = resolve_media_path(media_file.filepath)

    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Check if HLS is already generated
    if not hls_service.is_hls_ready(file_id):
        # Check if generation is in progress
        if hls_service.is_generating(file_id):
            raise HTTPException(status_code=202, detail="HLS generation in progress, retry in a few seconds")

        # Start HLS generation in background
        logger.info(f"Starting HLS generation for file {file_id}: {media_file.filename}")

        success = hls_service.generate_hls_simple(
            input_path=str(resolved_path),
            file_id=file_id,
            width=1280,
            height=720,
            bitrate="4000k",
            use_gpu=True
        )

        if not success:
            raise HTTPException(status_code=500, detail="HLS generation failed")

        # Schedule cleanup task
        background_tasks.add_task(hls_service.cleanup_old_segments)

    # Serve playlist
    playlist_path = hls_service.get_playlist_file(file_id)

    if not playlist_path:
        raise HTTPException(status_code=500, detail="Playlist not found after generation")

    return FileResponse(
        path=str(playlist_path),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/{file_id}/hls/{quality}/playlist.m3u8")
def serve_hls_quality_playlist(
    file_id: int,
    quality: str,
    db: Session = Depends(get_db)
):
    """
    Serve quality-specific HLS playlist.

    Args:
        file_id: Media file ID
        quality: Quality level (480p, 720p, 1080p)
        db: Database session

    Returns:
        Quality-specific playlist (.m3u8)
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    # Validate quality
    if quality not in ["480p", "720p", "1080p"]:
        raise HTTPException(status_code=400, detail="Invalid quality level")

    # Get playlist
    playlist_path = hls_service.get_playlist_file(file_id, quality=quality)

    if not playlist_path:
        raise HTTPException(status_code=404, detail=f"Playlist not found for quality {quality}")

    return FileResponse(
        path=str(playlist_path),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/{file_id}/hls/{segment}")
def serve_hls_segment(
    file_id: int,
    segment: str,
    db: Session = Depends(get_db)
):
    """
    Serve HLS video segment.

    Args:
        file_id: Media file ID
        segment: Segment filename (e.g., segment_000.ts)
        db: Database session

    Returns:
        Video segment (.ts file)
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    # Validate segment filename (security check)
    if not segment.endswith(".ts") or "/" in segment or "\\" in segment:
        raise HTTPException(status_code=400, detail="Invalid segment name")

    # Get segment file
    segment_path = hls_service.get_segment_file(file_id, segment)

    if not segment_path:
        raise HTTPException(status_code=404, detail="Segment not found")

    return FileResponse(
        path=str(segment_path),
        media_type="video/mp2t",
        headers={
            "Cache-Control": "max-age=3600",  # Cache segments for 1 hour
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.options("/{file_id}/progressive")
def progressive_stream_options():
    """Handle OPTIONS preflight for CORS."""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400"
        }
    )


@router.head("/{file_id}/progressive")
def progressive_stream_head(file_id: int, db: Session = Depends(get_db)):
    """Handle HEAD requests for progressive streaming."""
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()
    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    from fastapi.responses import Response
    return Response(
        status_code=200,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "none",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/{file_id}/progressive")
def progressive_stream(
    file_id: int,
    width: int = 1280,
    height: int = 720,
    quality: int = 23,
    use_gpu: bool = True,
    db: Session = Depends(get_db)
):
    """
    Progressive streaming with on-the-fly GPU transcoding (Plex-style).

    Starts FFmpeg and streams output while transcoding is in progress.
    Uses fragmented MP4 for instant playback (2-3 seconds to start).

    Args:
        file_id: Media file ID
        width: Target width (default 1280)
        height: Target height (default 720)
        quality: CRF quality 18-28 (default 23)
        use_gpu: Use GPU NVENC encoding (default True)
        db: Database session

    Returns:
        StreamingResponse with video/mp4
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    resolved_path = resolve_media_path(media_file.filepath)

    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Build FFmpeg command for progressive streaming
    cmd = [settings.ffmpeg_path]

    if use_gpu:
        cmd.extend([
            "-hwaccel", "cuda",
            "-hwaccel_output_format", "cuda"
        ])

    cmd.extend(["-i", str(resolved_path)])

    if use_gpu:
        cmd.extend([
            "-vf", f"scale_cuda={width}:{height}",
            "-c:v", "h264_nvenc",
            "-preset", "p4",  # NVENC preset
            "-cq", str(quality)
        ])
    else:
        cmd.extend([
            "-vf", f"scale={width}:{height}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(quality)
        ])

    # Audio transcoding (DTS → AAC)
    cmd.extend([
        "-c:a", "aac",
        "-b:a", "128k",
        "-ac", "2",  # Stereo
        "-ar", "48000"
    ])

    # KEY: Fragmented MP4 for progressive streaming
    cmd.extend([
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4",
        "-"  # Output to stdout (pipe)
    ])

    logger.info(f"Starting progressive stream for {media_file.filename} ({width}x{height}, GPU={use_gpu})")

    def generate():
        """Generator that yields FFmpeg output chunks."""
        process = None
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=8192
            )

            # Stream chunks as they're produced
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                yield chunk

        except Exception as e:
            logger.error(f"Progressive stream error: {e}")
            if process:
                process.kill()
            raise

        finally:
            if process:
                process.wait(timeout=5)
                if process.returncode != 0 and process.returncode is not None:
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    logger.error(f"FFmpeg error: {stderr[-500:]}")

    return StreamingResponse(
        generate(),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "none",  # No seeking during active transcode
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.options("/{file_id}/smart")
def smart_stream_options():
    """Handle OPTIONS preflight for CORS."""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400"
        }
    )


@router.head("/{file_id}/smart")
def smart_stream_head(file_id: int, db: Session = Depends(get_db)):
    """Handle HEAD requests for smart streaming."""
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()
    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    # PROOF OF CONCEPT: Handle HEAD for pre-transcoded file
    if file_id == 275:
        from pathlib import Path
        cached_file = Path("/tmp/mediavault_cache/episode_275_cached.mp4")
        if cached_file.exists():
            file_size = cached_file.stat().st_size
            from fastapi.responses import Response
            return Response(
                status_code=200,
                media_type="video/mp4",
                headers={
                    "Content-Length": str(file_size),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*"
                }
            )

    from fastapi.responses import Response
    return Response(
        status_code=200,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "none",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/{file_id}/smart")
def smart_stream(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Smart streaming endpoint that auto-selects best method.

    - Direct stream if browser-compatible (H.264 + AAC + MP4)
    - Progressive transcode if incompatible (DTS audio, etc.)

    Args:
        file_id: Media file ID
        request: FastAPI request
        db: Database session

    Returns:
        StreamingResponse with appropriate streaming method
    """
    media_file = db.query(MediaFile).filter(MediaFile.id == file_id).first()

    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    resolved_path = resolve_media_path(media_file.filepath)

    if not resolved_path or not resolved_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # PROOF OF CONCEPT: Serve pre-transcoded file for episode 275
    if file_id == 275:
        from pathlib import Path
        cached_file = Path("/tmp/mediavault_cache/episode_275_cached.mp4")
        if cached_file.exists():
            logger.info(f"[POC] Serving pre-transcoded cache for file {file_id}")
            from fastapi.responses import FileResponse
            return FileResponse(
                path=str(cached_file),
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*"
                }
            )

    # Check codec compatibility
    compat = ffmpeg_service.is_browser_compatible(
        video_codec=media_file.video_codec,
        audio_codec=media_file.audio_codec,
        container_format=media_file.format
    )

    logger.info(f"Smart stream for {media_file.filename}: {compat['recommendation']}")

    if compat['recommendation'] == "direct_stream":
        # Direct stream the original file with range support
        return stream_video(file_id=file_id, request=request, db=db)

    else:
        # Progressive transcode with GPU
        logger.info(f"Starting GPU transcode for {media_file.filename} (incompatible audio: {media_file.audio_codec})")

        # Use original resolution
        width = media_file.width or 1280
        height = media_file.height or 720

        # Build FFmpeg command for progressive streaming
        cmd = [settings.ffmpeg_path]
        cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        cmd.extend(["-i", str(resolved_path)])
        cmd.extend([
            "-vf", f"scale_cuda={width}:{height}",
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-cq", "23"
        ])
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "128k",
            "-ac", "2",
            "-ar", "48000"
        ])
        cmd.extend([
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-f", "mp4",
            "pipe:1"  # Explicitly use pipe instead of "-"
        ])

        def generate():
            """Generator that yields FFmpeg output chunks."""
            process = None
            try:
                logger.info(f"Starting FFmpeg: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )
                logger.info(f"FFmpeg process started: PID {process.pid}")

                # Just read and yield chunks - simple and non-blocking
                while True:
                    chunk = process.stdout.read(8192)
                    if not chunk:
                        logger.info("FFmpeg stream ended")
                        break
                    yield chunk

            except Exception as e:
                logger.error(f"Smart stream error: {e}", exc_info=True)
                if process and process.poll() is None:
                    process.kill()
                raise

            finally:
                if process and process.poll() is None:
                    logger.info("Terminating FFmpeg process")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except:
                        logger.warning("FFmpeg did not terminate, killing")
                        process.kill()

                if process and process.returncode not in [0, None, -15]:  # -15 is SIGTERM
                    try:
                        stderr = process.stderr.read().decode('utf-8', errors='ignore')
                        logger.error(f"FFmpeg final error (code {process.returncode}): {stderr[-500:]}")
                    except:
                        pass

        return StreamingResponse(
            generate(),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "none",
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*"
            }
        )
