"""
Chord detection service using Vamp/Chordino with librosa fallback.

Supports two detection modes:
1. Chordino via Vamp plugin (more accurate, requires VAMP_PATH setup)
2. Librosa chroma-based detection (fallback, always available)
"""

import re
import tempfile
import warnings
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
import librosa

from app.models.chord import DetectedChord, ChordList, ChordQuality

# Try to import vamp, but make it optional
try:
    import vamp
    VAMP_AVAILABLE = True
except ImportError:
    VAMP_AVAILABLE = False
    warnings.warn("Vamp not available. Using librosa-based chord detection.")


class ChordDetector:
    """
    Chord detection from audio.
    
    Uses Chordino Vamp plugin if available, otherwise falls back to
    librosa chroma-based chord recognition.
    """
    
    # Standard chord templates for template matching (chroma vectors)
    CHORD_TEMPLATES = {
        # Major triads
        "C": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
        "C#": [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
        "D": [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],
        "D#": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
        "E": [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
        "F": [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
        "F#": [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        "G": [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        "G#": [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
        "A": [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        "A#": [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        "B": [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1],
        # Minor triads
        "Cm": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
        "C#m": [0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        "Dm": [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0],
        "D#m": [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
        "Em": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        "Fm": [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
        "F#m": [0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0],
        "Gm": [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0],
        "G#m": [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
        "Am": [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        "A#m": [0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        "Bm": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    }
    
    def __init__(
        self,
        use_vamp: bool = True,
        hop_length: int = 2048,
        min_duration: float = 0.5,
    ):
        """
        Initialize chord detector.
        
        Args:
            use_vamp: Try to use Vamp/Chordino if available
            hop_length: Hop length for chroma analysis
            min_duration: Minimum chord duration in seconds
        """
        self.use_vamp = use_vamp and VAMP_AVAILABLE
        self.hop_length = hop_length
        self.min_duration = min_duration
        
        # Check if Chordino plugin is available
        self.chordino_available = False
        if self.use_vamp:
            try:
                plugins = vamp.list_plugins()
                self.chordino_available = "nnls-chroma:chordino" in plugins
            except Exception:
                self.chordino_available = False
        
        # Precompute template matrix for librosa fallback
        self._template_matrix = np.array(list(self.CHORD_TEMPLATES.values())).T
        self._template_names = list(self.CHORD_TEMPLATES.keys())
    
    def detect(self, audio_path: str | Path) -> ChordList:
        """
        Extract chords from audio file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            ChordList containing all detected chords
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Try Chordino first if available
        if self.chordino_available:
            try:
                return self._detect_with_chordino(audio_path)
            except Exception as e:
                warnings.warn(f"Chordino failed: {e}. Falling back to librosa.")
        
        # Fallback to librosa-based detection
        return self._detect_with_librosa(audio_path)
    
    def detect_from_bytes(self, audio_data: bytes, file_extension: str = ".wav") -> ChordList:
        """
        Detect chords from audio bytes.
        
        Args:
            audio_data: Raw audio file bytes
            file_extension: File extension (e.g., ".wav", ".mp3")
            
        Returns:
            ChordList containing all detected chords
        """
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = Path(tmp.name)
        
        try:
            return self.detect(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def _detect_with_chordino(self, audio_path: Path) -> ChordList:
        """Detect chords using Chordino Vamp plugin."""
        # Load audio
        y, sr = librosa.load(str(audio_path), sr=44100, mono=True)
        
        # Run Chordino
        results = vamp.collect(
            y, sr, "nnls-chroma:chordino",
            output="simplechord"
        )
        
        chords = []
        chord_list = results.get("list", [])
        
        for i, item in enumerate(chord_list):
            timestamp = float(item.get("timestamp", 0))
            label = item.get("label", "N")
            
            # Calculate duration
            if i + 1 < len(chord_list):
                duration = float(chord_list[i + 1].get("timestamp", timestamp + 1)) - timestamp
            else:
                duration = 2.0
            
            # Skip "N" (no chord)
            if label == "N" or not label:
                continue
            
            # Parse chord
            root, quality, bass = self._parse_chord_symbol(label)
            
            chords.append(DetectedChord(
                symbol=label,
                root=root,
                quality=quality,
                timestamp=timestamp,
                duration=max(self.min_duration, duration),
                bass_note=bass,
                confidence=0.85,
            ))
        
        # Merge short consecutive identical chords
        chords = self._merge_consecutive_chords(chords)
        
        # Estimate key
        key = self._estimate_key(chords)
        duration = y.shape[0] / sr
        
        return ChordList(
            chords=chords,
            source_file=str(audio_path.name),
            duration=duration,
            key=key,
        )
    
    def _detect_with_librosa(self, audio_path: Path) -> ChordList:
        """Detect chords using librosa chroma features."""
        # Load audio
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        
        # Compute chroma features
        chroma = librosa.feature.chroma_cqt(
            y=y, sr=sr, 
            hop_length=self.hop_length,
            n_chroma=12,
        )
        
        # Get frame times
        times = librosa.frames_to_time(
            np.arange(chroma.shape[1]), 
            sr=sr, 
            hop_length=self.hop_length
        )
        
        # Match each frame to best chord template
        frame_chords = self._match_templates(chroma)
        
        # Group consecutive identical chords
        chords = self._group_chord_frames(frame_chords, times)
        
        # Filter short chords
        chords = [c for c in chords if c.duration >= self.min_duration]
        
        # Estimate key
        key = self._estimate_key(chords)
        duration = y.shape[0] / sr
        
        return ChordList(
            chords=chords,
            source_file=str(audio_path.name),
            duration=duration,
            key=key,
        )
    
    def _match_templates(self, chroma: np.ndarray) -> List[str]:
        """Match chroma frames to chord templates."""
        # Normalize chroma
        chroma_norm = chroma / (np.linalg.norm(chroma, axis=0, keepdims=True) + 1e-6)
        
        # Normalize templates
        templates_norm = self._template_matrix / (
            np.linalg.norm(self._template_matrix, axis=0, keepdims=True) + 1e-6
        )
        
        # Compute similarity (dot product)
        similarity = templates_norm.T @ chroma_norm
        
        # Get best match for each frame
        best_idx = np.argmax(similarity, axis=0)
        
        return [self._template_names[i] for i in best_idx]
    
    def _group_chord_frames(
        self, 
        frame_chords: List[str], 
        times: np.ndarray
    ) -> List[DetectedChord]:
        """Group consecutive chord frames into chord segments."""
        if not frame_chords:
            return []
        
        # Ensure times is a 1D array and convert to Python floats
        times = np.asarray(times).flatten()
        
        chords = []
        current_chord = frame_chords[0]
        start_time = float(times[0])
        
        for i in range(1, len(frame_chords)):
            if frame_chords[i] != current_chord:
                # End current chord
                end_time = float(times[i])
                root, quality, bass = self._parse_chord_symbol(current_chord)
                
                duration = max(0.1, end_time - start_time)
                
                chords.append(DetectedChord(
                    symbol=current_chord,
                    root=root,
                    quality=quality,
                    timestamp=start_time,
                    duration=duration,
                    bass_note=bass,
                    confidence=0.7,  # Lower confidence for librosa method
                ))
                
                current_chord = frame_chords[i]
                start_time = float(times[i])
        
        # Add final chord
        if len(times) > 0:
            root, quality, bass = self._parse_chord_symbol(current_chord)
            final_duration = float(times[-1]) - start_time + self.hop_length / 22050
            final_duration = max(0.1, final_duration)
            
            chords.append(DetectedChord(
                symbol=current_chord,
                root=root,
                quality=quality,
                timestamp=start_time,
                duration=final_duration,
                bass_note=bass,
                confidence=0.7,
            ))
        
        return chords
    
    def _merge_consecutive_chords(self, chords: List[DetectedChord]) -> List[DetectedChord]:
        """Merge consecutive identical chords."""
        if not chords:
            return []
        
        merged = [chords[0]]
        
        for chord in chords[1:]:
            if chord.symbol == merged[-1].symbol:
                # Extend previous chord
                merged[-1] = merged[-1].model_copy(update={
                    "duration": merged[-1].duration + chord.duration
                })
            else:
                merged.append(chord)
        
        return merged
    
    def _parse_chord_symbol(self, symbol: str) -> Tuple[str, ChordQuality, Optional[str]]:
        """
        Parse a chord symbol into its components.
        
        Examples:
            "C" -> ("C", MAJOR, None)
            "Am7" -> ("A", MIN7, None)
            "G/B" -> ("G", MAJOR, "B")
        """
        # Handle slash chords
        bass_note = None
        if "/" in symbol:
            parts = symbol.split("/")
            symbol = parts[0]
            bass_note = parts[1] if len(parts) > 1 else None
        
        # Extract root note
        root_match = re.match(r'^([A-G][#b]?)', symbol)
        if not root_match:
            return ("C", ChordQuality.UNKNOWN, bass_note)
        
        root = root_match.group(1)
        quality_str = symbol[len(root):].strip()
        
        # Map quality string to enum
        quality = self._map_quality(quality_str)
        
        return (root, quality, bass_note)
    
    def _map_quality(self, quality_str: str) -> ChordQuality:
        """Map a quality string to ChordQuality enum."""
        quality_str = quality_str.lower().strip()
        
        quality_map = {
            "": ChordQuality.MAJOR,
            "maj": ChordQuality.MAJOR,
            "major": ChordQuality.MAJOR,
            "m": ChordQuality.MINOR,
            "min": ChordQuality.MINOR,
            "minor": ChordQuality.MINOR,
            "-": ChordQuality.MINOR,
            "dim": ChordQuality.DIMINISHED,
            "o": ChordQuality.DIMINISHED,
            "aug": ChordQuality.AUGMENTED,
            "+": ChordQuality.AUGMENTED,
            "7": ChordQuality.DOMINANT_7,
            "dom7": ChordQuality.DOMINANT_7,
            "maj7": ChordQuality.MAJOR_7,
            "m7": ChordQuality.MINOR_7,
            "min7": ChordQuality.MINOR_7,
            "-7": ChordQuality.MINOR_7,
            "dim7": ChordQuality.DIMINISHED_7,
            "o7": ChordQuality.DIMINISHED_7,
            "m7b5": ChordQuality.HALF_DIMINISHED_7,
            "sus2": ChordQuality.SUSPENDED_2,
            "sus4": ChordQuality.SUSPENDED_4,
            "add9": ChordQuality.ADD_9,
        }
        
        if quality_str in quality_map:
            return quality_map[quality_str]
        
        # Handle compound qualities
        if "maj7" in quality_str:
            return ChordQuality.MAJOR_7
        if "m7" in quality_str or ("7" in quality_str and "m" in quality_str):
            return ChordQuality.MINOR_7
        if "7" in quality_str:
            return ChordQuality.DOMINANT_7
        if "m" in quality_str:
            return ChordQuality.MINOR
        if "dim" in quality_str:
            return ChordQuality.DIMINISHED
        if "aug" in quality_str:
            return ChordQuality.AUGMENTED
        
        return ChordQuality.MAJOR
    
    def _estimate_key(self, chords: List[DetectedChord]) -> Optional[str]:
        """Estimate key signature from chord progression."""
        if not chords:
            return None
        
        # Weight chords by duration and position
        root_weights = {}
        total_duration = sum(c.duration for c in chords)
        
        for i, chord in enumerate(chords):
            weight = chord.duration / total_duration if total_duration > 0 else 1
            
            # Boost first and last chords
            if i == 0:
                weight *= 1.5
            if i == len(chords) - 1:
                weight *= 1.3
            
            root_weights[chord.root] = root_weights.get(chord.root, 0) + weight
        
        if not root_weights:
            return None
        
        likely_root = max(root_weights, key=root_weights.get)
        
        # Determine major or minor
        minor_count = sum(1 for c in chords if c.quality == ChordQuality.MINOR)
        major_count = sum(1 for c in chords if c.quality == ChordQuality.MAJOR)
        
        root_chords = [c for c in chords if c.root == likely_root]
        if root_chords and root_chords[0].quality == ChordQuality.MINOR:
            return f"{likely_root} minor"
        
        if minor_count > major_count * 1.5:
            note_idx = self._note_to_index(likely_root)
            minor_root_idx = (note_idx - 3) % 12
            minor_root = self._index_to_note(minor_root_idx)
            return f"{minor_root} minor"
        
        return f"{likely_root} major"
    
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
    
    def _index_to_note(self, index: int) -> str:
        """Convert chromatic index to note name."""
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return notes[index % 12]
    
    def get_detection_method(self) -> str:
        """Return which detection method will be used."""
        if self.chordino_available:
            return "chordino"
        return "librosa"
