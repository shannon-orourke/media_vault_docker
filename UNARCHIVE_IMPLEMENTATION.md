# Unarchive Feature Implementation Summary

## ✅ Completed

### Backend
1. **Database Schema** (`002_archive_management.sql`)
   - `archive_files` table - Tracks RAR/ZIP archives
   - `archive_contents` table - Tracks extracted files
   - Retention tracking with `mark_for_deletion_at` (6 months)
   - ✅ Migration applied successfully

2. **Models** (`backend/app/models/archive.py`)
   - `ArchiveFile` model
   - `ArchiveContent` model
   - ✅ Registered in `models/__init__.py`

3. **Service** (`backend/app/services/archive_service.py`)
   - `scan_for_archives()` - Recursive scan for RAR/ZIP/7z
   - `extract_archive()` - Extract using unrar/unzip/7z
   - `mark_for_deletion()` - Mark for immediate deletion
   - `delete_old_archives()` - Cleanup after 6 months
   - `move_archive_to_seed_location()` - Move to seeding folder
   - ✅ Uses guessit for filename parsing
   - ✅ Automatic destination path: `/volume1/videos/movies` or `/volume1/videos/tv`

4. **API Routes** (`backend/app/routes/archives.py`)
   - `POST /api/archives/scan` - Scan for archives
   - `GET /api/archives` - List archives
   - `GET /api/archives/{id}` - Get archive details
   - `POST /api/archives/{id}/extract` - Extract archive
   - `POST /api/archives/{id}/mark-for-deletion` - Mark for deletion
   - `DELETE /api/archives/{id}` - Delete archive
   - `POST /api/archives/cleanup` - Delete old archives
   - ✅ Registered in `main.py`

5. **Scanner Improvements** (`backend/app/services/nas_service.py`)
   - ✅ Filters TypeScript files (.d.ts, .test.ts, .spec.ts)
   - ✅ Skips node_modules, .git, .venv, dist, build
   - ✅ File size heuristic (>10MB = likely video)
   - ✅ Directory heuristic (checks for /videos/, /src/, etc.)

### Frontend
1. **Unarchive Page** (`frontend/src/pages/Unarchive.tsx`)
   - ✅ Scan for archives with custom paths
   - ✅ List archives with status filtering
   - ✅ Extract button with confirmation modal
   - ✅ Mark for deletion (removes 6-month grace period)
   - ✅ Delete archive immediately
   - ✅ Shows destination path, file size, media type
   - ✅ Displays deletion date (6 months from discovery)

## 🔄 Remaining Tasks

### 1. Add Archive API Functions to Frontend

**File:** `frontend/src/services/api.ts`

Add these interfaces and API functions:

```typescript
// Add to interfaces section
export interface ArchiveFile {
  id: number;
  filename: string;
  filepath: string;
  file_size: number;
  archive_type: string;
  extraction_status: string;
  parsed_title: string | null;
  parsed_year: number | null;
  media_type: string | null;
  destination_path: string | null;
  extracted_to_path: string | null;
  mark_for_deletion_at: string | null;
  discovered_at: string;
}

export interface ArchiveListResponse {
  total: number;
  skip: number;
  limit: number;
  archives: ArchiveFile[];
}

export interface ScanArchivesRequest {
  paths?: string[];
}

export interface ExtractArchiveRequest {
  destination?: string;
}

// Add to mediaApi object
export const mediaApi = {
  // ... existing methods ...

  // Archive endpoints
  scanArchives: (data: ScanArchivesRequest) =>
    api.post('/archives/scan', data),

  listArchives: (params?: { status?: string; limit?: number; skip?: number }) =>
    api.get<ArchiveListResponse>('/archives', { params }),

  getArchive: (id: number) =>
    api.get<ArchiveFile>(`/archives/${id}`),

  extractArchive: (id: number, destination?: string) =>
    api.post(`/archives/${id}/extract`, { destination }),

  markArchiveForDeletion: (id: number) =>
    api.post(`/archives/${id}/mark-for-deletion`),

  deleteArchive: (id: number) =>
    api.delete(`/archives/${id}`),

  cleanupOldArchives: () =>
    api.post('/archives/cleanup'),
};
```

### 2. Add Unarchive Navigation Link

**File:** `frontend/src/App.tsx`

Add the Unarchive route and navigation:

```typescript
// Import Unarchive page
import Unarchive from './pages/Unarchive';

// Add route in BrowserRouter
<Route path="/unarchive" element={<Unarchive />} />

// Add navigation link in AppShell.Navbar
<NavLink
  label="Unarchive"
  leftSection={<IconPackage size={16} />}
  component={Link}
  to="/unarchive"
/>
```

