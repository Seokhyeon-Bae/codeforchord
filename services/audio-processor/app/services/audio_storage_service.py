import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.storage import AudioFileRecord, AudioFileResponse
from app.services.azure_blob_service import AzureBlobService
from app.services.mongo_service import MongoService


ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
MIME_MAP = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
}


class AudioStorageService:
    def __init__(
        self,
        mongo: MongoService,
        blob: AzureBlobService,
        container_uploads: str,
        container_recordings: str,
        sas_expiry_minutes: int,
        max_upload_size_bytes: int,
    ):
        self._mongo = mongo
        self._blob = blob
        self._container_uploads = container_uploads
        self._container_recordings = container_recordings
        self._sas_expiry_minutes = sas_expiry_minutes
        self._max_upload_size_bytes = max_upload_size_bytes

    def _validate(self, filename: str, size: int):
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
        if size > self._max_upload_size_bytes:
            raise ValueError(
                f"File too large: {size / 1024 / 1024:.1f}MB. Max: {self._max_upload_size_bytes / 1024 / 1024:.0f}MB"
            )

    async def upload_audio(
        self,
        data: bytes,
        original_filename: str,
        session_id: Optional[str] = None,
        upload_type: str = "upload",
    ) -> AudioFileResponse:
        self._validate(original_filename, len(data))
        ext = Path(original_filename).suffix.lower()
        blob_name = f"{uuid.uuid4()}{ext}"
        content_type = MIME_MAP.get(ext, "audio/octet-stream")
        container = self._container_recordings if upload_type == "recording" else self._container_uploads

        await self._blob.upload_blob(container, blob_name, data, content_type)

        now = datetime.utcnow()
        doc = {
            "blob_name": blob_name,
            "container_name": container,
            "original_filename": original_filename,
            "file_size_bytes": len(data),
            "content_type": content_type,
            "upload_type": upload_type,
            "session_id": session_id,
            "last_accessed": now,
            "created_at": now,
            "processing_status": "pending",
            "processing_error": None,
        }
        audio_id = await self._mongo.insert_audio_file(doc)

        if session_id:
            await self._mongo.add_audio_to_session(session_id, audio_id)

        return AudioFileResponse(
            blob_name=blob_name,
            original_filename=original_filename,
            file_size_bytes=len(data),
            upload_type=upload_type,
            session_id=session_id,
            created_at=now,
            processing_status="pending",
        )

    async def get_sas_url(self, blob_name: str) -> tuple[str, datetime]:
        record = await self._mongo.get_audio_file_by_blob_name(blob_name)
        if not record:
            raise FileNotFoundError(f"Audio file not found: {blob_name}")
        sas_url, expires_at = self._blob.generate_sas_url(
            record["container_name"], blob_name, self._sas_expiry_minutes
        )
        await self._mongo.update_last_accessed(blob_name)
        return sas_url, expires_at

    async def download_to_temp(self, blob_name: str, temp_dir: Path) -> Path:
        record = await self._mongo.get_audio_file_by_blob_name(blob_name)
        if not record:
            raise FileNotFoundError(f"Audio file not found: {blob_name}")
        data = await self._blob.download_blob(record["container_name"], blob_name)
        await self._mongo.update_last_accessed(blob_name)
        tmp_path = temp_dir / blob_name
        tmp_path.write_bytes(data)
        return tmp_path

    async def get_info(self, blob_name: str) -> Optional[dict]:
        return await self._mongo.get_audio_file_by_blob_name(blob_name)

    async def delete(self, blob_name: str):
        record = await self._mongo.get_audio_file_by_blob_name(blob_name)
        if not record:
            raise FileNotFoundError(f"Audio file not found: {blob_name}")
        await self._blob.delete_blob(record["container_name"], blob_name)
        await self._mongo.delete_audio_file_record(blob_name)

    async def list_files(
        self, session_id: Optional[str], limit: int = 20, offset: int = 0
    ) -> list[dict]:
        return await self._mongo.list_audio_files(session_id, limit, offset)
