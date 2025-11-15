#!/bin/bash
# Simple backend restart script
cd /home/mercury/projects/mediavault
echo "Stopping backend workers..."
pkill -f "uvicorn app.main:app" || true
sleep 3
echo "Backend stopped. Please manually start with: sudo systemctl start mediavault-backend"
echo "Or if running the iterative loop, it will restart automatically."
