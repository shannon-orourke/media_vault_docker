#!/bin/bash
# NAS Mount Health Monitor for MediaVault
# Checks mount health and auto-remounts if needed

MOUNT_BASE="/mnt/nas-media"
DOCKER_MOUNT="${MOUNT_BASE}/volume1/docker"
VIDEO_MOUNT="${MOUNT_BASE}/volume1/videos"
LOG_FILE="/var/log/mediavault-mount-health.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_and_remount() {
    local mount_point="$1"
    local mount_name="$2"

    # Check if mountpoint is valid
    if ! mountpoint -q "$mount_point"; then
        log "WARNING: $mount_name not mounted at $mount_point"

        # Try to remount using systemd
        log "Attempting to remount $mount_name..."

        # Get the systemd unit name (escape path)
        local unit_name=$(systemd-escape --path "$mount_point").mount

        # Restart the mount unit
        if systemctl restart "$unit_name"; then
            log "SUCCESS: Remounted $mount_name"
            return 0
        else
            log "ERROR: Failed to remount $mount_name"
            return 1
        fi
    fi

    # Check if we can actually read the mount
    if ! timeout 5 ls "$mount_point" &>/dev/null; then
        log "WARNING: $mount_name is mounted but not readable"

        # Force remount
        log "Forcing remount of $mount_name..."
        local unit_name=$(systemd-escape --path "$mount_point").mount

        systemctl stop "$unit_name"
        sleep 2

        if systemctl start "$unit_name"; then
            log "SUCCESS: Force remounted $mount_name"
            return 0
        else
            log "ERROR: Failed to force remount $mount_name"
            return 1
        fi
    fi

    # Mount is healthy
    return 0
}

# Main health check
log "Starting NAS mount health check..."

docker_healthy=false
video_healthy=false

# Check docker mount
if check_and_remount "$DOCKER_MOUNT" "Docker"; then
    docker_healthy=true
fi

# Check video mount
if check_and_remount "$VIDEO_MOUNT" "Videos"; then
    video_healthy=true
fi

# Log final status
if $docker_healthy && $video_healthy; then
    log "All mounts healthy ✓"
    exit 0
elif $docker_healthy || $video_healthy; then
    log "Partial mount failure (some mounts recovered)"
    exit 1
else
    log "CRITICAL: All mounts failed"
    exit 2
fi
