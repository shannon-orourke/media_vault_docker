#!/bin/bash
# Mount both NAS shares (docker and video)

set -e

NAS_HOST="10.27.10.11"
CREDS_FILE="/root/.nas-credentials"

# Mount points
DOCKER_MOUNT="/mnt/nas-synology/docker"
VIDEO_MOUNT="/mnt/nas-synology/video"

echo "======================================"
echo "Mounting NAS Shares"
echo "======================================"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "❌ Must run as root (use sudo)"
    exit 1
fi

# Create mount points
echo "Creating mount points..."
mkdir -p "$DOCKER_MOUNT"
mkdir -p "$VIDEO_MOUNT"
echo "✓ Mount points created"
echo ""

# Mount docker share
echo "Mounting //10.27.10.11/docker..."
if mountpoint -q "$DOCKER_MOUNT"; then
    echo "  Already mounted, unmounting..."
    umount "$DOCKER_MOUNT"
fi

mount -t cifs "//10.27.10.11/docker" "$DOCKER_MOUNT" \
    -o credentials="$CREDS_FILE",uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0

if mountpoint -q "$DOCKER_MOUNT"; then
    echo "✓ Docker share mounted!"
    echo "  Contents:"
    ls "$DOCKER_MOUNT" | head -5
else
    echo "❌ Docker mount failed!"
    exit 1
fi
echo ""

# Mount video share
echo "Mounting //10.27.10.11/video..."
if mountpoint -q "$VIDEO_MOUNT"; then
    echo "  Already mounted, unmounting..."
    umount "$VIDEO_MOUNT"
fi

mount -t cifs "//10.27.10.11/video" "$VIDEO_MOUNT" \
    -o credentials="$CREDS_FILE",uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0

if mountpoint -q "$VIDEO_MOUNT"; then
    echo "✓ Video share mounted!"
    echo "  Contents:"
    ls "$VIDEO_MOUNT" | head -5
else
    echo "❌ Video mount failed!"
    exit 1
fi
echo ""

# Verify your paths exist
echo "Verifying video paths..."
PATHS=(
    "$DOCKER_MOUNT/data/torrents/torrents"
    "$DOCKER_MOUNT/transmission/downloads/complete/tv"
    "$DOCKER_MOUNT/transmission/downloads/complete/movies"
    "$VIDEO_MOUNT"
)

for path in "${PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "✓ Found: $path"
        # Count video files
        count=$(find "$path" -maxdepth 2 -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.avi" \) 2>/dev/null | wc -l)
        echo "  (~$count video files)"
    else
        echo "✗ Not found: $path"
    fi
done
echo ""

# Add to fstab
echo "Adding to /etc/fstab for automount..."

# Backup fstab
if ! grep -q "$DOCKER_MOUNT" /etc/fstab; then
    cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d-%H%M%S)
    echo "" >> /etc/fstab
    echo "# MediaVault NAS mounts (added $(date))" >> /etc/fstab
    echo "//10.27.10.11/docker $DOCKER_MOUNT cifs credentials=$CREDS_FILE,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0,nofail,x-systemd.automount 0 0" >> /etc/fstab
    echo "//10.27.10.11/video $VIDEO_MOUNT cifs credentials=$CREDS_FILE,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0,nofail,x-systemd.automount 0 0" >> /etc/fstab
    echo "✓ Added to /etc/fstab"
else
    echo "✓ Already in /etc/fstab"
fi
echo ""

echo "======================================"
echo "✓ NAS Shares Mounted!"
echo "======================================"
echo ""
echo "Docker mount: $DOCKER_MOUNT"
echo "Video mount:  $VIDEO_MOUNT"
echo ""
echo "Scan paths for MediaVault:"
echo "  $DOCKER_MOUNT/data/torrents/torrents"
echo "  $DOCKER_MOUNT/transmission/downloads/complete/tv"
echo "  $DOCKER_MOUNT/transmission/downloads/complete/movies"
echo "  $VIDEO_MOUNT"
echo ""
echo "Next: Test GPU video playback!"
echo ""
