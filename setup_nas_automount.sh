#!/bin/bash
# Setup NAS automount for MediaVault

set -e

echo "======================================"
echo "MediaVault NAS Automount Setup"
echo "======================================"
echo ""

# NAS Configuration (from CLAUDE.md)
NAS_HOST="10.27.10.11"
NAS_USER="ProxmoxBackupsSMB"
NAS_PASS="Setup123"
MOUNT_POINT="/mnt/nas-synology"
CREDS_FILE="/root/.nas-credentials"

echo "Configuration:"
echo "  NAS Host: $NAS_HOST"
echo "  NAS User: $NAS_USER"
echo "  Mount Point: $MOUNT_POINT"
echo "  Credentials: $CREDS_FILE"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Step 1: Install cifs-utils
echo "Step 1: Installing cifs-utils..."
if ! command -v mount.cifs &> /dev/null; then
    apt-get update -qq
    apt-get install -y cifs-utils
    echo "✓ cifs-utils installed"
else
    echo "✓ cifs-utils already installed"
fi
echo ""

# Step 2: Create mount point
echo "Step 2: Creating mount point..."
if [ ! -d "$MOUNT_POINT" ]; then
    mkdir -p "$MOUNT_POINT"
    echo "✓ Created $MOUNT_POINT"
else
    echo "✓ Mount point already exists"
fi
echo ""

# Step 3: Create credentials file
echo "Step 3: Creating NAS credentials file..."
cat > "$CREDS_FILE" <<EOF
username=$NAS_USER
password=$NAS_PASS
EOF

chmod 600 "$CREDS_FILE"
echo "✓ Credentials saved to $CREDS_FILE (secure permissions: 600)"
echo ""

# Step 4: Test mount manually first
echo "Step 4: Testing manual mount..."
echo "Attempting to mount //10.27.10.11/transmission to $MOUNT_POINT"

# Unmount if already mounted
if mountpoint -q "$MOUNT_POINT"; then
    echo "Unmounting existing mount..."
    umount "$MOUNT_POINT"
fi

# Try to mount
mount -t cifs "//$NAS_HOST/transmission" "$MOUNT_POINT" \
    -o credentials="$CREDS_FILE",uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0

if mountpoint -q "$MOUNT_POINT"; then
    echo "✓ Manual mount successful!"
    echo ""
    echo "Contents of NAS:"
    ls -lh "$MOUNT_POINT" | head -10
    echo ""

    # Unmount for now (will use fstab for automount)
    umount "$MOUNT_POINT"
    echo "✓ Test mount unmounted"
else
    echo "❌ Mount failed!"
    exit 1
fi
echo ""

# Step 5: Add to /etc/fstab for automount
echo "Step 5: Adding to /etc/fstab for automount..."

FSTAB_ENTRY="//$NAS_HOST/transmission $MOUNT_POINT cifs credentials=$CREDS_FILE,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,vers=3.0,nofail,x-systemd.automount 0 0"

# Check if entry already exists
if grep -q "$MOUNT_POINT" /etc/fstab; then
    echo "⚠ Mount point already in /etc/fstab, skipping..."
else
    # Backup fstab
    cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d-%H%M%S)
    echo "✓ Backed up /etc/fstab"

    # Add entry
    echo "" >> /etc/fstab
    echo "# MediaVault NAS mount (added $(date))" >> /etc/fstab
    echo "$FSTAB_ENTRY" >> /etc/fstab
    echo "✓ Added to /etc/fstab"
fi
echo ""

# Step 6: Mount using fstab
echo "Step 6: Mounting using fstab..."
mount -a

if mountpoint -q "$MOUNT_POINT"; then
    echo "✓ NAS mounted successfully!"
    echo ""
    echo "Mounted filesystem info:"
    df -h "$MOUNT_POINT"
    echo ""
    echo "Contents:"
    ls -lh "$MOUNT_POINT" | head -10
else
    echo "❌ Automount failed! Check /etc/fstab"
    exit 1
fi
echo ""

# Step 7: Test access
echo "Step 7: Testing file access..."
if [ -d "$MOUNT_POINT/downloads" ]; then
    echo "✓ Can access downloads folder"
    ls -lh "$MOUNT_POINT/downloads" | head -5
else
    echo "⚠ Downloads folder not found, checking what's available:"
    find "$MOUNT_POINT" -maxdepth 2 -type d | head -10
fi
echo ""

echo "======================================"
echo "✓ NAS Automount Setup Complete!"
echo "======================================"
echo ""
echo "Summary:"
echo "  - cifs-utils installed"
echo "  - Credentials stored securely in $CREDS_FILE"
echo "  - Mount point: $MOUNT_POINT"
echo "  - fstab configured for automount on boot"
echo "  - NAS is currently mounted and accessible"
echo ""
echo "The NAS will automatically mount on system boot."
echo ""
echo "To verify mount at any time:"
echo "  mountpoint $MOUNT_POINT"
echo "  df -h $MOUNT_POINT"
echo ""
echo "To manually unmount:"
echo "  sudo umount $MOUNT_POINT"
echo ""
echo "To manually mount:"
echo "  sudo mount $MOUNT_POINT"
echo ""
