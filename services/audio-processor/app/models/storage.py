from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError(f"Invalid ObjectId: {v}")


class AudioFileRecord(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    blob_name: str
    container_name: str
    original_filename: str
    file_size_bytes: int
    content_type: str
    upload_type: str = "upload"  # "upload" | "recording"
    session_id: Optional[str] = None
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_status: str = "pending"  # "pending" | "processing" | "done" | "error"
    processing_error: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AudioFileResponse(BaseModel):
    blob_name: str
    original_filename: str
    file_size_bytes: int
    upload_type: str
    session_id: Optional[str]
    created_at: datetime
    processing_status: str


class SheetMusicRecord(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    audio_file_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str
    format: str  # "musicxml" | "midi" | "json"
    output_type: str  # "chords_only" | "lead_sheet" | "full_score"
    instrument: str  # "piano" | "guitar" | "vocal"
    content: str  # Full MusicXML string or base64 MIDI
    content_size_bytes: int
    metadata: dict
    arrangement_options: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class SheetMusicListItem(BaseModel):
    id: str
    title: str
    format: str
    output_type: str
    instrument: str
    content_size_bytes: int
    metadata: dict
    created_at: datetime


class SessionRecord(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    session_token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    audio_file_ids: list[str] = Field(default_factory=list)
    sheet_music_ids: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class SASUrlResponse(BaseModel):
    blob_name: str
    sas_url: str
    expires_at: datetime


class EvictionResult(BaseModel):
    evicted_count: int
    bytes_freed: int
    errors: list[str] = Field(default_factory=list)
