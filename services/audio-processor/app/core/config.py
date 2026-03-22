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
    
    class Config:
        env_file = ".env"
        env_prefix = "CFC_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
