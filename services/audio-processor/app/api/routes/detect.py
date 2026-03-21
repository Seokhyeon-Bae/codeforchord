"""Detection endpoints for notes and chords."""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from app.models.note import NoteList
from app.models.chord import ChordList
from app.models.sheet import Instrument
from app.models.requests import DetectionRequest
from app.services.pitch_detector import PitchDetector
from app.services.chord_detector import ChordDetector
from app.services.audio_merger import AudioMerger
from app.core.config import get_settings

router = APIRouter(prefix="/detect", tags=["detection"])


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return Path(filename).suffix.lower() if filename else ".wav"


def validate_file_extension(filename: str) -> None:
    """Validate audio file extension."""
    settings = get_settings()
    ext = get_file_extension(filename)
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Allowed: {settings.allowed_extensions}"
        )


@router.post("/notes", response_model=NoteList)
async def detect_notes(
    file: UploadFile = File(..., description="Audio file to analyze"),
    onset_threshold: float = Query(0.5, ge=0.1, le=0.9, description="Note onset sensitivity"),
    frame_threshold: float = Query(0.3, ge=0.1, le=0.9, description="Frame threshold"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum note confidence"),
):
    """
    Detect notes/pitches from uploaded audio.
    
    Uses Spotify's Basic Pitch model for polyphonic pitch detection.
    Returns a list of detected notes with timing and pitch information.
    """
    validate_file_extension(file.filename)
    
    # Save uploaded file temporarily
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        detector = PitchDetector(
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
        )
        notes = detector.detect(tmp_path)
        
        if min_confidence > 0:
            notes = notes.filter_by_confidence(min_confidence)
        
        return notes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/chords", response_model=ChordList)
async def detect_chords(
    file: UploadFile = File(..., description="Audio file to analyze"),
):
    """
    Detect chords from uploaded audio.
    
    Uses Chordino algorithm for chord recognition.
    Returns a list of detected chords with timing information.
    """
    validate_file_extension(file.filename)
    
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        detector = ChordDetector()
        chords = detector.detect(tmp_path)
        return chords
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chord detection failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/full")
async def detect_all(
    file: UploadFile = File(..., description="Audio file to analyze"),
    instrument: Instrument = Query(Instrument.PIANO, description="Source instrument"),
    onset_threshold: float = Query(0.5, ge=0.1, le=0.9),
    frame_threshold: float = Query(0.3, ge=0.1, le=0.9),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
):
    """
    Run full audio analysis: notes AND chords.
    
    Returns both detected notes and chords in a single response.
    Optionally filters by instrument range.
    """
    validate_file_extension(file.filename)
    
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        pitch_detector = PitchDetector(
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
        )
        merger = AudioMerger(pitch_detector=pitch_detector)
        
        notes, chords = merger.analyze(
            tmp_path,
            min_note_confidence=min_confidence,
        )
        
        # Filter by instrument range
        if notes and instrument:
            notes = merger.filter_by_instrument(notes, instrument.value)
        
        return {
            "notes": notes.model_dump() if notes else None,
            "chords": chords.model_dump() if chords else None,
            "instrument": instrument.value,
            "source_file": file.filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/health")
async def health():
    """Check detection service health."""
    return {"status": "healthy", "service": "detection"}
