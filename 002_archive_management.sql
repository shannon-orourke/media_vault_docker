-- Migration 002: Archive Management
-- Add support for tracking RAR archives and their extraction status

-- Create archive_files table
CREATE TABLE IF NOT EXISTS archive_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    archive_type VARCHAR(20) NOT NULL, -- 'rar', 'zip', '7z', etc.

    -- Extraction status
    extraction_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'extracted', 'failed', 'skipped'
    extracted_at TIMESTAMP,
    extraction_error TEXT,

    -- Parsed metadata (guessed from filename)
    parsed_title VARCHAR(500),
    parsed_year INTEGER,
    parsed_season INTEGER,
    parsed_episode INTEGER,
    media_type VARCHAR(50), -- 'movie', 'tv'

    -- Destination paths
    destination_path TEXT, -- Where extracted files should go
    extracted_to_path TEXT, -- Where files were actually extracted

    -- Retention tracking for seeding
    mark_for_deletion_at TIMESTAMP, -- When to delete (6 months from discovery)
    deleted_at TIMESTAMP,
    keep_for_seeding BOOLEAN DEFAULT true,

    -- Timestamps
    discovered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Indexes for searching
    CONSTRAINT check_media_type CHECK (media_type IN ('movie', 'tv', 'unknown'))
);

-- Create indexes for archive_files
CREATE INDEX IF NOT EXISTS idx_archive_files_extraction_status ON archive_files(extraction_status);
CREATE INDEX IF NOT EXISTS idx_archive_files_media_type ON archive_files(media_type);
CREATE INDEX IF NOT EXISTS idx_archive_files_mark_for_deletion ON archive_files(mark_for_deletion_at) WHERE mark_for_deletion_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_archive_files_discovered_at ON archive_files(discovered_at DESC);

-- Create archive_contents table (tracks extracted files)
CREATE TABLE IF NOT EXISTS archive_contents (
    id SERIAL PRIMARY KEY,
    archive_id INTEGER NOT NULL REFERENCES archive_files(id) ON DELETE CASCADE,

    -- File information
    filename VARCHAR(500) NOT NULL,
    relative_path TEXT, -- Path within the archive
    extracted_path TEXT, -- Full path where file was extracted
    file_size BIGINT,

    -- Link to media_files if it's a video
    media_file_id INTEGER REFERENCES media_files(id) ON DELETE SET NULL,

    -- Timestamps
    extracted_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_archive_file UNIQUE(archive_id, relative_path)
);

-- Create indexes for archive_contents
CREATE INDEX IF NOT EXISTS idx_archive_contents_archive_id ON archive_contents(archive_id);
CREATE INDEX IF NOT EXISTS idx_archive_contents_media_file_id ON archive_contents(media_file_id);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_archive_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_archive_files_updated_at
    BEFORE UPDATE ON archive_files
    FOR EACH ROW
    EXECUTE FUNCTION update_archive_updated_at();

COMMENT ON TABLE archive_files IS 'Tracks RAR/ZIP archives found on NAS for extraction and seeding management';
COMMENT ON TABLE archive_contents IS 'Tracks individual files extracted from archives';
COMMENT ON COLUMN archive_files.keep_for_seeding IS 'If true, archive will be kept for seeding torrents';
COMMENT ON COLUMN archive_files.mark_for_deletion_at IS 'Timestamp when archive should be deleted (typically 6 months after discovery)';
