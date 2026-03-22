from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.auth import get_optional_user
from app.models.storage import AudioFileResponse, SASUrlResponse

router = APIRouter(prefix="/audio", tags=["audio"])


def get_audio_storage():
    from app.main import app
    storage = getattr(app.state, "audio_storage", None)
    if storage is None:
        raise HTTPException(status_code=503, detail="Storage service not available")
    return storage


@router.post("/upload", response_model=AudioFileResponse, summary="Upload audio file to Azure")
async def upload_audio(
    file: UploadFile = File(...),
    session_id: str | None = Query(None),
    storage=Depends(get_audio_storage),
    user: Optional[dict] = Depends(get_optional_user),
):
    effective_session = session_id or (user.get("sub") if user else None)
    data = await file.read()
    try:
        record = await storage.upload_audio(
            data=data,
            original_filename=file.filename or "audio",
            session_id=effective_session,
            upload_type="upload",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return record


@router.post("/recording", response_model=AudioFileResponse, summary="Save live recording to Azure")
async def upload_recording(
    file: UploadFile = File(...),
    session_id: str | None = Query(None),
    storage=Depends(get_audio_storage),
    user: Optional[dict] = Depends(get_optional_user),
):
    effective_session = session_id or (user.get("sub") if user else None)
    data = await file.read()
    try:
        record = await storage.upload_audio(
            data=data,
            original_filename=file.filename or "recording",
            session_id=effective_session,
            upload_type="recording",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return record


@router.get("/{blob_name}/url", response_model=SASUrlResponse, summary="Get temporary SAS URL")
async def get_sas_url(
    blob_name: str,
    storage=Depends(get_audio_storage),
):
    try:
        sas_url, expires_at = await storage.get_sas_url(blob_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Audio file not found: {blob_name}")
    return SASUrlResponse(blob_name=blob_name, sas_url=sas_url, expires_at=expires_at)


@router.get("/{blob_name}/info", summary="Get audio file metadata")
async def get_audio_info(
    blob_name: str,
    storage=Depends(get_audio_storage),
):
    record = await storage.get_info(blob_name)
    if not record:
        raise HTTPException(status_code=404, detail=f"Audio file not found: {blob_name}")
    record.pop("_id", None)
    return record


@router.delete("/{blob_name}", summary="Delete audio file from Azure and MongoDB")
async def delete_audio(
    blob_name: str,
    storage=Depends(get_audio_storage),
):
    try:
        await storage.delete(blob_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Audio file not found: {blob_name}")
    return {"deleted": True, "blob_name": blob_name}


@router.get("/list", summary="List audio files")
async def list_audio(
    session_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    storage=Depends(get_audio_storage),
):
    files = await storage.list_files(session_id=session_id, limit=limit, offset=offset)
    for f in files:
        f.pop("_id", None)
    return {"files": files, "limit": limit, "offset": offset}


@router.get("/health", summary="Storage health check")
async def storage_health():
    from app.main import app
    mongo_ok = hasattr(app.state, "mongo") and app.state.mongo is not None
    blob_ok = hasattr(app.state, "blob") and app.state.blob is not None
    return {
        "mongodb": "ok" if mongo_ok else "unavailable",
        "azure_blob": "ok" if blob_ok else "unavailable",
    }
