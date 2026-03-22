"""Sheet music endpoints — generate, save, retrieve from MongoDB."""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.core.auth import get_optional_user
from app.models.sheet import (
    GeneratedSheet,
    Instrument,
    OutputFormat,
    OutputType,
    SheetMetadata,
)
from app.models.storage import SheetMusicListItem
from app.services.audio_merger import AudioMerger
from app.services.midi_generator import MidiGenerator
from app.services.sheet_generator import SheetGenerator

router = APIRouter(prefix="/sheets", tags=["sheets"])


def get_mongo():
    from app.main import app
    mongo = getattr(app.state, "mongo", None)
    if mongo is None:
        raise HTTPException(status_code=503, detail="Database service not available")
    return mongo


def get_audio_storage():
    from app.main import app
    storage = getattr(app.state, "audio_storage", None)
    if storage is None:
        raise HTTPException(status_code=503, detail="Storage service not available")
    return storage


def get_settings():
    from app.core.config import get_settings as _get_settings
    return _get_settings()


@router.post("/generate-and-save", summary="Generate sheet music and save to MongoDB")
async def generate_and_save(
    file: Optional[UploadFile] = File(None),
    blob_name: Optional[str] = Query(None, description="Existing blob_name from /audio/upload"),
    session_id: Optional[str] = Query(None),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    output_type: OutputType = Query(OutputType.LEAD_SHEET),
    title: str = Query("Untitled"),
    tempo: int = Query(120, ge=20, le=300),
    time_signature: str = Query("4/4"),
    instrument: Instrument = Query(Instrument.PIANO),
    correction_strength: float = Query(0.5, ge=0.0, le=1.0),
    mongo=Depends(get_mongo),
    audio_storage=Depends(get_audio_storage),
    user: Optional[dict] = Depends(get_optional_user),
):
    """
    Upload or reference an existing audio file, run the full generation pipeline,
    and save the result in MongoDB. Returns GeneratedSheet + sheet_id.
    """
    effective_session = session_id or (user.get("sub") if user else None)
    settings = get_settings()
    tmp_path: Optional[Path] = None
    audio_file_id: Optional[str] = None

    try:
        if blob_name:
            # Fetch from Azure
            record = await audio_storage.get_info(blob_name)
            if not record:
                raise HTTPException(status_code=404, detail=f"Audio not found: {blob_name}")
            audio_file_id = str(record.get("_id", ""))
            tmp_path = await audio_storage.download_to_temp(blob_name, Path(settings.temp_dir))
        elif file is not None:
            # Direct upload (stateless fallback — not saved to Azure)
            ext = Path(file.filename or "audio").suffix.lower() or ".wav"
            content = await file.read()
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
        else:
            raise HTTPException(status_code=400, detail="Provide either 'file' or 'blob_name'")

        # Run existing pipeline (unchanged)
        merger = AudioMerger()
        notes, chords = merger.analyze(tmp_path)
        if notes:
            notes = merger.filter_by_instrument(notes, instrument.value)

        metadata = SheetMetadata(
            title=title,
            tempo=tempo,
            time_signature=time_signature,
            instrument=instrument,
            key_signature=chords.key if chords else None,
        )

        if output_format == OutputFormat.MUSICXML:
            result: GeneratedSheet = SheetGenerator().generate(
                notes=notes,
                chords=chords,
                output_type=output_type,
                metadata=metadata,
                correction_strength=correction_strength,
            )
        else:
            result = MidiGenerator().generate(
                notes=notes,
                chords=chords,
                output_type=output_type,
                metadata=metadata,
            )

        # Persist to MongoDB
        now = datetime.utcnow()
        content_bytes = result.content.encode() if isinstance(result.content, str) else result.content
        doc = {
            "audio_file_id": audio_file_id,
            "session_id": effective_session,
            "title": title,
            "format": output_format.value,
            "output_type": output_type.value,
            "instrument": instrument.value,
            "content": result.content,
            "content_size_bytes": len(content_bytes),
            "metadata": {
                "title": title,
                "tempo": tempo,
                "time_signature": time_signature,
                "instrument": instrument.value,
                "key_signature": chords.key if chords else None,
            },
            "arrangement_options": None,
            "created_at": now,
            "last_accessed": now,
        }
        sheet_id = await mongo.insert_sheet_music(doc)

        if effective_session:
            await mongo.add_sheet_to_session(effective_session, sheet_id)

        return {**result.model_dump(), "sheet_id": sheet_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.get("/list", summary="List saved sheet music")
async def list_sheets(
    session_id: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mongo=Depends(get_mongo),
):
    docs = await mongo.list_sheets(session_id=session_id, fmt=format, limit=limit, offset=offset)
    items = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"sheets": items, "limit": limit, "offset": offset}


@router.get("/{sheet_id}", summary="Get saved sheet music (with content)")
async def get_sheet(sheet_id: str, mongo=Depends(get_mongo)):
    doc = await mongo.get_sheet_by_id(sheet_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Sheet not found: {sheet_id}")
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/{sheet_id}/download", summary="Download sheet music file")
async def download_sheet(sheet_id: str, mongo=Depends(get_mongo)):
    doc = await mongo.get_sheet_by_id(sheet_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Sheet not found: {sheet_id}")

    fmt = doc.get("format", "musicxml")
    title = doc.get("title", "sheet").replace(" ", "_").lower()
    content = doc["content"]

    if fmt == "musicxml":
        return Response(
            content=content.encode("utf-8") if isinstance(content, str) else content,
            media_type="application/vnd.recordare.musicxml+xml",
            headers={"Content-Disposition": f'attachment; filename="{title}.musicxml"'},
        )
    else:
        import base64
        raw = base64.b64decode(content) if isinstance(content, str) else content
        return Response(
            content=raw,
            media_type="audio/midi",
            headers={"Content-Disposition": f'attachment; filename="{title}.mid"'},
        )


@router.delete("/{sheet_id}", summary="Delete sheet music from MongoDB")
async def delete_sheet(sheet_id: str, mongo=Depends(get_mongo)):
    deleted = await mongo.delete_sheet(sheet_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Sheet not found: {sheet_id}")
    return {"deleted": True, "sheet_id": sheet_id}
