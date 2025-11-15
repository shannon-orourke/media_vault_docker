# NAS Folder Browser Feature

**Created:** 2025-11-10
**Status:** Complete - Ready for testing

## Overview

The NAS Folder Browser feature allows users to navigate the Synology NAS file system through a web interface and select specific folders to scan for media files. This provides a user-friendly alternative to manually configuring scan paths in the backend configuration.

## Features Implemented

### Backend API Endpoints

**File:** `backend/app/routes/nas.py`

1. **`GET /api/nas/browse?path=<path>`**
   - Browse folders on the NAS
   - Returns list of directories and files with metadata
   - Shows video file counts for directories
   - Provides breadcrumb navigation

2. **`POST /api/nas/scan`**
   - Start a scan of selected folders
   - Accepts array of paths to scan
   - Returns scan status with scan_id
   - Runs asynchronously

3. **`GET /api/nas/scan/{scan_id}`**
   - Get status of running or completed scan
   - Returns progress information
   - Poll this endpoint for real-time updates

4. **`GET /api/nas/scan-history`**
   - Get recent scan history
   - Shows last 10 scans by default
   - Useful for tracking scan operations

### Frontend Component

**File:** `frontend/src/components/NASFolderBrowser.tsx`

**Features:**
- **Folder Navigation:** Browse NAS directories with breadcrumb navigation
- **File Listing:** See folders and files with video counts
- **Multi-Select:** Check multiple folders to scan
- **Real-Time Progress:** Live scan status updates
- **Responsive UI:** Clean, modern interface using Mantine components

**UI Elements:**
- Breadcrumb navigation for current path
- Back button to navigate up
- Folder/file table with:
  - Checkboxes for folder selection
  - Folder/file icons
  - Video count badges
  - File size information
- Scan button showing selected folder count
- Progress display during scanning:
  - Files found
  - New files added
  - Updated files
  - Error count
- Success/failure alerts

### Settings Page Integration

**File:** `frontend/src/pages/Settings.tsx`

The folder browser is integrated as the first card on the Settings page, making it easily accessible for users to:
1. Browse the NAS
2. Select folders
3. Initiate scans
4. Monitor scan progress

## Usage

### Starting the Backend

```bash
cd /home/mercury/projects/mediavault/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8007
```

### Starting the Frontend

```bash
cd /home/mercury/projects/mediavault/frontend
npm run dev
```

### Using the Folder Browser

1. Navigate to **Settings** page
2. At the top, you'll see **"Browse & Scan Folders"**
3. The browser starts at `/volume1`
4. Click on folders to navigate into them
5. Check the boxes next to folders you want to scan
6. Click **"Scan Selected (X)"** button
7. Watch the progress bar for real-time updates
8. View scan results when complete

## API Examples

### Browse a Folder

```bash
curl "http://localhost:8007/api/nas/browse?path=/volume1/videos"
```

Response:
```json
{
  "current_path": "/volume1/videos",
  "parent_path": "/volume1",
  "items": [
    {
      "name": "Movies",
      "path": "/volume1/videos/Movies",
      "is_directory": true,
      "size": null,
      "video_count": 125
    },
    {
      "name": "TV",
      "path": "/volume1/videos/TV",
      "is_directory": true,
      "size": null,
      "video_count": 523
    }
  ]
}
```

### Start a Scan

```bash
curl -X POST "http://localhost:8007/api/nas/scan" \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["/volume1/videos/Movies", "/volume1/videos/TV"],
    "scan_type": "full"
  }'
```

Response:
```json
{
  "scan_id": 1,
  "status": "running",
  "files_found": 0,
  "files_new": 0,
  "files_updated": 0,
  "errors_count": 0,
  "scan_started_at": "2025-11-10T03:00:00",
  "scan_completed_at": null
}
```

### Check Scan Status

```bash
curl "http://localhost:8007/api/nas/scan/1"
```

