#!/bin/bash
echo "Fetching recent backend errors..."
echo ""
sudo journalctl -u mediavault-backend -n 100 --no-pager | grep -A 5 -B 5 -E "(ERROR|error|Exception|Traceback)" | tail -50
