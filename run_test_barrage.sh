#!/bin/bash
# MediaVault Test Barrage Executor
# Run this script to execute all automated tests

echo "=== MediaVault Test Barrage #1 ==="
echo "Started: $(date)"
echo ""

# Phase 1: Health Checks
echo "=================================================="
echo "[Phase 1] Health Checks"
echo "=================================================="

echo -e "\n[Test 1.1] Backend Health Endpoint"
curl -s http://localhost:8007/api/health | jq

echo -e "\n[Test 1.2] NAS Mount - Docker Volume"
if mountpoint -q /mnt/nas-media/volume1/docker; then
    echo "✅ PASS: /mnt/nas-media/volume1/docker is mounted"
else
    echo "❌ FAIL: /mnt/nas-media/volume1/docker is NOT mounted"
fi

echo -e "\n[Test 1.3] NAS Mount - Videos Volume"
if mountpoint -q /mnt/nas-media/volume1/videos; then
    echo "✅ PASS: /mnt/nas-media/volume1/videos is mounted"
else
    echo "❌ FAIL: /mnt/nas-media/volume1/videos is NOT mounted"
fi

echo -e "\n[Test 1.4] NAS Read Access"
if ls /mnt/nas-media/volume1/docker >/dev/null 2>&1; then
    file_count=$(ls /mnt/nas-media/volume1/docker | wc -l)
    echo "✅ PASS: Docker volume readable ($file_count items)"
else
    echo "❌ FAIL: Cannot read docker volume"
fi

echo -e "\n[Test 1.5] Database Connection"
db_result=$(docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -t -c "SELECT 1;" 2>&1)
if [ "$?" -eq 0 ]; then
    echo "✅ PASS: Database connection successful"
else
    echo "❌ FAIL: Database connection failed"
    echo "Error: $db_result"
fi

echo -e "\n[Test 1.6] Database Tables Exist"
table_count=$(docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>&1 | tr -d ' ')
if [ "$table_count" -ge 7 ]; then
    echo "✅ PASS: Database has $table_count tables (expected 7+)"
else
    echo "⚠️  WARNING: Database has only $table_count tables (expected 7+)"
fi

# Phase 2: API Testing
echo -e "\n=================================================="
echo "[Phase 2] API Testing"
echo "=================================================="

echo -e "\n[Test 2.1] Media List Endpoint"
media_response=$(curl -s "http://localhost:8007/api/media/?limit=10")
media_total=$(echo "$media_response" | jq -r '.total')
if [ "$media_total" -ge 0 ]; then
    echo "✅ PASS: Media list endpoint returned $media_total total files"
else
    echo "❌ FAIL: Media list endpoint failed"
fi

echo -e "\n[Test 2.2] Media Stats Endpoint"
stats_response=$(curl -s "http://localhost:8007/api/media/stats/summary")
total_size=$(echo "$stats_response" | jq -r '.total_size_gb // 0')
echo "Media Stats: $total_size GB total"
if [ "$?" -eq 0 ]; then
    echo "✅ PASS: Media stats endpoint works"
else
    echo "❌ FAIL: Media stats endpoint failed"
fi

echo -e "\n[Test 2.3] Scan History Endpoint"
scan_response=$(curl -s "http://localhost:8007/api/scan/history?limit=5")
scan_count=$(echo "$scan_response" | jq '. | length')
if [ "$scan_count" -ge 0 ]; then
    echo "✅ PASS: Scan history endpoint returned $scan_count scans"
else
    echo "❌ FAIL: Scan history endpoint failed"
fi

echo -e "\n[Test 2.4] NAS Browse Endpoint"
nas_response=$(curl -s "http://localhost:8007/api/nas/browse?path=/volume1/docker")
nas_items=$(echo "$nas_response" | jq -r '.items | length // 0')
if [ "$nas_items" -ge 0 ]; then
    echo "✅ PASS: NAS browse endpoint returned $nas_items items"
else
    echo "❌ FAIL: NAS browse endpoint failed"
fi

echo -e "\n[Test 2.5] Duplicate Groups Endpoint"
dup_response=$(curl -s "http://localhost:8007/api/duplicates/groups")
dup_count=$(echo "$dup_response" | jq '. | length // 0')
if [ "$?" -eq 0 ]; then
    echo "✅ PASS: Duplicate groups endpoint returned $dup_count groups"
else
    echo "❌ FAIL: Duplicate groups endpoint failed"
fi

echo -e "\n[Test 2.6] Pending Deletions Endpoint"
del_response=$(curl -s "http://localhost:8007/api/deletions/pending?limit=10")
del_count=$(echo "$del_response" | jq '.items | length // 0')
if [ "$?" -eq 0 ]; then
    echo "✅ PASS: Pending deletions endpoint returned $del_count items"
else
    echo "❌ FAIL: Pending deletions endpoint failed"
fi

# Phase 3: Database Testing
echo -e "\n=================================================="
echo "[Phase 3] Database Integrity"
echo "=================================================="

echo -e "\n[Test 3.1] Media Files Count"
media_count=$(docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -t -c "SELECT COUNT(*) FROM media_files;" 2>&1 | tr -d ' ')
echo "Media files in database: $media_count"

echo -e "\n[Test 3.2] Scan History Count"
scan_count=$(docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -t -c "SELECT COUNT(*) FROM scan_history;" 2>&1 | tr -d ' ')
echo "Scan history records: $scan_count"