Response:
```json
{
  "scan_id": 1,
  "status": "completed",
  "files_found": 648,
  "files_new": 648,
  "files_updated": 0,
  "errors_count": 0,
  "scan_started_at": "2025-11-10T03:00:00",
  "scan_completed_at": "2025-11-10T03:15:30"
}
```

## Technical Details

### Path Handling

The browser handles path conversion between:
- **Relative paths:** `/volume1/videos` (NAS-relative)
- **Absolute paths:** `/mnt/nas-media/volume1/videos` (system-absolute)

The backend automatically converts between these as needed.

### Security Considerations

- Hidden files and system folders are excluded (`.`, `@eaDir`, `#recycle`, `lost+found`)
- Permission errors are handled gracefully
- Path validation prevents directory traversal attacks
- Scan operations run with appropriate file system permissions

### Performance Optimizations

- Video counts are calculated non-recursively for quick loading
- Scan operations run asynchronously to avoid blocking
- Progress polling happens every 2 seconds
- File listings are scrollable for large directories

## File Structure

```
mediavault/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   └── nas.py                    # NEW - API endpoints
│   │   ├── main.py                       # UPDATED - registered nas router
│   │   └── services/
│   │       └── scanner_service.py        # EXISTING - scan logic
│   └── .env                              # UPDATED - scan paths
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   └── NASFolderBrowser.tsx      # NEW - Browser component
    │   └── pages/
    │       └── Settings.tsx              # UPDATED - Integrated browser
    └── package.json
```

## Configuration

The default scan paths are still configured in `backend/.env`:

```env
NAS_SCAN_PATHS=/volume1/videos,/volume1/docker/data/torrents/torrents,/volume1/docker/transmission/downloads/complete/tv,/volume1/docker/transmission/downloads/complete/movies
```

The folder browser allows ad-hoc scanning of any accessible folder without modifying the configuration.

## Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can browse to `/volume1` folder
- [ ] Can navigate into subfolders
- [ ] Video counts are displayed correctly
- [ ] Can select multiple folders
- [ ] Scan button is enabled when folders selected
- [ ] Scan starts successfully
- [ ] Progress updates in real-time
- [ ] Scan completes with success message
- [ ] Files appear in database after scan
- [ ] Can view scan history

## Next Steps

1. **Test the Feature**
   - Start backend and frontend
   - Navigate to Settings page
   - Test folder browsing
   - Run a test scan on a small folder
   - Verify files appear in Library

2. **Run Full Scan**
   - Use browser to select all media folders
   - Start comprehensive scan
   - Monitor progress
   - Verify all media discovered

3. **Future Enhancements**
   - Add file preview/thumbnails
   - Show file metadata on hover
   - Add search/filter for folders
   - Save favorite scan paths
   - Schedule automated scans
   - Bulk operations (delete, move, etc.)

## Known Limitations

- Video counts are non-recursive (only immediate files in folder)
- Large folders may take time to list
- Scan progress doesn't show current file being processed
- No pause/resume functionality for scans
- No partial scan support (must complete or fail)

## Troubleshooting

### Can't See Any Folders

Check that:
1. NAS mounts are healthy: `mountpoint /mnt/nas-media/volume1/docker`
2. Backend has permissions: `ls -la /mnt/nas-media/volume1/`
3. Backend is running: `curl http://localhost:8007/api/nas/browse?path=/volume1`

### Scan Fails to Start

Check:
1. Selected paths exist
2. Backend logs for errors: `docker logs mediavault-backend`
3. Database connection is active
4. FFmpeg is installed: `ffmpeg -version`

### Progress Not Updating

Check:
1. Browser console for errors
2. Backend is responding: `curl http://localhost:8007/api/nas/scan/<scan_id>`
3. Scan isn't stuck (check logs)

---

**Status:** ✅ Implementation complete, ready for testing
**Last Updated:** 2025-11-10