### 3. Add Editable Scan Paths in Settings

**File:** `frontend/src/pages/Settings.tsx`

Add this section:

```typescript
// Add state
const [scanPaths, setScanPaths] = useState('/volume1/docker, /volume1/videos');

// Add UI in Settings page
<Card shadow="sm" padding="lg" radius="md" withBorder>
  <Title order={4}>Scan Paths</Title>
  <Text size="sm" c="dimmed" mb="md">
    Configure which NAS paths to scan for media files and archives
  </Text>

  <Textarea
    label="Media Scan Paths (comma-separated)"
    description="Paths to scan for video files"
    placeholder="/volume1/videos, /volume1/movies"
    value={scanPaths}
    onChange={(e) => setScanPaths(e.currentTarget.value)}
    minRows={3}
    mb="md"
  />

  <Button onClick={handleSaveScanPaths}>
    Save Scan Paths
  </Button>
</Card>
```

### 4. Install unrar on System

**Required for extraction:**

```bash
# Install unrar
sudo apt-get update
sudo apt-get install -y unrar unzip p7zip-full

# Verify installation
unrar --version
unzip --version
7z --version
```

### 5. Rebuild and Deploy

```bash
# Stop dev frontend if running
pkill -f "npm run dev"

# Rebuild production frontend
cd /home/mercury/projects/mediavault/frontend
npm run build

# Restart backend service
sudo systemctl restart mediavault-backend

# Verify
curl https://mediavault.orourkes.me/api/health
curl https://mediavault.orourkes.me/api/archives
```

## 🎯 How to Use

### 1. Scan for Archives
1. Go to **Unarchive** page
2. Enter scan paths: `/volume1/downloads, /volume1/torrents`
3. Click **Scan for Archives**
4. System will find all RAR/ZIP/7z files

### 2. Extract Archive
1. Find archive in list (status: "pending")
2. Click to expand details
3. Click **Extract** button
4. Archive extracts to:
   - Movies: `/volume1/videos/movies/{Title} ({Year})`
   - TV: `/volume1/videos/tv/{Title}`
5. Extracted files automatically indexed in media library

### 3. Seeding Management
- **Automatic deletion date:** 6 months from discovery
- **Mark for deletion:** Removes grace period, deletes immediately
- **Keep for seeding:** Archives stay until deletion date
- **Cleanup:** Runs `/api/archives/cleanup` to delete old archives

## 🔧 Configuration

**Destination Paths** (`backend/app/services/archive_service.py`):
```python
self.movie_dest = "/volume1/videos/movies"
self.tv_dest = "/volume1/videos/tv"
```

**Retention Period:**
```python
archive.set_deletion_date(months=6)  # 6 months for seeding quota
```

## 📊 Database Queries

```sql
-- List pending archives
SELECT * FROM archive_files WHERE extraction_status = 'pending';

-- List archives ready for deletion
SELECT * FROM archive_files
WHERE mark_for_deletion_at <= NOW() AND deleted_at IS NULL;

-- Count archives by status
SELECT extraction_status, COUNT(*)
FROM archive_files
GROUP BY extraction_status;
```

## 🧪 Testing

```bash
# 1. Create test RAR file
echo "test content" > test.txt
rar a test.movie.2023.rar test.txt

# 2. Scan for it
curl -X POST https://mediavault.orourkes.me/api/archives/scan \
  -H "Content-Type: application/json" \
  -d '{"paths": ["/path/to/test"]}'

# 3. List archives
curl https://mediavault.orourkes.me/api/archives

# 4. Extract
curl -X POST https://mediavault.orourkes.me/api/archives/1/extract

# 5. Cleanup old archives
curl -X POST https://mediavault.orourkes.me/api/archives/cleanup
```

## 🎉 Features Summary

- ✅ Recursive RAR/ZIP/7z scanning
- ✅ Automatic title/year parsing with guessit
- ✅ Automatic destination path determination
- ✅ Extract to movies/tv folders
- ✅ 6-month retention for seeding quota
- ✅ Mark for immediate deletion
- ✅ Automatic cleanup of old archives
- ✅ Link extracted files to media library
- ✅ TypeScript file filtering (no more false positives!)

## 🚀 Next Steps

1. Add archive API functions to `api.ts`
2. Add Unarchive navigation link
3. Install `unrar` tools
4. Rebuild frontend
5. Restart backend
6. Test with real RAR files!
