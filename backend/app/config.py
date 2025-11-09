"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "MediaVault"
    app_version: str = "0.1.0"
    environment: str = "production"
    debug: bool = False

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8007
    frontend_port: int = 3007

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    allow_registration: bool = False

    # CORS
    cors_origins: str = "https://mediavault.orourkes.me,http://localhost:3007"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # NAS Configuration
    nas_host: str = "10.27.10.11"
    nas_smb_username: str = "ProxmoxBackupsSMB"
    nas_smb_password: str
    nas_smb_share: str = "volume1"
    nas_mount_path: str = "/mnt/nas-media"
    nas_scan_paths: str = "/volume1/docker,/volume1/videos"
    nas_temp_delete_path: str = "/volume1/video/duplicates_before_purge"
    local_temp_delete_path: str = "./tmp/duplicates_before_purge"
    dev_media_fallback_path: str = ""

    @property
    def nas_scan_paths_list(self) -> List[str]:
        """Parse scan paths from comma-separated string."""
        return [path.strip() for path in self.nas_scan_paths.split(",")]

    # TMDb API
    tmdb_api_key: str
    tmdb_read_access_token: str
    tmdb_base_url: str = "https://api.themoviedb.org/3/"
    tmdb_rate_limit: int = 40  # requests per 10 seconds

    # Azure OpenAI
    azure_openai_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_deployment_name_chat: str = "gpt-4o"
    azure_deployment_name_chat_mini: str = "gpt-4o-mini"
    azure_openai_max_tokens_per_day: int = 100000

    # FFmpeg / MediaInfo
    ffmpeg_path: str = "/usr/bin/ffmpeg"
    ffprobe_path: str = "/usr/bin/ffprobe"
    mediainfo_path: str = "/usr/bin/mediainfo"
    md5_chunk_size: int = 8192

    # Duplicate Detection
    fuzzy_match_threshold: int = 85
    quality_auto_approve_threshold: int = 50
    quality_manual_review_threshold: int = 20
    max_duplicates_per_batch: int = 100

    # Deletion Policy
    auto_delete_enabled: bool = False
    pending_deletion_retention_days: int = 30
    temp_delete_subdirs: str = "movies,tv,documentaries"

    @property
    def temp_delete_subdirs_list(self) -> List[str]:
        """Parse temp delete subdirs from comma-separated string."""
        return [subdir.strip() for subdir in self.temp_delete_subdirs.split(",")]

    # Language Detection
    trust_foreign_film_heuristic: bool = True
    require_english_audio: bool = True

    # Scanning
    default_scan_type: str = "full"
    scan_max_workers: int = 5
    scan_timeout: int = 3600
    video_extensions: str = ".mkv,.mp4,.avi,.m4v,.mov,.wmv,.flv,.webm,.mpg,.mpeg,.ts"

    @property
    def video_extensions_list(self) -> List[str]:
        """Parse video extensions from comma-separated string."""
        return [ext.strip() for ext in self.video_extensions.split(",")]

    # Logging
    log_level: str = "INFO"
    log_file: str = "/var/log/mediavault/mediavault.log"
    log_max_bytes: int = 10485760  # 10 MB
    log_backup_count: int = 5

    # Langfuse / TraceForge
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://10.27.10.104:3010"
    langfuse_project_id: str = ""

    @property
    def langfuse_enabled(self) -> bool:
        """Check if Langfuse is configured."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
