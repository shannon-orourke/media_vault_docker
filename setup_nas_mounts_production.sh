#!/bin/bash
# Production NAS Mount Setup for MediaVault
# Creates proper mount structure matching backend expectations

set -e

echo "======================================"
echo "MediaVault Production NAS Mount Setup"
echo "======================================"
echo ""

# Configuration
NAS_HOST="10.27.10.11"
NAS_USER="ProxmoxBackupsSMB"
NAS_PASS="Setup123"
MOUNT_BASE="/mnt/nas-media"
CREDS_FILE="/root/.nas-credentials"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Must run as root (use sudo)"
    exit 1
fi

# Step 1: Install dependencies
echo "Step 1: Installing cifs-utils..."
if ! command -v mount.cifs &> /dev/null; then
    apt-get update -qq
    apt-get install -y cifs-utils
    echo "✓ cifs-utils installed"
else
    echo "✓ cifs-utils already installed"
fi
echo ""

# Step 2: Create directory structure
echo "Step 2: Creating mount directory structure..."
mkdir -p "${MOUNT_BASE}/volume1/docker"
mkdir -p "${MOUNT_BASE}/volume1/videos"
echo "✓ Created ${MOUNT_BASE}/volume1/docker"
echo "✓ Created ${MOUNT_BASE}/volume1/videos"
echo ""

# Step 3: Create/update credentials file
echo "Step 3: Creating NAS credentials..."
cat > "$CREDS_FILE" <<EOF
username=$NAS_USER
password=$NAS_PASS
EOF
chmod 600 "$CREDS_FILE"
echo "✓ Credentials saved securely"
echo ""

# Step 4: Unmount old mounts if they exist
echo "Step 4: Cleaning up old mounts..."
if mountpoint -q "/mnt/nas-synology/docker"; then
    echo "  Unmounting old /mnt/nas-synology/docker..."
    umount "/mnt/nas-synology/docker"
fi
if mountpoint -q "/mnt/nas-synology/video"; then
    echo "  Unmounting old /mnt/nas-synology/video..."
    umount "/mnt/nas-synology/video"
fi
echo "✓ Old mounts cleaned up"
echo ""

# Step 5: Test manual mounts
echo "Step 5: Testing manual mounts..."

# Mount docker
echo "  Mounting docker share..."
mount -t cifs "//${NAS_HOST}/docker" "${MOUNT_BASE}/volume1/docker" \
    -o credentials="${CREDS_FILE}",uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0

if mountpoint -q "${MOUNT_BASE}/volume1/docker"; then
    echo "  ✓ Docker share mounted"
    ls "${MOUNT_BASE}/volume1/docker" | head -5
else
    echo "  ❌ Docker mount failed"
    exit 1
fi

# Mount video
echo "  Mounting video share..."
mount -t cifs "//${NAS_HOST}/video" "${MOUNT_BASE}/volume1/videos" \
    -o credentials="${CREDS_FILE}",uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0

if mountpoint -q "${MOUNT_BASE}/volume1/videos"; then
    echo "  ✓ Video share mounted"
    ls "${MOUNT_BASE}/volume1/videos" | head -5
else
    echo "  ❌ Video mount failed"
    exit 1
fi
echo ""

# Step 6: Create systemd mount units
echo "Step 6: Creating systemd mount units..."

# Docker mount unit
cat > /etc/systemd/system/mnt-nas\\x2dmedia-volume1-docker.mount <<'EOF'
[Unit]
Description=MediaVault NAS Docker Share
After=network-online.target
Wants=network-online.target

[Mount]
What=//10.27.10.11/docker
Where=/mnt/nas-media/volume1/docker
Type=cifs
Options=credentials=/root/.nas-credentials,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0,nofail,x-systemd.automount,x-systemd.idle-timeout=60

[Install]
WantedBy=multi-user.target
EOF

# Video mount unit
cat > /etc/systemd/system/mnt-nas\\x2dmedia-volume1-videos.mount <<'EOF'
[Unit]
Description=MediaVault NAS Video Share
After=network-online.target
Wants=network-online.target

[Mount]
What=//10.27.10.11/video
Where=/mnt/nas-media/volume1/videos
Type=cifs
Options=credentials=/root/.nas-credentials,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0,nofail,x-systemd.automount,x-systemd.idle-timeout=60

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Created systemd mount units"
echo ""

# Step 7: Enable and start mount units
echo "Step 7: Enabling systemd mount units..."
systemctl daemon-reload
systemctl enable mnt-nas\\x2dmedia-volume1-docker.mount
systemctl enable mnt-nas\\x2dmedia-volume1-videos.mount
echo "✓ Mount units enabled"
echo ""

# Step 8: Remove old fstab entries
echo "Step 8: Cleaning up /etc/fstab..."
if grep -q "/mnt/nas-synology" /etc/fstab; then
    cp /etc/fstab "/etc/fstab.backup.$(date +%Y%m%d-%H%M%S)"
    sed -i '/MediaVault NAS mounts/d' /etc/fstab
    sed -i '/mnt\/nas-synology/d' /etc/fstab
    echo "✓ Removed old fstab entries (backup created)"
else
    echo "✓ No old entries to remove"
fi
echo ""

# Step 9: Verify mounts
echo "Step 9: Verifying mount structure..."
echo ""
echo "Mount Status:"
mountpoint "${MOUNT_BASE}/volume1/docker" && echo "  ✓ Docker mounted"
mountpoint "${MOUNT_BASE}/volume1/videos" && echo "  ✓ Videos mounted"
echo ""
echo "Disk Usage:"
df -h "${MOUNT_BASE}/volume1/docker" | tail -1
df -h "${MOUNT_BASE}/volume1/videos" | tail -1
echo ""

echo "======================================"
echo "✓ Production NAS Mounts Complete!"
echo "======================================"
echo ""
echo "Mount Structure:"
echo "  Base: ${MOUNT_BASE}"
echo "  Docker: ${MOUNT_BASE}/volume1/docker"
echo "  Videos: ${MOUNT_BASE}/volume1/videos"
echo ""
echo "Backend Scan Paths (configured):"
echo "  /volume1/docker"
echo "  /volume1/videos"
echo ""
echo "Full Paths:"
echo "  ${MOUNT_BASE}/volume1/docker"
echo "  ${MOUNT_BASE}/volume1/videos"
echo ""
echo "Next Steps:"
echo "  1. Verify mount health: sudo systemctl status mnt-nas*"
echo "  2. Test persistence: sudo reboot (mounts should auto-restore)"
echo "  3. Deploy health monitoring service"
echo ""
