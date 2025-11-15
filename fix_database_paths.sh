#!/bin/bash
# Fix database paths to match new NAS mount structure

set -e

echo "======================================"
echo "Fixing MediaVault Database Paths"
echo "======================================"
echo ""

DB_NAME="mediavault"
DB_USER="pm_ideas_user"
DB_HOST="localhost"
DB_PORT="5433"

echo "This will update paths from:"
echo "  /mnt/nas-synology/transmission/"
echo "to:"
echo "  /mnt/nas-synology/docker/transmission/"
echo ""

# Get postgres password from pm-ideas project
if [ -f "/home/mercury/projects/pm-ideas/.env" ]; then
    export PGPASSWORD=$(grep POSTGRES_PASSWORD /home/mercury/projects/pm-ideas/.env | cut -d '=' -f2)
    echo "✓ Found database password"
else
    echo "❌ Cannot find password. Enter it manually:"
    read -sp "PostgreSQL password: " PGPASSWORD
    export PGPASSWORD
    echo ""
fi
echo ""

# Run the migration
echo "Running database migration..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f 004_fix_nas_paths.sql

echo ""
echo "======================================"
echo "✓ Database Paths Updated!"
echo "======================================"
echo ""
echo "Now test video playback:"
echo "  1. Go to https://mediavault.orourkes.me/library"
echo "  2. Click play on any Red Dwarf episode"
echo "  3. In another terminal: watch -n 1 nvidia-smi"
echo "  4. You should see GPU encoder activity!"
echo ""
