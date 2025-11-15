#!/bin/bash
# Mount NAS volume1 share

set -e

NAS_HOST="10.27.10.11"
NAS_SHARE="volume1"
MOUNT_POINT="/mnt/nas-synology"
CREDS_FILE="/root/.nas-credentials"

echo "======================================"
echo "Mounting NAS Volume1"
echo "======================================"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "❌ Must run as root (use sudo)"
    exit 1
fi

# Step 1: Test mount volume1
echo "Step 1: Mounting //$NAS_HOST/$NAS_SHARE to $MOUNT_POINT"

# Unmount if already mounted
if mountpoint -q "$MOUNT_POINT"; then
    echo "Unmounting existing mount..."
    umount "$MOUNT_POINT"
fi

# Mount volume1
mount -t cifs "//$NAS_HOST/$NAS_SHARE" "$MOUNT_POINT" \
    -o credentials="$CREDS_FILE",uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0

if mountpoint -q "$MOUNT_POINT"; then
    echo "✓ Mounted successfully!"
    echo ""
    echo "Mount info:"
    df -h "$MOUNT_POINT"
    echo ""
    echo "Top-level contents:"
    ls -lh "$MOUNT_POINT" | head -15
else
    echo "❌ Mount failed!"
    exit 1
fi
echo ""

# Step 2: Verify video paths exist
echo "Step 2: Verifying video paths..."
PATHS=(
    "$MOUNT_POINT/docker/data/torrents/torrents"
    "$MOUNT_POINT/docker/transmission/downloads/complete/tv"
    "$MOUNT_POINT/docker/transmission/downloads/complete/movies"
    "$MOUNT_POINT/video"
)

for path in "${PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "✓ Found: $path"
        file_count=$(find "$path" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.avi" \) 2>/dev/null | wc -l)
        echo "  ($file_count video files at top level)"
    else
        echo "✗ Not found: $path"
    fi
done
echo ""

# Step 3: Add to fstab for automount
echo "Step 3: Adding to /etc/fstab..."

FSTAB_ENTRY="//$NAS_HOST/$NAS_SHARE $MOUNT_POINT cifs credentials=$CREDS_FILE,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0,nofail,x-systemd.automount 0 0"

if grep -q "$MOUNT_POINT" /etc/fstab; then
    echo "⚠ Already in /etc/fstab, skipping..."
else
    cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d-%H%M%S)
    echo "" >> /etc/fstab
    echo "# MediaVault NAS mount - volume1 (added $(date))" >> /etc/fstab
    echo "$FSTAB_ENTRY" >> /etc/fstab
    echo "✓ Added to /etc/fstab"
fi
echo ""

echo "======================================"
echo "✓ NAS Volume1 Mounted!"
echo "======================================"
echo ""
echo "Mount point: $MOUNT_POINT"
echo "Will auto-mount on boot"
echo ""
echo "Next: Test video playback with GPU transcoding!"
echo ""
