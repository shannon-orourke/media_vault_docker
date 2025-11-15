#!/bin/bash
# Test various NAS share combinations

NAS_HOST="10.27.10.11"
MOUNT_POINT="/mnt/nas-synology"
CREDS_FILE="/root/.nas-credentials"

if [ "$EUID" -ne 0 ]; then
    echo "Must run as root"
    exit 1
fi

echo "Testing NAS shares on $NAS_HOST..."
echo ""

# Test shares based on your paths
SHARES=(
    "docker"
    "transmission"
    "torrents"
    "video"
    "homes"
    "homes/ProxmoxBackupsSMB"
    "volume1"
    "data"
)

for share in "${SHARES[@]}"; do
    echo -n "Testing: //$NAS_HOST/$share ... "

    if timeout 5 mount -t cifs "//$NAS_HOST/$share" "$MOUNT_POINT" \
        -o credentials="$CREDS_FILE",uid=1000,gid=1000,vers=3.0 2>/dev/null; then

        echo "✓ SUCCESS!"
        echo "  Contents:"
        ls "$MOUNT_POINT" | head -5

        # Check if this has the paths we need
        if [ -d "$MOUNT_POINT/transmission" ] || [ -d "$MOUNT_POINT/downloads" ] || [ -d "$MOUNT_POINT/docker" ]; then
            echo "  ⭐ Contains expected folders!"
        fi

        umount "$MOUNT_POINT" 2>/dev/null
        echo ""
    else
        echo "✗ Failed"
    fi
done

echo ""
echo "If none worked, the share might need to be created in Synology DSM."
echo "Or try different credentials/permissions."