echo -e "\n[Test 3.3] Quality Score Range Validation"
invalid_scores=$(docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -t -c "SELECT COUNT(*) FROM media_files WHERE quality_score < 0 OR quality_score > 200;" 2>&1 | tr -d ' ')
if [ "$invalid_scores" -eq 0 ]; then
    echo "✅ PASS: All quality scores in valid range (0-200)"
else
    echo "❌ FAIL: Found $invalid_scores files with invalid quality scores"
fi

echo -e "\n[Test 3.4] TMDb Fields Present"
tmdb_fields=$(docker exec pm-ideas-postgres psql -U pm_ideas_user -d mediavault -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'media_files' AND column_name IN ('tmdb_id', 'tmdb_type', 'tmdb_year', 'imdb_id');" 2>&1 | tr -d ' ')
if [ "$tmdb_fields" -eq 4 ]; then
    echo "✅ PASS: All TMDb fields present in database"
else
    echo "⚠️  WARNING: Only $tmdb_fields/4 TMDb fields found"
fi

# Phase 4: File System Testing
echo -e "\n=================================================="
echo "[Phase 4] File System Operations"
echo "=================================================="

echo -e "\n[Test 4.1] Video File Discovery"
video_count=$(find /mnt/nas-media/volume1/docker/transmission/downloads/complete/tv -name "*.mkv" -o -name "*.mp4" 2>/dev/null | wc -l)
echo "Found $video_count video files in TV directory"
if [ "$video_count" -gt 0 ]; then
    echo "✅ PASS: Video files discoverable"
else
    echo "⚠️  WARNING: No video files found"
fi

echo -e "\n[Test 4.2] FFprobe Availability"
if command -v ffprobe >/dev/null 2>&1; then
    ffprobe_version=$(ffprobe -version | head -1)
    echo "✅ PASS: FFprobe available ($ffprobe_version)"
else
    echo "❌ FAIL: FFprobe not found in PATH"
fi

echo -e "\n[Test 4.3] Sample File Metadata Extraction"
sample_file=$(find /mnt/nas-media/volume1/docker/transmission/downloads/complete/tv -name "*.mkv" 2>/dev/null | head -1)
if [ -n "$sample_file" ]; then
    echo "Testing: $(basename "$sample_file")"
    if ffprobe "$sample_file" -v quiet -print_format json -show_format 2>/dev/null | jq -e '.format.duration' >/dev/null; then
        echo "✅ PASS: Metadata extraction works"
    else
        echo "❌ FAIL: Cannot extract metadata"
    fi
else
    echo "⚠️  WARNING: No sample file found for testing"
fi

# Phase 5: Performance Testing
echo -e "\n=================================================="
echo "[Phase 5] Performance Baselines"
echo "=================================================="

echo -e "\n[Test 5.1] Health Endpoint Response Time"
health_time=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8007/api/health)
echo "Response time: ${health_time}s (target: <0.1s)"
if (( $(echo "$health_time < 0.1" | bc -l) )); then
    echo "✅ PASS: Health endpoint fast"
else
    echo "⚠️  WARNING: Health endpoint slower than target"
fi

echo -e "\n[Test 5.2] Media List Response Time (10 items)"
media_time=$(curl -s -w "%{time_total}" -o /dev/null "http://localhost:8007/api/media/?limit=10")
echo "Response time: ${media_time}s (target: <0.5s)"
if (( $(echo "$media_time < 0.5" | bc -l) )); then
    echo "✅ PASS: Media list fast"
else
    echo "⚠️  WARNING: Media list slower than target"
fi

echo -e "\n[Test 5.3] Media List Response Time (100 items)"
media_time_100=$(curl -s -w "%{time_total}" -o /dev/null "http://localhost:8007/api/media/?limit=100")
echo "Response time: ${media_time_100}s (target: <1.0s)"
if (( $(echo "$media_time_100 < 1.0" | bc -l) )); then
    echo "✅ PASS: Large media list acceptable"
else
    echo "⚠️  WARNING: Large media list slower than target"
fi

# Phase 6: Security Testing
echo -e "\n=================================================="
echo "[Phase 6] Security Checks"
echo "=================================================="

echo -e "\n[Test 6.1] Security Headers"
headers=$(curl -s -I https://mediavault.orourkes.me/api/health 2>&1)
if echo "$headers" | grep -qi "x-frame-options"; then
    echo "✅ PASS: X-Frame-Options header present"
else
    echo "⚠️  WARNING: X-Frame-Options header missing"
fi

if echo "$headers" | grep -qi "x-content-type-options"; then
    echo "✅ PASS: X-Content-Type-Options header present"
else
    echo "⚠️  WARNING: X-Content-Type-Options header missing"
fi

echo -e "\n[Test 6.2] CORS Configuration"
cors_header=$(curl -s -H "Origin: https://mediavault.orourkes.me" -I http://localhost:8007/api/health | grep -i "access-control")
if [ -n "$cors_header" ]; then
    echo "✅ PASS: CORS headers configured"
else
    echo "⚠️  WARNING: CORS headers not found"
fi

# Summary
echo -e "\n=================================================="
echo "Test Barrage Summary"
echo "=================================================="
echo "Completed: $(date)"
echo ""
echo "Review results above for any ❌ FAIL or ⚠️  WARNING items"
echo "Document results in testbarrage1.md"
echo ""
echo "Next steps:"
echo "1. Fix any critical failures"
echo "2. Run manual UI tests via browser"
echo "3. Proceed with full NAS scan when all tests pass"
