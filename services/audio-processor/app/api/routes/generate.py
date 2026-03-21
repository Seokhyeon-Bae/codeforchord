"""Generation endpoints for sheet music and MIDI."""

import tempfile
import base64
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import Response

from app.models.note import NoteList
from app.models.chord import ChordList
from app.models.sheet import (
    OutputFormat, 
    OutputType, 
    Instrument, 
    SheetMetadata, 
    GeneratedSheet,
    MelodyStyle,
)
from app.models.requests import GenerateSheetRequest, MelodyRequest
from app.services.pitch_detector import PitchDetector
from app.services.chord_detector import ChordDetector
from app.services.sheet_generator import SheetGenerator
from app.services.midi_generator import MidiGenerator
from app.services.melody_suggester import MelodySuggester
from app.services.audio_merger import AudioMerger

router = APIRouter(prefix="/generate", tags=["generation"])


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return Path(filename).suffix.lower() if filename else ".wav"


@router.post("/sheet", response_model=GeneratedSheet)
async def generate_sheet(
    file: UploadFile = File(..., description="Audio file to process"),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    output_type: OutputType = Query(OutputType.LEAD_SHEET),
    title: str = Query("Untitled", description="Song title"),
    tempo: int = Query(120, ge=20, le=300, description="Tempo in BPM"),
    time_signature: str = Query("4/4", description="Time signature"),
    instrument: Instrument = Query(Instrument.PIANO),
):
    """
    Generate sheet music from uploaded audio.
    
    Analyzes the audio to detect notes and chords, then generates
    sheet music in the requested format.
    
    Output types:
    - chords_only: Just chord symbols
    - lead_sheet: Melody with chord symbols
    - full_score: Complete arrangement with accompaniment
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        # Analyze audio
        merger = AudioMerger()
        notes, chords = merger.analyze(tmp_path)
        
        # Filter notes by instrument
        if notes:
            notes = merger.filter_by_instrument(notes, instrument.value)
        
        # Create metadata
        metadata = SheetMetadata(
            title=title,
            tempo=tempo,
            time_signature=time_signature,
            instrument=instrument,
            key_signature=chords.key if chords else None,
        )
        
        # Generate output
        if output_format == OutputFormat.MUSICXML:
            generator = SheetGenerator()
            result = generator.generate(
                notes=notes,
                chords=chords,
                output_type=output_type,
                metadata=metadata,
            )
        else:  # MIDI
            generator = MidiGenerator()
            result = generator.generate(
                notes=notes,
                chords=chords,
                output_type=output_type,
                metadata=metadata,
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/sheet/download")
async def download_sheet(
    file: UploadFile = File(...),
    output_format: OutputFormat = Query(OutputFormat.MUSICXML),
    output_type: OutputType = Query(OutputType.LEAD_SHEET),
    title: str = Query("Untitled"),
    tempo: int = Query(120, ge=20, le=300),
    time_signature: str = Query("4/4"),
    instrument: Instrument = Query(Instrument.PIANO),
):
    """
    Generate and download sheet music file.
    
    Returns the file directly for download instead of JSON response.
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
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
            generator = SheetGenerator()
            result = generator.generate(notes, chords, output_type, metadata)
            
            return Response(
                content=result.content.encode("utf-8"),
                media_type="application/vnd.recordare.musicxml+xml",
                headers={
                    "Content-Disposition": f'attachment; filename="{result.filename}.musicxml"'
                }
            )
        else:  # MIDI
            generator = MidiGenerator()
            midi_bytes = generator.generate_bytes(notes, chords, output_type, metadata)
            
            filename = title.replace(" ", "_").lower()
            return Response(
                content=midi_bytes,
                media_type="audio/midi",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.mid"'
                }
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/melody")
async def generate_melody(
    file: UploadFile = File(..., description="Audio file with chord progression"),
    style: MelodyStyle = Query(MelodyStyle.SIMPLE),
    octave: int = Query(4, ge=2, le=6, description="Base octave for melody"),
    density: float = Query(1.0, ge=0.25, le=2.0, description="Note density"),
    include_passing_tones: bool = Query(True),
    include_neighbor_tones: bool = Query(True),
    output_format: OutputFormat = Query(OutputFormat.MIDI),
    tempo: int = Query(120, ge=20, le=300),
):
    """
    Generate a melody suggestion based on detected chords.
    
    Uses rule-based algorithms to create melodies from chord tones,
    passing tones, and neighbor tones.
    
    Styles:
    - simple: Basic chord tone melody
    - arpeggiated: Broken chord patterns
    - scalar: Scale-based motion
    - rhythmic: Syncopated patterns
    """
    ext = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        # Detect chords
        chord_detector = ChordDetector()
        chords = chord_detector.detect(tmp_path)
        
        if not chords.chords:
            raise HTTPException(status_code=400, detail="No chords detected in audio")
        
        # Generate melody
        from app.models.sheet import MelodyOptions
        options = MelodyOptions(
            style=style,
            octave=octave,
            density=density,
            include_passing_tones=include_passing_tones,
            include_neighbor_tones=include_neighbor_tones,
        )
        
        suggester = MelodySuggester()
        melody = suggester.suggest(chords, options, tempo)
        
        # Return based on format
        if output_format == OutputFormat.MIDI:
            midi_gen = MidiGenerator()
            midi_bytes = midi_gen.notes_to_midi(melody.notes, tempo)
            midi_base64 = base64.b64encode(midi_bytes).decode("utf-8")
            
            return {
                "melody": melody.model_dump(),
                "midi_base64": midi_base64,
                "chords": chords.model_dump(),
                "tempo": tempo,
            }
        else:
            return {
                "melody": melody.model_dump(),
                "chords": chords.model_dump(),
                "tempo": tempo,
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Melody generation failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/melody/from-chords")
async def generate_melody_from_chords(
    chords: ChordList,
    style: MelodyStyle = Query(MelodyStyle.SIMPLE),
    octave: int = Query(4, ge=2, le=6),
    density: float = Query(1.0, ge=0.25, le=2.0),
    include_passing_tones: bool = Query(True),
    include_neighbor_tones: bool = Query(True),
    tempo: int = Query(120, ge=20, le=300),
):
    """
    Generate melody from a provided chord progression (JSON).
    
    Useful when you already have chord data and just need melody suggestions.
    """
    if not chords.chords:
        raise HTTPException(status_code=400, detail="No chords provided")
    
    try:
        from app.models.sheet import MelodyOptions
        options = MelodyOptions(
            style=style,
            octave=octave,
            density=density,
            include_passing_tones=include_passing_tones,
            include_neighbor_tones=include_neighbor_tones,
        )
        
        suggester = MelodySuggester()
        melody = suggester.suggest(chords, options, tempo)
        
        midi_gen = MidiGenerator()
        midi_bytes = midi_gen.notes_to_midi(melody.notes, tempo)
        midi_base64 = base64.b64encode(midi_bytes).decode("utf-8")
        
        return {
            "melody": melody.model_dump(),
            "midi_base64": midi_base64,
            "tempo": tempo,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Melody generation failed: {str(e)}")


@router.get("/health")
async def health():
    """Check generation service health."""
    return {"status": "healthy", "service": "generation"}
