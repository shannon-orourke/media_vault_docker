-- Migration: Add TMDb type, year, and IMDB ID fields to media_files table
-- Date: 2025-11-10

-- Add new TMDb/IMDB columns
ALTER TABLE media_files
ADD COLUMN IF NOT EXISTS tmdb_type VARCHAR(20),
ADD COLUMN IF NOT EXISTS tmdb_year INTEGER,
ADD COLUMN IF NOT EXISTS imdb_id VARCHAR(20);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_media_files_imdb_id ON media_files(imdb_id);
CREATE INDEX IF NOT EXISTS idx_media_files_tmdb_type ON media_files(tmdb_type);

-- Verify columns exist
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'media_files'
AND column_name IN ('tmdb_type', 'tmdb_year', 'imdb_id')
ORDER BY column_name;
