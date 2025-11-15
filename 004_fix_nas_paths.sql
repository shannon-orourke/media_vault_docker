-- Fix NAS mount paths in database
-- Changes /mnt/nas-synology/transmission to /mnt/nas-synology/docker/transmission

BEGIN;

-- Show current paths before update
SELECT
    'BEFORE UPDATE' as status,
    COUNT(*) as total_files,
    COUNT(CASE WHEN filepath LIKE '/mnt/nas-synology/transmission/%' THEN 1 END) as old_transmission_paths
FROM media_files;

-- Update transmission paths
UPDATE media_files
SET filepath = REPLACE(filepath, '/mnt/nas-synology/transmission/', '/mnt/nas-synology/docker/transmission/')
WHERE filepath LIKE '/mnt/nas-synology/transmission/%';

-- Show results after update
SELECT
    'AFTER UPDATE' as status,
    COUNT(*) as total_files,
    COUNT(CASE WHEN filepath LIKE '/mnt/nas-synology/docker/transmission/%' THEN 1 END) as new_docker_paths,
    COUNT(CASE WHEN filepath LIKE '/mnt/nas-synology/transmission/%' THEN 1 END) as remaining_old_paths
FROM media_files;

-- Show sample of updated paths
SELECT id, filename, filepath
FROM media_files
WHERE filepath LIKE '/mnt/nas-synology/docker/transmission/%'
LIMIT 5;

COMMIT;
