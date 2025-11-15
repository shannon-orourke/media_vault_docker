# Video Streaming Fix: HEAD Request Handling

## Problem Identified by Automated Tests

The automated tests revealed the **root cause** of why videos don't play:

```
FAILED: test_response_headers
AssertionError: Wrong Content-Type: application/json
```

When browsers try to play a video, they first send a **HEAD request** to check the Content-Type. Our streaming endpoints were returning:
- ❌ `Content-Type: application/json` (FastAPI default)
- ✓ Expected: `Content-Type: video/mp4`

**Result**: Browser sees JSON instead of video, refuses to play.

## What Was Fixed

Added HEAD request handlers for both streaming endpoints:

### Before
```python
@router.get("/{file_id}/progressive")  # Only GET handler
@router.get("/{file_id}/smart")        # Only GET handler
```

### After
```python
@router.head("/{file_id}/progressive")  # HEAD handler added
@router.get("/{file_id}/progressive")

@router.head("/{file_id}/smart")        # HEAD handler added
@router.get("/{file_id}/smart")
```

Both HEAD handlers now return:
```python
Response(
    status_code=200,
    media_type="video/mp4",  # Correct Content-Type!
    headers={
        "Accept-Ranges": "none",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*"
    }
)
```

## How to Test the Fix

1. **Restart the backend** (required to apply changes):
   ```bash
   sudo systemctl restart mediavault-backend
   ```

2. **Test HEAD requests manually**:
   ```bash
   curl -I -k "https://mediavault.orourkes.me/api/stream/335/smart"
   # Should now show: Content-Type: video/mp4
   ```

3. **Run automated tests**:
   ```bash
   ./test_streaming_automated.sh
   ```

   Expected results:
   - ✅ `test_response_headers` - Should now pass
   - ✅ `test_video_actually_plays` - Should now pass with readyState > 0
   - Screenshot: `/tmp/video_playing.png` (proof it works!)

## Expected Outcome

After restart, when you play a video:
1. Browser sends HEAD request → Gets `Content-Type: video/mp4` ✓
2. Browser sends GET request → Receives MP4 stream ✓
3. Video element starts buffering (readyState goes from 0 → 2+ ) ✓
4. Video plays! ✓

## Why This Happened

FastAPI doesn't automatically create HEAD handlers when you define GET routes. Browsers need HEAD requests to work properly with video elements, so we had to add them explicitly.

## Verification Commands

After restarting backend, run these in sequence:

```bash
# 1. Check HEAD request returns video/mp4
curl -I -k https://mediavault.orourkes.me/api/stream/335/smart 2>&1 | grep Content-Type

# 2. Run just the header test
cd backend
pytest tests/test_streaming_e2e.py::TestStreamAPIValidation::test_response_headers -v

# 3. Run the critical browser test
pytest tests/test_streaming_e2e.py::TestBrowserPlayback::test_video_actually_plays -v -s

# 4. If that passes, run full test suite
cd ..
./test_streaming_automated.sh
```

## Files Modified

- `backend/app/routes/stream.py`:
  - Added `progressive_stream_head()` at line 544
  - Added `smart_stream_head()` at line 684

## Success Criteria

✅ All automated tests pass
✅ Browser test shows `readyState >= 2`
✅ Screenshot shows video playing: `/tmp/video_playing.png`
✅ No more spinning - video actually plays!
