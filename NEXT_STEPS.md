# Next Steps - Backend Restart and Testing

## What We Fixed
Added missing imports to `backend/app/routes/stream.py`:
- `import subprocess` (needed for FFmpeg pipe streaming)
- `from app.config import get_settings` (needed for settings.ffmpeg_path)

## Step 1: Restart Backend
Run this script (requires sudo password):
```bash
./restart_and_test.sh
```

This will:
1. Restart mediavault-backend service
2. Show backend status
3. Test the progressive endpoint

## Step 2: Check for Errors (if needed)
If restart_and_test.sh shows "Internal Server Error", run:
```bash
./check_backend_error.sh
```

This will show the actual Python traceback from the backend logs.

## Step 3: Monitor Live Playback
Open TWO terminal windows:

**Terminal 1 - Backend Logs:**
```bash
./monitor_backend.sh
```

**Terminal 2 - GPU Monitor:**
```bash
watch -n 1 nvidia-smi
```

Then go to https://mediavault.orourkes.me/library and click play on a video.

## What You Should See

### If Working:
- **Terminal 1 (Backend):** FFmpeg command executing, streaming requests
- **Terminal 2 (GPU):** GPU encoder usage spike (10-30%)
- **Browser:** Video starts playing within 2-3 seconds

### If Not Working:
- Backend logs will show the actual error
- Share the error output and we'll debug further

## Quick Test Commands

Test progressive endpoint directly:
```bash
# Should return binary MP4 data (not "Internal Server Error")
timeout 5 curl -k "https://mediavault.orourkes.me/api/stream/335/progressive?use_gpu=true" | head -c 100 | xxd
```

Test smart endpoint:
```bash
# Should return 302 redirect or binary data
curl -I -k "https://mediavault.orourkes.me/api/stream/335/smart"
```

## Current Status
✅ Missing imports added to stream.py
⏳ Backend restart required
⏳ Testing progressive streaming with GPU
⏳ Verify video playback in browser
