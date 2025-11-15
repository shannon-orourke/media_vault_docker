# NAS Mount Setup and Monitoring

**Created:** 2025-11-10
**Status:** Ready for deployment

## Overview

This solution provides automated NAS mount persistence and health monitoring for MediaVault, solving the critical operational issue of unstable SMB connections.

## Problem Statement

The MediaVault backend requires stable access to Synology NAS shares at specific paths:
- `/mnt/nas-media/volume1/docker`
- `/mnt/nas-media/volume1/videos`

Without automated mount persistence and health monitoring, the system is at risk of losing NAS access on:
- System reboots
- Network disconnections
- SMB connection timeouts
- NAS restarts

## Solution Components

### 1. Production Mount Setup (`setup_nas_mounts_production.sh`)

**Purpose:** Creates proper mount structure matching backend expectations

**What it does:**
- Installs `cifs-utils` if needed
- Creates mount directory structure at `/mnt/nas-media/volume1/`
- Mounts NAS shares at correct paths:
  - `//10.27.10.11/docker` → `/mnt/nas-media/volume1/docker`
  - `//10.27.10.11/video` → `/mnt/nas-media/volume1/videos`
- Creates systemd mount units for automatic mounting
- Removes old incompatible fstab entries
- Enables systemd units for boot persistence

**Usage:**
```bash
sudo ./setup_nas_mounts_production.sh
```

### 2. Health Monitor Script (`nas_mount_health_monitor.sh`)

**Purpose:** Continuously monitors mount health and auto-remounts on failure

**What it does:**
- Checks if mount points are accessible
- Attempts to read from each mount (timeout protection)
- Auto-remounts using systemd on failure
- Logs all activity to `/var/log/mediavault-mount-health.log`
- Returns appropriate exit codes for systemd monitoring

**Features:**
- Graceful remount on stale mounts
- Force remount on unresponsive mounts
- Detailed logging with timestamps
- Safe timeout handling

### 3. Systemd Service & Timer

**Files:**
- `mediavault-mount-health.service` - Health check service
- `mediavault-mount-health.timer` - Runs every 5 minutes

**Features:**
- Automatic health checks every 5 minutes
- Runs 2 minutes after boot
- Integrates with systemd journal for logging
- Can be triggered manually for immediate checks

### 4. Backend Health Check (`backend/check_nas_mounts.py`)

**Purpose:** Pre-flight check for backend startup

**What it does:**
- Verifies all required NAS mounts are accessible
- Prevents backend from starting with unhealthy mounts
- Provides clear troubleshooting guidance
- Returns non-zero exit code on failure

**Usage:**
```bash
python3 backend/check_nas_mounts.py
```

### 5. Deployment Script (`deploy_nas_monitoring.sh`)

**Purpose:** One-command deployment of entire solution

**What it does:**
- Runs production mount setup
- Installs health monitor to `/usr/local/bin/`
- Installs systemd service and timer
- Enables and starts health monitoring
- Runs initial health check
- Displays verification status

**Usage:**
```bash
sudo ./deploy_nas_monitoring.sh
```

## Deployment Instructions

### Quick Deploy (Recommended)

```bash
cd /home/mercury/projects/mediavault
sudo ./deploy_nas_monitoring.sh
```

This will:
1. ✅ Set up correct mount structure
2. ✅ Enable automatic mounting on boot
3. ✅ Install health monitoring
4. ✅ Start periodic health checks
5. ✅ Verify everything is working

### Manual Step-by-Step Deploy

If you prefer to deploy components separately:

```bash
# 1. Set up mounts
sudo ./setup_nas_mounts_production.sh

# 2. Install health monitor
sudo cp nas_mount_health_monitor.sh /usr/local/bin/mediavault-mount-health-monitor.sh
sudo chmod +x /usr/local/bin/mediavault-mount-health-monitor.sh

# 3. Install systemd units
sudo cp mediavault-mount-health.service /etc/systemd/system/
sudo cp mediavault-mount-health.timer /etc/systemd/system/

# 4. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable mediavault-mount-health.timer
sudo systemctl start mediavault-mount-health.timer

# 5. Run initial check
sudo systemctl start mediavault-mount-health.service
```

## Verification

### Check Mount Status

```bash
# Check if mounts are active
mountpoint /mnt/nas-media/volume1/docker
mountpoint /mnt/nas-media/volume1/videos

# Check systemd mount status
sudo systemctl status mnt-nas-media-volume1-docker.mount
sudo systemctl status mnt-nas-media-volume1-videos.mount

# Check disk usage
df -h /mnt/nas-media/volume1/docker
df -h /mnt/nas-media/volume1/videos
```

### Check Health Monitoring

```bash
# Check health timer status
sudo systemctl status mediavault-mount-health.timer

# View recent health check logs
sudo journalctl -u mediavault-mount-health -n 50

# Follow health logs in real-time
sudo journalctl -u mediavault-mount-health -f

# View health log file
sudo tail -f /var/log/mediavault-mount-health.log
```

### Backend Health Check

```bash
# From backend directory
cd backend
python3 check_nas_mounts.py
```

