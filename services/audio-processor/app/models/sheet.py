from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class OutputFormat(str, Enum):
    """Supported output formats."""
    
    MUSICXML = "musicxml"
    MIDI = "midi"
    JSON = "json"


class OutputType(str, Enum):
    """Type of sheet output."""
    
    CHORDS_ONLY = "chords_only"
    LEAD_SHEET = "lead_sheet"
    FULL_SCORE = "full_score"


class Instrument(str, Enum):
    """Supported instruments."""
    
    PIANO = "piano"
    GUITAR = "guitar"
    VOCAL = "vocal"


class SheetMetadata(BaseModel):
    """Metadata for generated sheet music."""
    
    title: Optional[str] = Field(default="Untitled", description="Song title")
    composer: Optional[str] = None
    tempo: int = Field(default=120, ge=20, le=300, description="Tempo in BPM")
    time_signature: str = Field(default="4/4", description="Time signature")
    key_signature: Optional[str] = Field(default=None, description="Key signature")
    instrument: Instrument = Field(default=Instrument.PIANO)


class GeneratedSheet(BaseModel):
    """Result of sheet music generation."""
    
    content: str = Field(..., description="Generated content (MusicXML string or base64 MIDI)")
    format: OutputFormat
    output_type: OutputType
    metadata: SheetMetadata
    filename: str = Field(default="output", description="Suggested filename (without extension)")
    
    @property
    def file_extension(self) -> str:
        """Get file extension for the format."""
        ext_map = {
            OutputFormat.MUSICXML: ".musicxml",
            OutputFormat.MIDI: ".mid",
            OutputFormat.JSON: ".json",
        }
        return ext_map.get(self.format, ".txt")


class ArrangementOptions(BaseModel):
    """Options for music arrangement."""
    
    transpose_semitones: int = Field(default=0, ge=-12, le=12, description="Semitones to transpose")
    convert_to_minor: bool = Field(default=False, description="Convert major chords to minor")
    convert_to_major: bool = Field(default=False, description="Convert minor chords to major")
    simplify_chords: bool = Field(default=False, description="Simplify to easy voicings")
    target_instrument: Optional[Instrument] = None


class MelodyStyle(str, Enum):
    """Style for melody generation."""
    
    SIMPLE = "simple"
    ARPEGGIATED = "arpeggiated"
    SCALAR = "scalar"
    RHYTHMIC = "rhythmic"


class MelodyOptions(BaseModel):
    """Options for melody suggestion."""
    
    style: MelodyStyle = Field(default=MelodyStyle.SIMPLE)
    octave: int = Field(default=4, ge=2, le=6, description="Base octave for melody")
    density: float = Field(default=1.0, ge=0.25, le=2.0, description="Note density multiplier")
    include_passing_tones: bool = Field(default=True)
    include_neighbor_tones: bool = Field(default=True)
