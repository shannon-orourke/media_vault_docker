-- Migration 003: Fix schema mismatches between database and SQLAlchemy models
-- Date: 2025-11-09
-- Fixes column name mismatches and adds missing columns

-- ============================================================================
-- FIX 1: archive_operations table - rename file_id to media_file_id
-- ============================================================================
ALTER TABLE archive_operations
RENAME COLUMN file_id TO media_file_id;

-- ============================================================================
-- FIX 2: archive_operations table - add missing columns from SQLAlchemy model
-- ============================================================================
ALTER TABLE archive_operations
ADD COLUMN IF NOT EXISTS file_size BIGINT,
ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS performed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS performed_by_user_id INTEGER,
ADD COLUMN IF NOT EXISTS operation_metadata JSON;

-- Create index on performed_at for better query performance
CREATE INDEX IF NOT EXISTS idx_archive_operations_performed_at ON archive_operations(performed_at);

-- ============================================================================
-- FIX 3: pending_deletions table - remove duplicate file_id column
-- ============================================================================
-- The table had both file_id (NOT NULL) and media_file_id (nullable)
-- Remove file_id since SQLAlchemy model only uses media_file_id
ALTER TABLE pending_deletions
DROP COLUMN IF EXISTS file_id CASCADE;

-- ============================================================================
-- FIX 4: pending_deletions table - make temp_filepath nullable
-- ============================================================================
-- When source file is missing, we can't move it to temp, so temp_filepath should be nullable
ALTER TABLE pending_deletions
ALTER COLUMN temp_filepath DROP NOT NULL,
ALTER COLUMN deletion_reason DROP NOT NULL;

-- ============================================================================
-- RESULT: All schema issues resolved
-- ============================================================================
-- archive_operations: Uses media_file_id, has all required columns
-- pending_deletions: No duplicate columns, temp_filepath nullable for missing files
