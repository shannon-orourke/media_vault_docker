#!/bin/bash
# Monitor backend logs in real-time

echo "======================================"
echo "Monitoring MediaVault Backend Logs"
echo "======================================"
echo ""
echo "Watching for streaming requests..."
echo "Try playing a video now!"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Follow backend logs
sudo journalctl -u mediavault-backend -f --no-pager | grep -E "(stream|progressive|smart|ffmpeg|NVENC|error|ERROR|Starting|GPU)" --color=always
