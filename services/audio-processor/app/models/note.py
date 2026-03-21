from pydantic import BaseModel, Field
from typing import Optional


class DetectedNote(BaseModel):
    """Represents a single detected note from audio analysis."""
    
    pitch: int = Field(..., ge=0, le=127, description="MIDI pitch number (0-127)")
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    velocity: int = Field(default=80, ge=1, le=127, description="MIDI velocity (1-127)")
    confidence: float = Field(default=1.0, ge=0, le=1, description="Detection confidence (0-1)")
    pitch_bend: Optional[float] = Field(default=None, description="Pitch bend in semitones")
    
    @property
    def duration(self) -> float:
        """Duration of the note in seconds."""
        return self.end_time - self.start_time
    
    @property
    def note_name(self) -> str:
        """Human-readable note name (e.g., 'C4', 'F#5')."""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (self.pitch // 12) - 1
        note = note_names[self.pitch % 12]
        return f"{note}{octave}"
    
    def transpose(self, semitones: int) -> "DetectedNote":
        """Return a new note transposed by the given semitones."""
        new_pitch = max(0, min(127, self.pitch + semitones))
        return DetectedNote(
            pitch=new_pitch,
            start_time=self.start_time,
            end_time=self.end_time,
            velocity=self.velocity,
            confidence=self.confidence,
            pitch_bend=self.pitch_bend,
        )


class NoteList(BaseModel):
    """Collection of detected notes."""
    
    notes: list[DetectedNote] = Field(default_factory=list)
    source_file: Optional[str] = None
    duration: Optional[float] = Field(default=None, description="Total audio duration in seconds")
    sample_rate: Optional[int] = None
    
    def filter_by_confidence(self, min_confidence: float = 0.5) -> "NoteList":
        """Return notes filtered by minimum confidence."""
        filtered = [n for n in self.notes if n.confidence >= min_confidence]
        return NoteList(
            notes=filtered,
            source_file=self.source_file,
            duration=self.duration,
            sample_rate=self.sample_rate,
        )
    
    def transpose_all(self, semitones: int) -> "NoteList":
        """Return all notes transposed by the given semitones."""
        return NoteList(
            notes=[n.transpose(semitones) for n in self.notes],
            source_file=self.source_file,
            duration=self.duration,
            sample_rate=self.sample_rate,
        )
