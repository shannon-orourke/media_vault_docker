# MediaVault - Quick Start Guide

## ✅ Current Status

**Backend:** Running on http://localhost:8007
**Frontend:** Running on http://localhost:3007

Both services are fully functional and ready to use!

---

## 🚀 Access the Application

Open your browser and navigate to:

```
http://localhost:3007
```

You'll see the MediaVault dashboard with:
- **Dashboard** - Library stats and recent scans
- **Library** - Browse all media files
- **Duplicates** - Review and manage duplicates
- **Scanner** - Start scans and run deduplication
- **Settings** - View configuration

---

## 📝 Quick Workflow

### 1. Start a Scan

1. Go to the **Scanner** page
2. Enter NAS paths (one per line):
   ```
   /volume1/docker
   /volume1/videos
   ```
3. Select scan type:
   - **Full Scan**: Scans all files (first run)
   - **Incremental**: Skips existing files (faster)
4. Click **Start Scan**

The scanner will:
- Recursively find all video files (.mkv, .mp4, .avi, etc.)
- Extract metadata using FFprobe
- Calculate MD5 hashes
- Score quality (0-200 scale)
- Detect languages (audio/subtitle tracks)
- Look up TMDb metadata (if available)

### 2. Detect Duplicates

1. After scanning, stay on the **Scanner** page
2. Click **Run Duplicate Detection**

The system will:
- Find exact duplicates (MD5 hash matching)
- Find fuzzy duplicates (guessit + rapidfuzz)
- Group duplicates with confidence scores
- Calculate quality deltas between files

### 3. Review Duplicates

1. Go to the **Duplicates** page
2. Expand a duplicate group to see all files
3. Review:
   - Quality scores
   - Resolution and codec
   - Audio languages
   - File sizes
   - Quality differences
4. Click **Keep** on the file you want to keep
5. Click **Dismiss Group** when done reviewing

### 4. Browse Library

1. Go to the **Library** page
2. Use the search bar to filter files
3. Sort by:
   - Date added
   - Name
   - Quality score
   - File size
4. Click the info icon to see detailed metadata
5. Click the trash icon to delete a file

---

## 🔧 Backend API

The backend API is available at http://localhost:8007

### API Documentation
- Swagger UI: http://localhost:8007/docs
- ReDoc: http://localhost:8007/redoc

### Key Endpoints

**Health Check:**
```bash
curl http://localhost:8007/api/health
```

**Start Scan:**
```bash
curl -X POST http://localhost:8007/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{"paths": ["/volume1/docker"], "scan_type": "full"}'
```

**List Media:**
```bash
curl http://localhost:8007/api/media?limit=10
```

**Run Deduplication:**
```bash
curl -X POST http://localhost:8007/api/scan/deduplicate
```

**List Duplicates:**
```bash
curl http://localhost:8007/api/duplicates
```

---

## 🎯 Testing with Real NAS Files

### Mount NAS (Optional)

If you want to test with the actual Synology NAS:

```bash
# Create mount point
sudo mkdir -p /mnt/nas-media

# Mount NAS share
sudo mount -t cifs //10.27.10.11/docker /mnt/nas-media \
  -o username=ProxmoxBackupsSMB,password=Setup123

# Verify mount
ls /mnt/nas-media

# Scan mounted path
curl -X POST http://localhost:8007/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{"paths": ["/mnt/nas-media"], "scan_type": "full"}'
```

### Test with Sample Files

If you don't have the NAS, you can test with any local media files:

```bash
# Create test directory
mkdir -p /tmp/test_videos

# Copy some video files
cp /path/to/your/videos/*.mkv /tmp/test_videos/

# Scan test directory
curl -X POST http://localhost:8007/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{"paths": ["/tmp/test_videos"], "scan_type": "full"}'
```

---

## 🐛 Troubleshooting

### Backend Not Running?
```bash
cd /home/mercury/projects/mediavault/backend
uvicorn app.main:app --host 0.0.0.0 --port 8007
```

### Frontend Not Running?
```bash
cd /home/mercury/projects/mediavault/frontend
npm run dev
```

### Check Backend Logs
```bash
# If running in foreground, check terminal output
# If running in background, check process logs
ps aux | grep uvicorn
```

### Check Frontend Logs
```bash
# Check terminal where npm run dev is running
# Or check browser console (F12)
```

### Database Issues?
```bash
# Connect to database
docker exec -it pm-ideas-postgres psql -U pm_ideas_user -d mediavault

# Check tables
\dt

# Check media files
SELECT COUNT(*) FROM media_files;

# Check scans
SELECT * FROM scan_history ORDER BY scan_started_at DESC LIMIT 5;

# Exit
\q
```

### NAS Mount Issues?
```bash
# Check connectivity
ping 10.27.10.11

# Test SMB access
smbclient //10.27.10.11/docker -U ProxmoxBackupsSMB

# Check mount
mount | grep nas
```

---

## 📚 Understanding Quality Scores

Quality scores range from **0 to 200** points:

| Score Range | Quality Level |
|-------------|---------------|
| 150-200 | Excellent (4K HDR) |
| 100-149 | Good (1080p HD) |
| 50-99 | Fair (720p) |
| 0-49 | Poor (SD/480p) |

**Components:**
- Resolution: 4K=100, 1080p=75, 720p=50, 480p=25
- Codec: H.265=20, H.264=15, VP9=18, AV1=22
- Bitrate: Up to 30 points (normalized)
- Audio: 5.1=15, 2.0=10
- Multi-audio tracks: +3 per track (max 10)
- Subtitles: +2 per track (max 10)
- HDR: +15 for HDR10/Dolby Vision

---

## 🔐 Deletion Safety

MediaVault is designed to be **extremely safe**:

1. **No Auto-Delete**: Files are NEVER deleted automatically
2. **Manual Review**: Every deletion requires your explicit approval
3. **Language Protection**: Never suggests deleting the only English version
4. **Staging Area**: Files are moved to `/volume1/video/duplicates_before_purge/` before final deletion
5. **Detailed Reasoning**: Every deletion decision shows full reasoning

---

## 🎉 Next Steps

1. **Run Your First Scan**
   - Use the Scanner page to scan `/volume1/docker` or `/volume1/videos`
   - Wait for completion (can take minutes to hours depending on file count)

2. **Detect Duplicates**
   - After scanning, run duplicate detection
   - Review results in the Duplicates page

3. **Review Quality Scores**
   - Browse the Library page
   - Check quality scores for your files
   - Look for files with low scores

4. **Deploy to Production**
   - See `DEPLOYMENT_SUMMARY.md` for production deployment steps
   - Install nginx config
   - Get SSL certificate
   - Set up systemd services

---

## 📞 Need Help?

- Check logs in terminal windows
- Inspect browser console (F12)
- Check database with psql
- Review `DEPLOYMENT_SUMMARY.md` for detailed technical info
- Review `PLANNING.md` for architecture details

---

**Happy organizing!** 🎬
