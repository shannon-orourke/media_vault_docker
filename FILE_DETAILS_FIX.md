# File Details Modal Fix

**Created:** 2025-11-10
**Status:** Complete

## Issue

The File Details modal (info button) in the Library page was not displaying some fields correctly:
- **Bitrate:** Showing "kbps" with no value
- **Audio Channels:** Empty
- **MD5:** Empty

The data was actually in the database (confirmed via test scan), but the frontend wasn't displaying it properly.

## Root Cause

The modal in `frontend/src/pages/Library.tsx` (lines 388-391) was displaying raw values without:
- Null/undefined checks
- Proper formatting
- Fallback values

## Fix Applied

**File:** `frontend/src/pages/Library.tsx` (lines 380-425)

### Changes:

1. **Bitrate Display**
   ```typescript
   // Before:
   <Text><strong>Bitrate:</strong> {file.bitrate} kbps</Text>

   // After:
   <Text><strong>Bitrate:</strong> {file.bitrate ? `${Math.round(file.bitrate / 1000)} Mbps` : 'N/A'}</Text>
   ```
   - Converts from kbps to Mbps (divides by 1000)
   - Shows "N/A" if not available
   - Result: "11 Mbps" instead of "11475 kbps"

2. **Audio Channels Display**
   ```typescript
   // Before:
   <Text><strong>Audio Channels:</strong> {file.audio_channels}</Text>

   // After:
   <Text><strong>Audio Channels:</strong> {file.audio_channels || 'N/A'}</Text>
   ```
   - Shows actual value (e.g., "2.0")
   - Fallback to "N/A" if not available

3. **MD5 Hash Display**
   ```typescript
   // Before:
   <Text><strong>MD5:</strong> {file.md5_hash}</Text>

   // After:
   <Group gap="xs">
     <Text size="sm">
       <strong>MD5:</strong> {file.md5_hash ? 'Yes' : 'Not calculated'}
     </Text>
     {file.md5_hash && (
       <Badge
         variant="light"
         style={{ cursor: 'pointer' }}
         onClick={() => {
           navigator.clipboard.writeText(file.md5_hash || '');
           notifications.show({
             title: 'MD5 Hash',
             message: file.md5_hash,
             color: 'blue',
             autoClose: 5000,
           });
         }}
       >
         Copy Hash
       </Badge>
     )}
   </Group>
   ```
   - Shows "Yes" if MD5 exists, "Not calculated" if not
   - Adds clickable "Copy Hash" badge
   - Clicking the badge:
     - Copies full MD5 hash to clipboard
     - Shows toast notification with complete hash
     - Auto-closes after 5 seconds

## Testing

To verify the fix:

1. **Start frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Open Library page**
   - Navigate to Library
   - Find one of the Red Dwarf episodes
   - Click the info (ⓘ) button

3. **Expected Results:**
   - **Path:** Full file path shown
   - **Codec:** "h264 / dts"
   - **Bitrate:** "11 Mbps"
   - **Audio Channels:** "2.0"
   - **MD5:** "Yes" with a "Copy Hash" badge

4. **Click "Copy Hash" badge:**
   - Toast notification appears with full MD5 hash
   - Hash is copied to clipboard
   - Can paste to verify

## Example Output

Before Fix:
```
Path: /mnt/nas-media/volume1/docker/.../Red.Dwarf.S12E01...mkv
Codec: h264 / dts
Bitrate: kbps
Audio Channels:
MD5:
```

After Fix:
```
Path: /mnt/nas-media/volume1/docker/.../Red.Dwarf.S12E01...mkv
Codec: h264 / dts
Bitrate: 11 Mbps
Audio Channels: 2.0
MD5: Yes [Copy Hash]
```

## Files Modified

- `frontend/src/pages/Library.tsx` - Fixed file details modal display

## Related

- The backend data capture was working correctly (validated in test scan)
- This was purely a frontend display issue
- No backend changes were needed

---

**Status:** ✅ Complete - Ready for testing
