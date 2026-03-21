from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ChordQuality(str, Enum):
    """Chord quality types."""
    
    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"
    AUGMENTED = "augmented"
    DOMINANT_7 = "dom7"
    MAJOR_7 = "maj7"
    MINOR_7 = "min7"
    DIMINISHED_7 = "dim7"
    HALF_DIMINISHED_7 = "half-dim7"
    SUSPENDED_2 = "sus2"
    SUSPENDED_4 = "sus4"
    ADD_9 = "add9"
    UNKNOWN = "unknown"


class DetectedChord(BaseModel):
    """Represents a single detected chord from audio analysis."""
    
    symbol: str = Field(..., description="Full chord symbol (e.g., 'Cmaj7', 'Am', 'G/B')")
    root: str = Field(..., description="Root note (e.g., 'C', 'A', 'G')")
    quality: ChordQuality = Field(default=ChordQuality.MAJOR, description="Chord quality")
    timestamp: float = Field(..., ge=0, description="Start time in seconds")
    duration: float = Field(default=1.0, ge=0, description="Duration in seconds")
    bass_note: Optional[str] = Field(default=None, description="Bass note for slash chords")
    confidence: float = Field(default=1.0, ge=0, le=1, description="Detection confidence")
    
    @property
    def end_time(self) -> float:
        """End time of the chord."""
        return self.timestamp + self.duration
    
    @property
    def root_midi(self) -> int:
        """MIDI pitch of root note (C4 = 60)."""
        note_map = {
            "C": 0, "C#": 1, "Db": 1,
            "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "Fb": 4,
            "F": 5, "F#": 6, "Gb": 6,
            "G": 7, "G#": 8, "Ab": 8,
            "A": 9, "A#": 10, "Bb": 10,
            "B": 11, "Cb": 11,
        }
        return 60 + note_map.get(self.root, 0)
    
    def transpose(self, semitones: int) -> "DetectedChord":
        """Return a new chord transposed by the given semitones."""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # Calculate new root
        current_idx = self._note_to_index(self.root)
        new_idx = (current_idx + semitones) % 12
        new_root = note_names[new_idx]
        
        # Calculate new bass if present
        new_bass = None
        if self.bass_note:
            bass_idx = self._note_to_index(self.bass_note)
            new_bass_idx = (bass_idx + semitones) % 12
            new_bass = note_names[new_bass_idx]
        
        # Build new symbol
        quality_suffix = self._get_quality_suffix()
        new_symbol = new_root + quality_suffix
        if new_bass:
            new_symbol += f"/{new_bass}"
        
        return DetectedChord(
            symbol=new_symbol,
            root=new_root,
            quality=self.quality,
            timestamp=self.timestamp,
            duration=self.duration,
            bass_note=new_bass,
            confidence=self.confidence,
        )
    
    def to_minor(self) -> "DetectedChord":
        """Convert major chord to minor."""
        if self.quality == ChordQuality.MAJOR:
            new_quality = ChordQuality.MINOR
            new_symbol = self.root + "m"
            if self.bass_note:
                new_symbol += f"/{self.bass_note}"
            return DetectedChord(
                symbol=new_symbol,
                root=self.root,
                quality=new_quality,
                timestamp=self.timestamp,
                duration=self.duration,
                bass_note=self.bass_note,
                confidence=self.confidence,
            )
        return self
    
    def to_major(self) -> "DetectedChord":
        """Convert minor chord to major."""
        if self.quality == ChordQuality.MINOR:
            new_quality = ChordQuality.MAJOR
            new_symbol = self.root
            if self.bass_note:
                new_symbol += f"/{self.bass_note}"
            return DetectedChord(
                symbol=new_symbol,
                root=self.root,
                quality=new_quality,
                timestamp=self.timestamp,
                duration=self.duration,
                bass_note=self.bass_note,
                confidence=self.confidence,
            )
        return self
    
    def diminish(self) -> "DetectedChord":
        """Convert to diminished chord."""
        new_symbol = self.root + "dim"
        if self.bass_note:
            new_symbol += f"/{self.bass_note}"
        return DetectedChord(
            symbol=new_symbol,
            root=self.root,
            quality=ChordQuality.DIMINISHED,
            timestamp=self.timestamp,
            duration=self.duration,
            bass_note=self.bass_note,
            confidence=self.confidence,
        )
    
    def augment(self) -> "DetectedChord":
        """Convert to augmented chord."""
        new_symbol = self.root + "aug"
        if self.bass_note:
            new_symbol += f"/{self.bass_note}"
        return DetectedChord(
            symbol=new_symbol,
            root=self.root,
            quality=ChordQuality.AUGMENTED,
            timestamp=self.timestamp,
            duration=self.duration,
            bass_note=self.bass_note,
            confidence=self.confidence,
        )
    
    def _note_to_index(self, note: str) -> int:
        """Convert note name to chromatic index."""
        note_map = {
            "C": 0, "C#": 1, "Db": 1,
            "D": 2, "D#": 3, "Eb": 3,
            "E": 4,
            "F": 5, "F#": 6, "Gb": 6,
            "G": 7, "G#": 8, "Ab": 8,
            "A": 9, "A#": 10, "Bb": 10,
            "B": 11,
        }
        return note_map.get(note, 0)
    
    def _get_quality_suffix(self) -> str:
        """Get chord symbol suffix for quality."""
        suffix_map = {
            ChordQuality.MAJOR: "",
            ChordQuality.MINOR: "m",
            ChordQuality.DIMINISHED: "dim",
            ChordQuality.AUGMENTED: "aug",
            ChordQuality.DOMINANT_7: "7",
            ChordQuality.MAJOR_7: "maj7",
            ChordQuality.MINOR_7: "m7",
            ChordQuality.DIMINISHED_7: "dim7",
            ChordQuality.HALF_DIMINISHED_7: "m7b5",
            ChordQuality.SUSPENDED_2: "sus2",
            ChordQuality.SUSPENDED_4: "sus4",
            ChordQuality.ADD_9: "add9",
        }
        return suffix_map.get(self.quality, "")


