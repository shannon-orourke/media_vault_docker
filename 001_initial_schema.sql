-- MediaVault Database Schema Migration
-- Version: 001
-- Created: 2025-11-08
-- Database: mediavault (PostgreSQL 16)

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- 1. Users (Authentication)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    must_change_password BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- 2. Sessions (JWT Tracking)
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    jti VARCHAR(255) UNIQUE NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_jti ON sessions(jti);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- 3. NAS Configuration
CREATE TABLE nas_config (
    id SERIAL PRIMARY KEY,
    nas_name VARCHAR(100) NOT NULL,
    nas_host VARCHAR(255) NOT NULL,
    nas_type VARCHAR(50) DEFAULT 'smb',
    smb_username VARCHAR(100),
    smb_password_encrypted TEXT,
    smb_domain VARCHAR(100),
    smb_share VARCHAR(100),
    mount_path VARCHAR(255),
    mount_options TEXT,
    scan_paths TEXT[],
    is_active BOOLEAN DEFAULT true,
    last_connected_at TIMESTAMP,
    last_connection_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. Duplicate Groups
CREATE TABLE duplicate_groups (
    id SERIAL PRIMARY KEY,
    group_hash VARCHAR(128) NOT NULL UNIQUE,
    duplicate_type VARCHAR(20) NOT NULL,
    confidence DECIMAL(5,2),
    title VARCHAR(255),
    year INTEGER,
    season INTEGER,
    episode INTEGER,
    media_type VARCHAR(20),
    member_count INTEGER DEFAULT 0,
    recommended_action VARCHAR(20),
    action_reason TEXT,
    reviewed BOOLEAN DEFAULT false,
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER,
    detected_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_duplicate_groups_reviewed ON duplicate_groups(reviewed);
CREATE INDEX idx_duplicate_groups_type ON duplicate_groups(duplicate_type);
CREATE INDEX idx_duplicate_groups_hash ON duplicate_groups(group_hash);

-- 5. Media Files (Core Inventory)
CREATE TABLE media_files (
    id SERIAL PRIMARY KEY,

    -- File identification
    filename VARCHAR(500) NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    file_size BIGINT NOT NULL,
    md5_hash CHAR(32),

    -- Media metadata
    duration DECIMAL(10,2),
    format VARCHAR(50),
    video_codec VARCHAR(50),
    audio_codec VARCHAR(50),
    resolution VARCHAR(20),
    width INTEGER,
    height INTEGER,
    bitrate INTEGER,
    framerate DECIMAL(6,2),

    -- Quality indicators
    quality_tier VARCHAR(20),
    hdr_type VARCHAR(20),
    audio_channels DECIMAL(3,1),
    audio_track_count INTEGER DEFAULT 1,
    subtitle_track_count INTEGER DEFAULT 0,

    -- Language tracking
    audio_languages TEXT[],
    subtitle_languages TEXT[],
    dominant_audio_language VARCHAR(10),

    -- Parsed metadata (guessit)
    parsed_title VARCHAR(500),
    parsed_year INTEGER,
    parsed_season INTEGER,
    parsed_episode INTEGER,
    parsed_release_group VARCHAR(100),
    media_type VARCHAR(50),

    -- TMDb metadata
    tmdb_id INTEGER,
    tmdb_title VARCHAR(500),
    tmdb_overview TEXT,
    tmdb_poster_path VARCHAR(500),
    tmdb_rating DECIMAL(3,1),
    tmdb_genres JSONB,
    tmdb_last_updated TIMESTAMP,

    -- Quality score
    quality_score INTEGER,

    -- Status
    is_duplicate BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    archived_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,

    -- Timestamps
    discovered_at TIMESTAMP DEFAULT NOW(),
    last_scanned_at TIMESTAMP DEFAULT NOW(),
    metadata_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_media_files_filepath ON media_files(filepath);
CREATE INDEX idx_media_files_md5 ON media_files(md5_hash) WHERE md5_hash IS NOT NULL;
CREATE INDEX idx_media_parsed_movie ON media_files(parsed_title, parsed_year);
CREATE INDEX idx_media_parsed_tv ON media_files(parsed_title, parsed_season, parsed_episode);
CREATE INDEX idx_media_type_quality ON media_files(media_type, quality_score);
CREATE INDEX idx_media_files_duplicate ON media_files(is_duplicate);

-- 6. Duplicate Members (Many-to-Many)
CREATE TABLE duplicate_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    rank INTEGER,
    recommended_action VARCHAR(20),
    action_reason TEXT,
    quality_score DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_group FOREIGN KEY (group_id)
        REFERENCES duplicate_groups(id) ON DELETE CASCADE,
    CONSTRAINT fk_file FOREIGN KEY (file_id)
        REFERENCES media_files(id) ON DELETE CASCADE,
    CONSTRAINT unique_group_file UNIQUE (group_id, file_id)
);

CREATE INDEX idx_duplicate_members_group ON duplicate_members(group_id);
CREATE INDEX idx_duplicate_members_file ON duplicate_members(file_id);

-- 7. Pending Deletions (Temp Staging Area)
CREATE TABLE pending_deletions (
    id SERIAL PRIMARY KEY,
    media_file_id INTEGER NOT NULL UNIQUE,
    original_filepath TEXT NOT NULL,
    temp_filepath TEXT,
    file_size BIGINT NOT NULL,
    reason TEXT NOT NULL,
    duplicate_group_id INTEGER,
    better_quality_file_id INTEGER,
    quality_score_diff INTEGER,
    language_concern BOOLEAN DEFAULT false,
    language_concern_reason TEXT,
    staged_at TIMESTAMP DEFAULT NOW(),
    approved_for_deletion BOOLEAN DEFAULT false,
    approved_at TIMESTAMP,
    approved_by_user_id INTEGER,
    deleted_at TIMESTAMP,
    deletion_metadata JSONB,

    CONSTRAINT fk_pending_media FOREIGN KEY (media_file_id)
        REFERENCES media_files(id) ON DELETE CASCADE,
    CONSTRAINT fk_pending_better FOREIGN KEY (better_quality_file_id)
        REFERENCES media_files(id) ON DELETE SET NULL,
    CONSTRAINT fk_pending_group FOREIGN KEY (duplicate_group_id)
        REFERENCES duplicate_groups(id) ON DELETE SET NULL,
    CONSTRAINT fk_pending_user FOREIGN KEY (approved_by_user_id)
        REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_pending_deletions_media ON pending_deletions(media_file_id);
CREATE INDEX idx_pending_deletions_group ON pending_deletions(duplicate_group_id);
CREATE INDEX idx_pending_deletions_action ON pending_deletions(final_action);
CREATE INDEX idx_pending_deletions_scheduled ON pending_deletions(scheduled_deletion_at);
CREATE INDEX idx_pending_deletions_requires_review ON pending_deletions(requires_manual_review);

-- 8. Scan History
CREATE TABLE scan_history (
    id SERIAL PRIMARY KEY,
    scan_type VARCHAR(20),
    nas_paths TEXT[],
    scan_started_at TIMESTAMP NOT NULL,
    scan_completed_at TIMESTAMP,
    duration_seconds INTEGER,
    files_found INTEGER DEFAULT 0,
    files_new INTEGER DEFAULT 0,
    files_updated INTEGER DEFAULT 0,
    files_deleted INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details JSONB,
    status VARCHAR(20) DEFAULT 'running',
    triggered_by VARCHAR(50),
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_scan_history_status ON scan_history(status);
CREATE INDEX idx_scan_history_started ON scan_history(scan_started_at DESC);

-- 9. User Decisions
CREATE TABLE user_decisions (
    id SERIAL PRIMARY KEY,
    duplicate_group_id INTEGER NOT NULL,
    user_id INTEGER,
    action_taken VARCHAR(50),
    files_archived INTEGER[],
    files_deleted INTEGER[],
    primary_file_id INTEGER,
    notes TEXT,
    confidence VARCHAR(20),
    decided_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_duplicate_group_decision FOREIGN KEY (duplicate_group_id)
        REFERENCES duplicate_groups(id) ON DELETE CASCADE
);

CREATE INDEX idx_user_decisions_group ON user_decisions(duplicate_group_id);

-- 10. Archive Operations
CREATE TABLE archive_operations (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL,
    duplicate_group_id INTEGER,
    operation_type VARCHAR(20),
    source_path TEXT NOT NULL,
    destination_path TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    is_reversed BOOLEAN DEFAULT false,
    reversed_at TIMESTAMP,
    reversed_by INTEGER,
    triggered_by INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_file_archive FOREIGN KEY (file_id)
        REFERENCES media_files(id) ON DELETE CASCADE
);

CREATE INDEX idx_archive_operations_file ON archive_operations(file_id);
CREATE INDEX idx_archive_operations_status ON archive_operations(status);

-- ============================================================================
-- CHAT WITH YOUR DATA TABLES
-- ============================================================================

-- 11. Chat Sessions
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    context_type VARCHAR(50),
    model VARCHAR(50) DEFAULT 'gpt-4o',
    total_tokens_used INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_chat_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_last_message ON chat_sessions(last_message_at DESC);

-- 12. Chat Messages
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    context_data JSONB,
    context_query TEXT,
    model VARCHAR(50),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    finish_reason VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_chat_session FOREIGN KEY (session_id)
        REFERENCES chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at);

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default NAS config
INSERT INTO nas_config (
    nas_name,
    nas_host,
    nas_type,
    smb_username,
    smb_share,
    scan_paths,
    is_active
) VALUES (
    'Synology NAS',
    '10.27.10.11',
    'smb',
    'ProxmoxBackupsSMB',
    'volume1',
    ARRAY['/volume1/docker', '/volume1/videos'],
    true
);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE media_files IS 'Core inventory of all media files on NAS';
COMMENT ON TABLE duplicate_groups IS 'Groups of duplicate files with confidence scores';
COMMENT ON TABLE pending_deletions IS 'Staging area for files before permanent deletion (MANUAL APPROVAL ONLY)';
COMMENT ON TABLE chat_sessions IS 'Azure OpenAI chat sessions for "chat with your data" feature';
COMMENT ON TABLE chat_messages IS 'Individual messages in chat sessions with context injection';

COMMENT ON COLUMN media_files.md5_hash IS 'Content hash for exact duplicate detection';
COMMENT ON COLUMN media_files.quality_tier IS '4K, 1080p, 720p, 480p, SD';
COMMENT ON COLUMN media_files.has_english_audio IS 'Critical for deletion decisions';
COMMENT ON COLUMN media_files.is_foreign_film IS 'Heuristic: non-English audio + English subs';

COMMENT ON COLUMN pending_deletions.deletion_reason IS 'Human-readable explanation (e.g., "Kept 4K version, deleted 1080p")';
COMMENT ON COLUMN pending_deletions.temp_filepath IS 'Path in /volume1/video/duplicates_before_purge/{media_type}/{date}/';
COMMENT ON COLUMN pending_deletions.requires_manual_review IS 'Flag uncertain decisions (e.g., quality diff < 20 points)';
COMMENT ON COLUMN pending_deletions.final_action IS 'MANUAL APPROVAL ONLY - no auto-deletion';

-- ============================================================================
-- GRANT PERMISSIONS (if needed)
-- ============================================================================

-- Grant all permissions to pm_ideas_user (database owner)
-- No additional grants needed as owner has full access

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
