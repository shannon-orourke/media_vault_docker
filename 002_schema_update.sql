-- Migration: Update schema to match new models
-- Date: 2025-11-08
-- Purpose: Align duplicate_groups, duplicate_members, media_files, pending_deletions with refactored models

BEGIN;

-- ============================================================================
-- 1. Update duplicate_groups table
-- ============================================================================
ALTER TABLE duplicate_groups
    ADD COLUMN IF NOT EXISTS group_hash VARCHAR(128),
    ADD COLUMN IF NOT EXISTS duplicate_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS confidence DECIMAL(5,2),
    ADD COLUMN IF NOT EXISTS title VARCHAR(255),
    ADD COLUMN IF NOT EXISTS year INTEGER,
    ADD COLUMN IF NOT EXISTS season INTEGER,
    ADD COLUMN IF NOT EXISTS episode INTEGER,
    ADD COLUMN IF NOT EXISTS member_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS recommended_action VARCHAR(20),
    ADD COLUMN IF NOT EXISTS action_reason TEXT,
    ADD COLUMN IF NOT EXISTS detected_at TIMESTAMP;

-- Migrate old data to new columns
UPDATE duplicate_groups SET
    duplicate_type = COALESCE(group_type, 'exact'),
    confidence = confidence_score,
    title = show_name,
    season = season_number,
    episode = episode_number,
    member_count = COALESCE(file_count, 0),
    recommended_action = action_taken,
    detected_at = COALESCE(created_at, NOW())
WHERE duplicate_type IS NULL;

-- Generate group_hash for existing records (using ID as fallback)
UPDATE duplicate_groups SET
    group_hash = 'legacy_' || id::text
WHERE group_hash IS NULL;

-- Make required columns NOT NULL after migration
ALTER TABLE duplicate_groups
    ALTER COLUMN group_hash SET NOT NULL,
    ALTER COLUMN duplicate_type SET NOT NULL;

-- Drop old columns (keep as comments for safety - uncomment if sure)
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS group_type;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS confidence_score;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS show_name;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS season_number;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS episode_number;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS file_count;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS total_size;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS potential_savings;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS action_taken;
-- ALTER TABLE duplicate_groups DROP COLUMN IF EXISTS primary_file_id;

-- Add indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_duplicate_groups_hash ON duplicate_groups(group_hash);
DROP INDEX IF EXISTS idx_duplicate_groups_type;
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_type ON duplicate_groups(duplicate_type);

-- ============================================================================
-- 2. Update duplicate_members table
-- ============================================================================
ALTER TABLE duplicate_members
    ADD COLUMN IF NOT EXISTS rank INTEGER,
    ADD COLUMN IF NOT EXISTS recommended_action VARCHAR(20),
    ADD COLUMN IF NOT EXISTS action_reason TEXT;

-- Migrate old data
UPDATE duplicate_members SET
    rank = quality_rank,
    recommended_action = CASE WHEN is_primary THEN 'keep' ELSE 'review' END
WHERE rank IS NULL;

-- Drop old columns (commented for safety)
-- ALTER TABLE duplicate_members DROP COLUMN IF EXISTS quality_rank;
-- ALTER TABLE duplicate_members DROP COLUMN IF EXISTS is_primary;
-- ALTER TABLE duplicate_members DROP COLUMN IF EXISTS size_rank;
-- ALTER TABLE duplicate_members RENAME COLUMN added_at TO created_at;

-- ============================================================================
-- 3. Update media_files table
-- ============================================================================
ALTER TABLE media_files
    ADD COLUMN IF NOT EXISTS dominant_audio_language VARCHAR(10),
    ADD COLUMN IF NOT EXISTS parsed_title VARCHAR(500),
    ADD COLUMN IF NOT EXISTS parsed_year INTEGER,
    ADD COLUMN IF NOT EXISTS parsed_season INTEGER,
    ADD COLUMN IF NOT EXISTS parsed_episode INTEGER,
    ADD COLUMN IF NOT EXISTS parsed_release_group VARCHAR(100),
    ADD COLUMN IF NOT EXISTS tmdb_genres JSONB,
    ADD COLUMN IF NOT EXISTS tmdb_last_updated TIMESTAMP,
    ADD COLUMN IF NOT EXISTS quality_score INTEGER,
    ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_scanned_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS metadata_updated_at TIMESTAMP;

