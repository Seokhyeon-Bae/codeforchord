"""Merge and combine audio analysis results."""

from typing import Optional, Tuple
from pathlib import Path
import tempfile

from app.models.note import NoteList
from app.models.chord import ChordList
from app.services.pitch_detector import PitchDetector
from app.services.chord_detector import ChordDetector


class AudioMerger:
    """
    Combine results from multiple audio analysis services.
    
    Handles:
    - Running both pitch and chord detection
    - Aligning results temporally
    - Filtering by instrument type
    """
    
    def __init__(
        self,
        pitch_detector: Optional[PitchDetector] = None,
        chord_detector: Optional[ChordDetector] = None,
    ):
        self.pitch_detector = pitch_detector or PitchDetector()
        self.chord_detector = chord_detector or ChordDetector()
    
    def analyze(
        self, 
        audio_path: str | Path,
        detect_notes: bool = True,
        detect_chords: bool = True,
        min_note_confidence: float = 0.5,
    ) -> Tuple[Optional[NoteList], Optional[ChordList]]:
        """
        Run full audio analysis.
        
        Args:
            audio_path: Path to audio file
            detect_notes: Whether to detect notes
            detect_chords: Whether to detect chords
            min_note_confidence: Minimum confidence for note inclusion
            
        Returns:
            Tuple of (NoteList, ChordList)
        """
        notes = None
        chords = None
        
        if detect_notes:
            notes = self.pitch_detector.detect(audio_path)
            if min_note_confidence > 0:
                notes = notes.filter_by_confidence(min_note_confidence)
        
        if detect_chords:
            chords = self.chord_detector.detect(audio_path)
        
        return notes, chords
    
    def analyze_from_bytes(
        self,
        audio_data: bytes,
        file_extension: str = ".wav",
        detect_notes: bool = True,
        detect_chords: bool = True,
        min_note_confidence: float = 0.5,
    ) -> Tuple[Optional[NoteList], Optional[ChordList]]:
        """
        Run full audio analysis from bytes.
        
        Args:
            audio_data: Raw audio bytes
            file_extension: Audio format extension
            detect_notes: Whether to detect notes
            detect_chords: Whether to detect chords
            min_note_confidence: Minimum note confidence
            
        Returns:
            Tuple of (NoteList, ChordList)
        """
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = Path(tmp.name)
        
        try:
            return self.analyze(
                tmp_path,
                detect_notes=detect_notes,
                detect_chords=detect_chords,
                min_note_confidence=min_note_confidence,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def align_to_beats(
        self,
        notes: NoteList,
        chords: ChordList,
        bpm: int = 120,
    ) -> Tuple[NoteList, ChordList]:
        """
        Quantize note and chord timings to beat grid.
        
        Useful for cleaner sheet music output.
        """
        seconds_per_beat = 60.0 / bpm
        
        # Quantize notes
        quantized_notes = []
        for note in notes.notes:
            # Round to nearest 16th note
            grid = seconds_per_beat / 4
            new_start = round(note.start_time / grid) * grid
            new_end = round(note.end_time / grid) * grid
            
            # Ensure minimum duration
            if new_end <= new_start:
                new_end = new_start + grid
            
            quantized_notes.append(note.model_copy(update={
                "start_time": new_start,
                "end_time": new_end,
            }))
        
        # Quantize chords
        quantized_chords = []
        for chord in chords.chords:
            grid = seconds_per_beat
            new_timestamp = round(chord.timestamp / grid) * grid
            new_duration = round(chord.duration / grid) * grid
            
            if new_duration < grid:
                new_duration = grid
            
            quantized_chords.append(chord.model_copy(update={
                "timestamp": new_timestamp,
                "duration": new_duration,
            }))
        
        return (
            NoteList(
                notes=quantized_notes,
                source_file=notes.source_file,
                duration=notes.duration,
                sample_rate=notes.sample_rate,
            ),
            ChordList(
                chords=quantized_chords,
                source_file=chords.source_file,
                duration=chords.duration,
                key=chords.key,
            ),
        )
    
    def filter_by_instrument(
        self,
        notes: NoteList,
        instrument: str,
    ) -> NoteList:
        """
        Filter notes by typical instrument range.
        
        Args:
            notes: Input notes
            instrument: "piano", "guitar", or "vocal"
            
        Returns:
            Filtered NoteList
        """
        # Typical MIDI ranges
        ranges = {
            "piano": (21, 108),   # A0 to C8
            "guitar": (40, 88),   # E2 to E6
            "vocal": (48, 84),    # C3 to C6
        }
        
        min_pitch, max_pitch = ranges.get(instrument.lower(), (0, 127))
        
        filtered = [
            n for n in notes.notes 
            if min_pitch <= n.pitch <= max_pitch
        ]
        
        return NoteList(
            notes=filtered,
            source_file=notes.source_file,
            duration=notes.duration,
            sample_rate=notes.sample_rate,
        )