Expected output:
```
==================================================
MediaVault NAS Mount Health Check
==================================================

✓ Docker share is healthy
✓ Video share is healthy

All NAS mounts are healthy ✓
```

## Testing Resilience

### Test Auto-Recovery After Unmount

```bash
# 1. Manually unmount to simulate failure
sudo umount /mnt/nas-media/volume1/docker

# 2. Trigger health check (or wait 5 minutes)
sudo systemctl start mediavault-mount-health.service

# 3. Verify auto-remount
mountpoint /mnt/nas-media/volume1/docker
# Should show: /mnt/nas-media/volume1/docker is a mountpoint
```

### Test Persistence After Reboot

```bash
# 1. Reboot system
sudo reboot

# 2. After boot, check mounts
mountpoint /mnt/nas-media/volume1/docker
mountpoint /mnt/nas-media/volume1/videos

# Both should be automatically mounted
```

## Integration with Backend

### Docker Compose Integration

Add health check to backend service in `docker-compose.yml`:

```yaml
services:
  backend:
    build: ./backend
    volumes:
      - /mnt/nas-media:/mnt/nas-media:ro
    healthcheck:
      test: ["CMD", "python3", "/app/check_nas_mounts.py"]
      interval: 5m
      timeout: 10s
      retries: 3
      start_period: 30s
```

### Backend Startup Script

Add to backend entrypoint:

```bash
#!/bin/bash
# Backend startup script

echo "Checking NAS mounts..."
python3 check_nas_mounts.py

if [ $? -ne 0 ]; then
    echo "ERROR: NAS mounts are not healthy. Exiting."
    exit 1
fi

echo "NAS mounts are healthy. Starting backend..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Mount Not Appearing After Boot

```bash
# Check systemd mount unit status
sudo systemctl status mnt-nas-media-volume1-docker.mount

# Check logs
sudo journalctl -u mnt-nas-media-volume1-docker.mount -n 50

# Manual start
sudo systemctl start mnt-nas-media-volume1-docker.mount
```

### Health Check Failing

```bash
# View detailed logs
sudo journalctl -u mediavault-mount-health -n 100

# Check mount accessibility
ls -la /mnt/nas-media/volume1/docker
ls -la /mnt/nas-media/volume1/videos

# Test NAS connectivity
ping -c 3 10.27.10.11

# Test SMB connection
smbclient -L //10.27.10.11 -U ProxmoxBackupsSMB%Setup123
```

### Stale Mount (Unresponsive)

```bash
# Force unmount
sudo umount -l /mnt/nas-media/volume1/docker

# Restart mount unit
sudo systemctl restart mnt-nas-media-volume1-docker.mount

# Or trigger health monitor
sudo systemctl start mediavault-mount-health.service
```

## Monitoring and Alerting

### Watch Health Logs

```bash
# Real-time monitoring
sudo journalctl -u mediavault-mount-health -f

# Or watch log file
sudo tail -f /var/log/mediavault-mount-health.log
```

### Integration with External Monitoring

The health check service returns appropriate exit codes:
- `0` - All mounts healthy
- `1` - Partial failure (some mounts recovered)
- `2` - Critical failure (all mounts failed)

You can integrate this with monitoring systems like:
- Prometheus + Alertmanager
- Nagios
- Datadog
- Custom scripts

Example monitoring script:
```bash
#!/bin/bash
# Check MediaVault mount health

if ! systemctl is-active --quiet mediavault-mount-health.timer; then
    echo "CRITICAL: Health monitoring timer not running"
    exit 2
fi

# Check last health check result
if systemctl is-failed --quiet mediavault-mount-health.service; then
    echo "WARNING: Last health check failed"
    exit 1
fi

echo "OK: Mount health monitoring active"
exit 0
```

## Files Created

```
mediavault/
├── setup_nas_mounts_production.sh      # Production mount setup
├── nas_mount_health_monitor.sh         # Health monitoring script
├── deploy_nas_monitoring.sh            # One-command deployment
├── mediavault-mount-health.service     # Systemd service unit
├── mediavault-mount-health.timer       # Systemd timer unit
├── backend/check_nas_mounts.py         # Backend pre-flight check
└── NAS_MOUNT_SETUP.md                  # This document
```

## Next Steps

After deployment:

1. ✅ Deploy this solution: `sudo ./deploy_nas_monitoring.sh`
2. ⏭️ Run real NAS scan to populate database
3. ⏭️ Validate duplicate detection with real data
4. ⏭️ Test deletion staging and restore workflows
5. ⏭️ Test video playback in browsers

## Security Notes

- NAS credentials stored in `/root/.nas-credentials` (mode 600)
- Only root can access credentials file
- Mounts run with uid=1000, gid=1000 for mercury user
- Health monitor runs as root (required for mount operations)

## Performance Notes

- Health checks run every 5 minutes (configurable in timer)
- Mount timeout protection (5 seconds)
- Systemd automount provides lazy mounting
- Idle timeout of 60 seconds to reduce NAS load

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u mediavault-mount-health`
2. Review this documentation
3. Check systemd mount status
4. Verify NAS connectivity

---

**Status:** Ready for deployment ✅
**Last Updated:** 2025-11-10
