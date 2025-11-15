# TMDb Search Link Feature

**Created:** 2025-11-10
**Status:** Complete

## Overview

Added a "Search on TMDb" button to the file details modal that opens The Movie Database search page with the parsed title and year.

## Implementation

### Frontend Changes

**File:** `frontend/src/pages/Library.tsx`

1. **Added IconExternalLink import:**
   ```typescript
   import { IconExternalLink } from '@tabler/icons-react';
   ```

2. **Added TMDb search button in file details modal:**
   ```typescript
   {file.parsed_title && (
     <Group gap="xs" mt="md">
       <Button
         variant="light"
         size="sm"
         leftSection={<IconExternalLink size={16} />}
         onClick={() => {
           const searchQuery = encodeURIComponent(
             file.parsed_title + (file.parsed_year ? ` ${file.parsed_year}` : '')
           );
           window.open(`https://www.themoviedb.org/search?query=${searchQuery}`, '_blank');
         }}
       >
         Search on TMDb
       </Button>
     </Group>
   )}
   ```

3. **Updated TypeScript interface** in `frontend/src/services/api.ts`:
   - Added `parsed_season: number | null`
   - Added `parsed_episode: number | null`

### Backend Changes (Already Completed)

**File:** `backend/app/routes/media.py`

Previously updated to include all metadata fields in the list endpoint response:
- `parsed_title`
- `parsed_year`
- `parsed_season`
- `parsed_episode`

## How It Works

1. **Button Appears:** Only shows when a file has a `parsed_title` (extracted by guessit during scan)
2. **Search Query:** Constructs a TMDb search URL with:
   - Title: e.g., "Red Dwarf"
   - Year (if available): e.g., "2017"
3. **Opens in New Tab:** Click opens TMDb search in a new browser tab

## Example Usage

### For TV Shows

**File:** `Red.Dwarf.S12E01.1080p.BluRay.x264-SHORTBREHD.mkv`

**Modal Shows:**
```
Path: /mnt/nas-media/volume1/docker/.../Red.Dwarf.S12E01...mkv
Codec: h264 / dts
Bitrate: 11 Mbps
Audio Channels: 2.0
MD5: Yes [Copy Hash]

[Search on TMDb] ← Button
```

**Click Action:**
Opens: `https://www.themoviedb.org/search?query=Red%20Dwarf`

### For Movies

**File:** `Inception.2010.1080p.BluRay.x264.mkv`

**Search URL:**
`https://www.themoviedb.org/search?query=Inception%202010`

## Benefits

1. **Quick Access:** One click to find detailed information on TMDb
2. **No API Calls:** Uses client-side search, no backend requests needed
3. **Works Immediately:** No need to populate TMDb IDs in database
4. **User-Friendly:** Opens in new tab, doesn't navigate away from library

## Future Enhancements

To make this even better in the future:

1. **Store TMDb IDs During Scan:**
   - Enhance scanner to query TMDb API during scan
   - Store `tmdb_id` in database
   - Link directly to specific movie/show page

2. **Add IMDB Links:**
   - TMDb API returns IMDB IDs
   - Add button for IMDB as well

3. **Show TMDb Metadata:**
   - Display poster images
   - Show ratings/popularity
   - Add plot summaries

4. **Smart Matching:**
   - For TV shows, link to specific season/episode page
   - Handle special cases (anime, documentaries)

## Testing

To test the feature:

1. **Navigate to Library:**
   ```
   https://mediavault.orourkes.me/library
   ```

2. **Click Info Button (ⓘ)** on any Red Dwarf file

3. **Verify Modal Shows:**
   - All metadata (codec, bitrate, audio channels, MD5)
   - "Search on TMDb" button at bottom

4. **Click Button:**
   - Should open TMDb search in new tab
   - Search for "Red Dwarf"
   - Should find the TV show

5. **Expected Result:**
   TMDb page: https://www.themoviedb.org/tv/199-red-dwarf

## Files Modified

- ✅ `frontend/src/pages/Library.tsx` - Added TMDb search button
- ✅ `frontend/src/services/api.ts` - Updated interface with parsed fields
- ✅ `backend/app/routes/media.py` - Already updated to return all fields

## API Response Example

```json
{
  "id": 342,
  "filename": "Red.Dwarf.S12E06.1080p.BluRay.x264-SHORTBREHD.mkv",
  "parsed_title": "Red Dwarf",
  "parsed_year": null,
  "parsed_season": 12,
  "parsed_episode": 6,
  "video_codec": "h264",
  "audio_codec": "dts",
  "bitrate": 11188,
  "audio_channels": 2.0,
  "md5_hash": "0e1516b0b66b89f75a4b2deca5db566c"
}
```

## Screenshots

The file details modal now shows:

```
┌─────────────────────────────────────────────┐
│ File Details                          [X]   │
├─────────────────────────────────────────────┤
│ Path: /mnt/nas-media/volume1/...           │
│ Codec: h264 / dts                           │
│ Bitrate: 11 Mbps                            │
│ Audio Channels: 2.0                         │
│ MD5: Yes [Copy Hash]                        │
│                                             │
│ ┌───────────────────────────────────┐      │
│ │  ⎋ Search on TMDb                 │      │
│ └───────────────────────────────────┘      │
└─────────────────────────────────────────────┘
```

---

**Status:** ✅ Complete and deployed
**Last Updated:** 2025-11-10
