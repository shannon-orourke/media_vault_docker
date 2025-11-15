#!/bin/bash
# Deploy NAS Mount Monitoring for MediaVault
# This script sets up automated mount persistence and health monitoring

set -e

echo "======================================"
echo "MediaVault NAS Monitoring Deployment"
echo "======================================"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Must run as root (use sudo)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 1: Run production mount setup
echo "Step 1: Setting up production NAS mounts..."
echo ""
bash "${SCRIPT_DIR}/setup_nas_mounts_production.sh"
echo ""

# Step 2: Install health monitor script
echo "Step 2: Installing health monitor script..."
cp "${SCRIPT_DIR}/nas_mount_health_monitor.sh" /usr/local/bin/mediavault-mount-health-monitor.sh
chmod +x /usr/local/bin/mediavault-mount-health-monitor.sh
echo "✓ Health monitor installed to /usr/local/bin/"
echo ""

# Step 3: Install systemd service and timer
echo "Step 3: Installing systemd service and timer..."
cp "${SCRIPT_DIR}/mediavault-mount-health.service" /etc/systemd/system/
cp "${SCRIPT_DIR}/mediavault-mount-health.timer" /etc/systemd/system/
echo "✓ Systemd units installed"
echo ""

# Step 4: Enable and start health monitoring
echo "Step 4: Enabling health monitoring..."
systemctl daemon-reload
systemctl enable mediavault-mount-health.timer
systemctl start mediavault-mount-health.timer
echo "✓ Health monitoring enabled and started"
echo ""

# Step 5: Run initial health check
echo "Step 5: Running initial health check..."
systemctl start mediavault-mount-health.service
echo "✓ Initial health check complete"
echo ""

# Step 6: Show status
echo "Step 6: Verification..."
echo ""
echo "Mount Status:"
systemctl status mnt-nas\\x2dmedia-volume1-docker.mount --no-pager -l || true
echo ""
systemctl status mnt-nas\\x2dmedia-volume1-videos.mount --no-pager -l || true
echo ""

echo "Health Monitor Timer:"
systemctl status mediavault-mount-health.timer --no-pager -l || true
echo ""

echo "Recent Health Logs:"
journalctl -u mediavault-mount-health.service -n 20 --no-pager || true
echo ""

echo "======================================"
echo "✓ NAS Monitoring Deployment Complete!"
echo "======================================"
echo ""
echo "Summary:"
echo "  ✓ NAS mounts configured at /mnt/nas-media/volume1/"
echo "  ✓ Systemd mount units enabled (auto-mount on boot)"
echo "  ✓ Health monitoring service installed"
echo "  ✓ Health checks run every 5 minutes"
echo ""
echo "Useful Commands:"
echo "  Check mount status:    sudo systemctl status mnt-nas-media-volume1-*"
echo "  Check health timer:    sudo systemctl status mediavault-mount-health.timer"
echo "  View health logs:      sudo journalctl -u mediavault-mount-health -f"
echo "  Manual health check:   sudo systemctl start mediavault-mount-health.service"
echo "  Restart mounts:        sudo systemctl restart mnt-nas-media-volume1-*.mount"
echo ""
echo "Log File:"
echo "  /var/log/mediavault-mount-health.log"
echo ""
