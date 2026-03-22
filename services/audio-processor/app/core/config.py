from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "CodeForChord Audio Processor"
    version: str = "0.1.0"
    debug: bool = False
    
    # Audio processing settings
    sample_rate: int = 22050
    onset_threshold: float = 0.5
    frame_threshold: float = 0.3
    min_note_length: float = 0.058
    
    # File handling
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: list[str] = [".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"]
    temp_dir: Path = Path("./temp")
    
    # Default output settings
    default_tempo: int = 120
    default_time_signature: str = "4/4"

    # Azure Blob Storage
    azure_storage_connection_string: str = ""
    azure_storage_account_name: str = ""
    azure_storage_account_key: str = ""
    azure_container_uploads: str = "cfc-uploads"
    azure_container_recordings: str = "cfc-recordings"
    azure_sas_expiry_minutes: int = 60
    azure_max_storage_bytes: int = 50 * 1024 * 1024 * 1024  # 50GB
    azure_audio_ttl_hours: int = 72
    azure_audio_min_retention_hours: int = 1
    azure_max_upload_size_bytes: int = 500 * 1024 * 1024  # 500MB for Azure-backed uploads
    lru_interval_seconds: int = 3600
    lru_eviction_batch_size: int = 50

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "codeforchord"

    # Auth0
    auth0_domain: str = ""
    auth0_audience: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "CFC_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
