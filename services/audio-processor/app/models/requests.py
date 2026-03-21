from pydantic import BaseModel, Field
from typing import Optional
from .sheet import OutputFormat, OutputType, Instrument, ArrangementOptions, MelodyOptions, MelodyStyle


class DetectionRequest(BaseModel):
    """Request parameters for audio detection."""
    
    instrument: Instrument = Field(default=Instrument.PIANO, description="Source instrument type")
    onset_threshold: float = Field(default=0.5, ge=0.1, le=0.9, description="Note onset sensitivity")
    frame_threshold: float = Field(default=0.3, ge=0.1, le=0.9, description="Frame activation threshold")
    min_confidence: float = Field(default=0.5, ge=0, le=1, description="Minimum detection confidence")


class GenerateSheetRequest(BaseModel):
    """Request parameters for sheet generation."""
    
    output_format: OutputFormat = Field(default=OutputFormat.MUSICXML)
    output_type: OutputType = Field(default=OutputType.LEAD_SHEET)
    title: Optional[str] = Field(default="Untitled")
    tempo: int = Field(default=120, ge=20, le=300)
    time_signature: str = Field(default="4/4")
    key_signature: Optional[str] = None
    instrument: Instrument = Field(default=Instrument.PIANO)


class ArrangeRequest(BaseModel):
    """Request for arrangement operations."""
    
    options: ArrangementOptions = Field(default_factory=ArrangementOptions)
    output_format: OutputFormat = Field(default=OutputFormat.MUSICXML)


class TransposeRequest(BaseModel):
    """Request for transposition."""
    
    semitones: int = Field(..., ge=-12, le=12, description="Semitones to transpose (-12 to +12)")
    output_format: OutputFormat = Field(default=OutputFormat.MUSICXML)


class ModeConvertRequest(BaseModel):
    """Request for major/minor conversion."""
    
    target_mode: str = Field(..., pattern="^(major|minor)$", description="Target mode")
    output_format: OutputFormat = Field(default=OutputFormat.MUSICXML)


class SimplifyRequest(BaseModel):
    """Request for chord simplification."""
    
    target_instrument: Instrument = Field(default=Instrument.GUITAR)
    output_format: OutputFormat = Field(default=OutputFormat.MUSICXML)


class MelodyRequest(BaseModel):
    """Request for melody generation."""
    
    style: MelodyStyle = Field(default=MelodyStyle.SIMPLE)
    octave: int = Field(default=4, ge=2, le=6)
    density: float = Field(default=1.0, ge=0.25, le=2.0)
    include_passing_tones: bool = Field(default=True)
    include_neighbor_tones: bool = Field(default=True)
    output_format: OutputFormat = Field(default=OutputFormat.MIDI)


class FullAnalysisRequest(BaseModel):
    """Request for full audio analysis."""
    
    detection: DetectionRequest = Field(default_factory=DetectionRequest)
    generate: GenerateSheetRequest = Field(default_factory=GenerateSheetRequest)
    arrangement: Optional[ArrangementOptions] = None
    melody: Optional[MelodyOptions] = None
