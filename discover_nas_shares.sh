#!/bin/bash
# Discover available NAS shares by testing common names

NAS_HOST="10.27.10.11"
CREDS_FILE="/root/.nas-credentials"
MOUNT_POINT="/mnt/nas-synology"

echo "======================================"
echo "NAS Share Discovery"
echo "======================================"
echo ""
echo "Testing common Synology share names..."
echo ""

# Common Synology share names
SHARES=(
    "video"
    "videos"
    "Video"
    "docker"
    "Docker"
    "volume1"
    "homes"
    "public"
    "transmission"
    "downloads"
)

# Test each share
for share in "${SHARES[@]}"; do
    echo -n "Testing //$NAS_HOST/$share ... "

    if timeout 3 mount -t cifs "//$NAS_HOST/$share" "$MOUNT_POINT" \
        -o credentials="$CREDS_FILE",uid=1000,gid=1000,vers=3.0 2>/dev/null; then

        echo "✓ SUCCESS!"
        echo "  Mounted: //$NAS_HOST/$share"
        echo "  Contents:"
        ls -lh "$MOUNT_POINT" | head -10

        # Unmount
        umount "$MOUNT_POINT" 2>/dev/null
        echo ""

    else
        echo "✗ Not accessible"
    fi
done

echo ""
echo "======================================"
echo "If you see ✓ SUCCESS above, use that share name."
echo ""
echo "If no shares worked, check:"
echo "  1. NAS IP: $NAS_HOST (verify in Synology DSM)"
echo "  2. Username: ProxmoxBackupsSMB"
echo "  3. Password in: $CREDS_FILE"
echo "  4. SMB service enabled in Synology DSM"
echo ""
