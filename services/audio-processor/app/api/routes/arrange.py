"""Arrangement endpoints for music transformations."""

import tempfile
import base64
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body

from app.models.note import NoteList
from app.models.chord import ChordList
from app.models.sheet import (
    OutputFormat, 
    OutputType, 
    Instrument, 
    SheetMetadata,
    ArrangementOptions,
)
from app.models.requests import TransposeRequest, ModeConvertRequest, SimplifyRequest
from app.services.pitch_detector import PitchDetector
from app.services.chord_detector import ChordDetector
from app.services.sheet_generator import SheetGenerator
from app.services.midi_generator import MidiGenerator
from app.services.arranger import Arranger
from app.services.audio_merger import AudioMerger

router = APIRouter(prefix="/arrange", tags=["arrangement"])


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return Path(filename).suffix.lower() if filename else ".wav"


@router.post("/transpose")
async def transpose(
    file: UploadFile = File(..., description="Audio file to process"),
    semitones: int = Query(..., ge=-12, le=12, description="Semitones to transpose"),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    tempo: int = Query(120, ge=20, le=300),
):
    """
    Transpose detected notes and chords by semitones.
    
    - Positive values transpose up
    - Negative values transpose down
    - Range: -12 to +12 (one octave each direction)
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        merger = AudioMerger()
        notes, chords = merger.analyze(tmp_path)
        
        arranger = Arranger()
        transposed_notes, transposed_chords = arranger.transpose(notes, chords, semitones)
        
        metadata = SheetMetadata(tempo=tempo)
        
        if output_format == OutputFormat.MUSICXML:
            generator = SheetGenerator()
            result = generator.generate(
                transposed_notes, transposed_chords, 
                OutputType.LEAD_SHEET, metadata
            )
            return {
                "musicxml": result.content,
                "notes": transposed_notes.model_dump() if transposed_notes else None,
                "chords": transposed_chords.model_dump() if transposed_chords else None,
                "transposition": semitones,
            }
        else:
            generator = MidiGenerator()
            midi_bytes = generator.generate_bytes(
                transposed_notes, transposed_chords,
                OutputType.LEAD_SHEET, metadata
            )
            return {
                "midi_base64": base64.b64encode(midi_bytes).decode("utf-8"),
                "notes": transposed_notes.model_dump() if transposed_notes else None,
                "chords": transposed_chords.model_dump() if transposed_chords else None,
                "transposition": semitones,
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transposition failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/transpose/chords")
async def transpose_chords(
    chords: ChordList = Body(..., description="Chord list to transpose"),
    semitones: int = Query(..., ge=-12, le=12),
):
    """
    Transpose a chord progression by semitones (JSON input).
    
    Useful when you already have chord data from detection.
    """
    arranger = Arranger()
    _, transposed = arranger.transpose(None, chords, semitones)
    return transposed


@router.post("/convert-mode/chords")
async def convert_mode_chords(
    chords: ChordList = Body(..., description="Chord list to convert"),
    target_mode: str = Query(..., pattern="^(major|minor)$", description="Target mode"),
):
    """
    Convert chord progression between major and minor modes (JSON input).
    
    Parallel mode conversion using music theory rules:
    - Major to Minor: C → Cm, Cmaj7 → Cm7, C7 → Cm7
    - Minor to Major: Cm → C, Cm7 → Cmaj7, Cdim → C
    
    This keeps the same root note and changes the chord quality.
    """
    arranger = Arranger()
    if target_mode == "minor":
        converted = arranger.to_minor(chords)
    else:
        converted = arranger.to_major(chords)
    return converted


@router.post("/convert-mode")
async def convert_mode(
    file: UploadFile = File(...),
    target_mode: str = Query(..., pattern="^(major|minor)$", description="Target mode"),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    tempo: int = Query(120, ge=20, le=300),
):
    """
    Convert between major and minor modes.
    
    - "minor": Convert major chords to minor
    - "major": Convert minor chords to major
    
    This is a parallel mode conversion (C -> Cm, Am -> A).
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        merger = AudioMerger()
        notes, chords = merger.analyze(tmp_path)
        
        if not chords:
            raise HTTPException(status_code=400, detail="No chords detected")
        
        arranger = Arranger()
        if target_mode == "minor":
            converted = arranger.to_minor(chords)
        else:
            converted = arranger.to_major(chords)
        
        metadata = SheetMetadata(tempo=tempo)
        
        if output_format == OutputFormat.MUSICXML:
            generator = SheetGenerator()
            result = generator.generate(notes, converted, OutputType.LEAD_SHEET, metadata)
            return {
                "musicxml": result.content,
                "chords": converted.model_dump(),
                "original_key": chords.key,
                "target_mode": target_mode,
            }
        else:
            generator = MidiGenerator()
            midi_bytes = generator.generate_bytes(notes, converted, OutputType.LEAD_SHEET, metadata)
            return {
                "midi_base64": base64.b64encode(midi_bytes).decode("utf-8"),
                "chords": converted.model_dump(),
                "target_mode": target_mode,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mode conversion failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/simplify")
async def simplify_chords(
    file: UploadFile = File(...),
    target_instrument: Instrument = Query(Instrument.GUITAR),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    tempo: int = Query(120, ge=20, le=300),
):
    """
    Simplify chords for easier playing.
    
    Converts complex chords (7ths, extensions) to simpler triads.
    For guitar, removes slash bass notes and complex voicings.
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        merger = AudioMerger()
        notes, chords = merger.analyze(tmp_path)
        
        if not chords:
            raise HTTPException(status_code=400, detail="No chords detected")
        
        arranger = Arranger()
        simplified = arranger.simplify_chords(chords, target_instrument)
        
        metadata = SheetMetadata(tempo=tempo, instrument=target_instrument)
        
        if output_format == OutputFormat.MUSICXML:
            generator = SheetGenerator()
            result = generator.generate(notes, simplified, OutputType.LEAD_SHEET, metadata)
            return {
                "musicxml": result.content,
                "original_chords": chords.model_dump(),
                "simplified_chords": simplified.model_dump(),
                "target_instrument": target_instrument.value,
            }
        else:
            generator = MidiGenerator()
            midi_bytes = generator.generate_bytes(notes, simplified, OutputType.LEAD_SHEET, metadata)
            return {
                "midi_base64": base64.b64encode(midi_bytes).decode("utf-8"),
                "simplified_chords": simplified.model_dump(),
                "target_instrument": target_instrument.value,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simplification failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/jazzify")
async def jazzify_chords(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    tempo: int = Query(120, ge=20, le=300),
):
    """
    Add jazz extensions to simple chords.
    
    Converts basic triads to seventh chords:
    - C -> Cmaj7
    - Am -> Am7
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        merger = AudioMerger()
        notes, chords = merger.analyze(tmp_path)
        
        if not chords:
            raise HTTPException(status_code=400, detail="No chords detected")
        
        arranger = Arranger()
        jazzified = arranger.jazzify_chords(chords)
        
        metadata = SheetMetadata(tempo=tempo)
        
        if output_format == OutputFormat.MUSICXML:
            generator = SheetGenerator()
            result = generator.generate(notes, jazzified, OutputType.LEAD_SHEET, metadata)
            return {
                "musicxml": result.content,
                "original_chords": chords.model_dump(),
                "jazzified_chords": jazzified.model_dump(),
            }
        else:
            generator = MidiGenerator()
            midi_bytes = generator.generate_bytes(notes, jazzified, OutputType.LEAD_SHEET, metadata)
            return {
                "midi_base64": base64.b64encode(midi_bytes).decode("utf-8"),
                "jazzified_chords": jazzified.model_dump(),
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jazzification failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/full")
async def full_arrangement(
    file: UploadFile = File(...),
    transpose_semitones: int = Query(0, ge=-12, le=12),
    convert_to_minor: bool = Query(False),
    convert_to_major: bool = Query(False),
    simplify: bool = Query(False),
    target_instrument: Instrument = Query(Instrument.PIANO),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    tempo: int = Query(120, ge=20, le=300),
):
    """
    Apply multiple arrangement transformations at once.
    
    Transformations are applied in order:
    1. Transpose
    2. Mode conversion
    3. Simplification
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        merger = AudioMerger()
        notes, chords = merger.analyze(tmp_path)
        
        options = ArrangementOptions(
            transpose_semitones=transpose_semitones,
            convert_to_minor=convert_to_minor,
            convert_to_major=convert_to_major,
            simplify_chords=simplify,
            target_instrument=target_instrument if simplify else None,
        )
        
        arranger = Arranger()
        arranged_notes, arranged_chords = arranger.arrange(notes, chords, options)
        
        metadata = SheetMetadata(tempo=tempo, instrument=target_instrument)
        
        if output_format == OutputFormat.MUSICXML:
            generator = SheetGenerator()
            result = generator.generate(
                arranged_notes, arranged_chords,
                OutputType.LEAD_SHEET, metadata
            )
            return {
                "musicxml": result.content,
                "notes": arranged_notes.model_dump() if arranged_notes else None,
                "chords": arranged_chords.model_dump() if arranged_chords else None,
                "transformations_applied": {
                    "transpose": transpose_semitones,
                    "to_minor": convert_to_minor,
                    "to_major": convert_to_major,
                    "simplified": simplify,
                },
            }
        else:
            generator = MidiGenerator()
            midi_bytes = generator.generate_bytes(
                arranged_notes, arranged_chords,
                OutputType.LEAD_SHEET, metadata
            )
            return {
                "midi_base64": base64.b64encode(midi_bytes).decode("utf-8"),
                "chords": arranged_chords.model_dump() if arranged_chords else None,
                "transformations_applied": {
                    "transpose": transpose_semitones,
                    "to_minor": convert_to_minor,
                    "to_major": convert_to_major,
                    "simplified": simplify,
                },
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arrangement failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/health")
async def health():
    """Check arrangement service health."""
    return {"status": "healthy", "service": "arrangement"}