class ChordList(BaseModel):
    """Collection of detected chords."""
    
    chords: list[DetectedChord] = Field(default_factory=list)
    source_file: Optional[str] = None
    duration: Optional[float] = Field(default=None, description="Total audio duration")
    key: Optional[str] = Field(default=None, description="Detected key signature")
    
    def transpose_all(self, semitones: int) -> "ChordList":
        """Return all chords transposed by the given semitones."""
        return ChordList(
            chords=[c.transpose(semitones) for c in self.chords],
            source_file=self.source_file,
            duration=self.duration,
            key=self._transpose_key(semitones) if self.key else None,
        )
    
    def to_minor_all(self) -> "ChordList":
        """Convert all major chords to minor."""
        return ChordList(
            chords=[c.to_minor() for c in self.chords],
            source_file=self.source_file,
            duration=self.duration,
            key=self.key,
        )
    
    def to_major_all(self) -> "ChordList":
        """Convert all minor chords to major."""
        return ChordList(
            chords=[c.to_major() for c in self.chords],
            source_file=self.source_file,
            duration=self.duration,
            key=self.key,
        )
    
    def _transpose_key(self, semitones: int) -> str:
        """Transpose the key signature."""
        if not self.key:
            return None
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # Parse key (e.g., "C major", "Am")
        parts = self.key.replace(" ", "").lower()
        is_minor = "m" in parts or "minor" in parts.lower()
        root = parts.replace("minor", "").replace("major", "").replace("m", "").strip().upper()
        
        note_map = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, 
                    "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, 
                    "A": 9, "A#": 10, "BB": 10, "B": 11}
        
        if root.upper() in note_map:
            idx = note_map[root.upper()]
            new_idx = (idx + semitones) % 12
            new_root = note_names[new_idx]
            return f"{new_root} {'minor' if is_minor else 'major'}"
        return self.key