-- Migrate existing data
UPDATE media_files SET
    parsed_title = show_name,
    parsed_year = year,
    parsed_season = season_number,
    parsed_episode = episode_number,
    parsed_release_group = release_group,
    discovered_at = COALESCE(scanned_at, created_at, NOW()),
    last_scanned_at = COALESCE(last_verified_at, scanned_at, created_at, NOW()),
    metadata_updated_at = COALESCE(updated_at, NOW())
WHERE parsed_title IS NULL;

-- Add new indexes
CREATE INDEX IF NOT EXISTS idx_media_parsed_movie ON media_files(parsed_title, parsed_year);
CREATE INDEX IF NOT EXISTS idx_media_parsed_tv ON media_files(parsed_title, parsed_season, parsed_episode);
CREATE INDEX IF NOT EXISTS idx_media_type_quality ON media_files(media_type, quality_score);

-- ============================================================================
-- 4. Update pending_deletions table
-- ============================================================================
ALTER TABLE pending_deletions
    ADD COLUMN IF NOT EXISTS media_file_id INTEGER,
    ADD COLUMN IF NOT EXISTS file_size BIGINT,
    ADD COLUMN IF NOT EXISTS reason TEXT,
    ADD COLUMN IF NOT EXISTS better_quality_file_id INTEGER,
    ADD COLUMN IF NOT EXISTS quality_score_diff INTEGER,
    ADD COLUMN IF NOT EXISTS language_concern BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS language_concern_reason TEXT,
    ADD COLUMN IF NOT EXISTS staged_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS approved_for_deletion BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS approved_by_user_id INTEGER,
    ADD COLUMN IF NOT EXISTS deletion_metadata JSONB;

-- Migrate existing data
UPDATE pending_deletions SET
    media_file_id = file_id,
    file_size = (SELECT file_size FROM media_files WHERE id = pending_deletions.file_id),
    reason = COALESCE(deletion_reason, 'Unknown'),
    better_quality_file_id = kept_file_id,
    quality_score_diff = (quality_difference::integer),
    language_concern = COALESCE(requires_manual_review, false),
    staged_at = COALESCE(moved_to_temp_at, NOW()),
    approved_for_deletion = (reviewed AND final_action = 'approved'),
    approved_at = reviewed_at,
    approved_by_user_id = reviewed_by
WHERE media_file_id IS NULL;

-- Add foreign key constraints (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_pending_media'
    ) THEN
        ALTER TABLE pending_deletions
        ADD CONSTRAINT fk_pending_media FOREIGN KEY (media_file_id)
        REFERENCES media_files(id) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_pending_better'
    ) THEN
        ALTER TABLE pending_deletions
        ADD CONSTRAINT fk_pending_better FOREIGN KEY (better_quality_file_id)
        REFERENCES media_files(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_pending_user'
    ) THEN
        ALTER TABLE pending_deletions
        ADD CONSTRAINT fk_pending_user FOREIGN KEY (approved_by_user_id)
        REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add unique constraint on media_file_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_deletions_media_unique ON pending_deletions(media_file_id);

-- Update other indexes
DROP INDEX IF EXISTS idx_pending_deletions_file;
CREATE INDEX IF NOT EXISTS idx_pending_deletions_media ON pending_deletions(media_file_id);

COMMIT;

-- Verification queries
SELECT 'duplicate_groups count:' as check, COUNT(*) as count FROM duplicate_groups;
SELECT 'duplicate_members count:' as check, COUNT(*) as count FROM duplicate_members;
SELECT 'media_files count:' as check, COUNT(*) as count FROM media_files;
SELECT 'pending_deletions count:' as check, COUNT(*) as count FROM pending_deletions;
