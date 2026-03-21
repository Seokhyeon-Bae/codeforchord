"""Music arrangement engine for transformations and simplifications."""

from typing import Optional
from copy import deepcopy

from app.models.note import DetectedNote, NoteList
from app.models.chord import DetectedChord, ChordList, ChordQuality
from app.models.sheet import Instrument, ArrangementOptions
from app.core.constants import EASY_GUITAR_VOICINGS, NOTE_NAMES


class Arranger:
    """
    Music arrangement engine for chord and note transformations.
    
    Supports:
    - Transposition
    - Major/minor mode conversion
    - Chord augmentation/diminution
    - Simplification for different instruments
    - Style-based voicing suggestions
    """
    
    # Chord simplification mappings (complex -> simple)
    SIMPLIFICATION_MAP = {
        # Seventh chords to triads
        ChordQuality.MAJOR_7: ChordQuality.MAJOR,
        ChordQuality.MINOR_7: ChordQuality.MINOR,
        ChordQuality.DOMINANT_7: ChordQuality.MAJOR,
        ChordQuality.DIMINISHED_7: ChordQuality.DIMINISHED,
        ChordQuality.HALF_DIMINISHED_7: ChordQuality.MINOR,
        # Extensions to base
        ChordQuality.ADD_9: ChordQuality.MAJOR,
        # Suspended to major (common simplification)
        ChordQuality.SUSPENDED_2: ChordQuality.MAJOR,
        ChordQuality.SUSPENDED_4: ChordQuality.MAJOR,
    }
    
    # Jazz voicing extensions
    JAZZ_EXTENSIONS = {
        ChordQuality.MAJOR: ChordQuality.MAJOR_7,
        ChordQuality.MINOR: ChordQuality.MINOR_7,
    }
    
    def __init__(self):
        pass
    
    def arrange(
        self,
        notes: Optional[NoteList] = None,
        chords: Optional[ChordList] = None,
        options: Optional[ArrangementOptions] = None,
    ) -> tuple[Optional[NoteList], Optional[ChordList]]:
        """
        Apply arrangement transformations based on options.
        
        Args:
            notes: Notes to transform
            chords: Chords to transform
            options: Arrangement options
            
        Returns:
            Tuple of (transformed notes, transformed chords)
        """
        options = options or ArrangementOptions()
        
        result_notes = deepcopy(notes) if notes else None
        result_chords = deepcopy(chords) if chords else None
        
        # Apply transposition first
        if options.transpose_semitones != 0:
            if result_notes:
                result_notes = result_notes.transpose_all(options.transpose_semitones)
            if result_chords:
                result_chords = result_chords.transpose_all(options.transpose_semitones)
        
        # Apply mode conversion
        if options.convert_to_minor and result_chords:
            result_chords = result_chords.to_minor_all()
        elif options.convert_to_major and result_chords:
            result_chords = result_chords.to_major_all()
        
        # Apply simplification
        if options.simplify_chords and result_chords:
            result_chords = self.simplify_chords(
                result_chords, 
                options.target_instrument or Instrument.GUITAR
            )
        
        return result_notes, result_chords
    
    def transpose(
        self,
        notes: Optional[NoteList] = None,
        chords: Optional[ChordList] = None,
        semitones: int = 0,
    ) -> tuple[Optional[NoteList], Optional[ChordList]]:
        """
        Transpose notes and chords by a number of semitones.
        
        Args:
            notes: Notes to transpose
            chords: Chords to transpose
            semitones: Number of semitones (-12 to +12)
            
        Returns:
            Tuple of transposed (notes, chords)
        """
        result_notes = notes.transpose_all(semitones) if notes else None
        result_chords = chords.transpose_all(semitones) if chords else None
        return result_notes, result_chords
    
    def to_minor(self, chords: ChordList) -> ChordList:
        """Convert all major chords to their parallel minor."""
        return chords.to_minor_all()
    
    def to_major(self, chords: ChordList) -> ChordList:
        """Convert all minor chords to their parallel major."""
        return chords.to_major_all()
    
    def diminish_chord(self, chord: DetectedChord) -> DetectedChord:
        """
        Convert a chord to diminished.
        
        Flattens the 3rd and 5th intervals.
        """
        return chord.diminish()
    
    def augment_chord(self, chord: DetectedChord) -> DetectedChord:
        """
        Convert a chord to augmented.
        
        Raises the 5th by a semitone.
        """
        return chord.augment()
    
    def simplify_chords(
        self, 
        chords: ChordList, 
        target_instrument: Instrument = Instrument.GUITAR
    ) -> ChordList:
        """
        Simplify chord voicings for easier playing.
        
        Args:
            chords: Original chord list
            target_instrument: Target instrument for voicing
            
        Returns:
            ChordList with simplified chords
        """
        simplified = []
        
        for chord in chords.chords:
            simple_chord = self._simplify_single_chord(chord, target_instrument)
            simplified.append(simple_chord)
        
        return ChordList(
            chords=simplified,
            source_file=chords.source_file,
            duration=chords.duration,
            key=chords.key,
        )
    
    def _simplify_single_chord(
        self, 
        chord: DetectedChord, 
        instrument: Instrument
    ) -> DetectedChord:
        """Simplify a single chord based on instrument."""
        # Get simplified quality
        new_quality = self.SIMPLIFICATION_MAP.get(chord.quality, chord.quality)
        
        # Build new symbol
        quality_suffix = self._quality_to_suffix(new_quality)
        new_symbol = chord.root + quality_suffix
        
        # Remove slash bass for guitar (makes fingering easier)
        bass = chord.bass_note
        if instrument == Instrument.GUITAR:
            bass = None
        else:
            if bass:
                new_symbol += f"/{bass}"
        
        return DetectedChord(
            symbol=new_symbol,
            root=chord.root,
            quality=new_quality,
            timestamp=chord.timestamp,
            duration=chord.duration,
            bass_note=bass,
            confidence=chord.confidence,
        )
    
    def jazzify_chords(self, chords: ChordList) -> ChordList:
        """
        Add jazz extensions to simple chords.
        
        Converts triads to seventh chords.
        """
        jazzified = []
        
        for chord in chords.chords:
            new_quality = self.JAZZ_EXTENSIONS.get(chord.quality, chord.quality)
            
            quality_suffix = self._quality_to_suffix(new_quality)
            new_symbol = chord.root + quality_suffix
            if chord.bass_note:
                new_symbol += f"/{chord.bass_note}"
            
            jazzified.append(DetectedChord(
                symbol=new_symbol,
                root=chord.root,
                quality=new_quality,
                timestamp=chord.timestamp,
                duration=chord.duration,
                bass_note=chord.bass_note,
                confidence=chord.confidence,
            ))
        
        return ChordList(
            chords=jazzified,
            source_file=chords.source_file,
            duration=chords.duration,
            key=chords.key,
        )
    
    def get_easy_guitar_voicing(self, chord: DetectedChord) -> Optional[list[Optional[int]]]:
        """
        Get easy guitar fingering for a chord.
        
        Returns a list of fret numbers for strings 6-1 (low E to high E).
        None means don't play that string.
        """
        # Simplify first
        simple = self._simplify_single_chord(chord, Instrument.GUITAR)
        
        # Look up in voicing dictionary
        voicing_key = simple.symbol.replace("#", "#").replace("b", "b")
        
        # Try exact match
        if voicing_key in EASY_GUITAR_VOICINGS:
            return EASY_GUITAR_VOICINGS[voicing_key]
        
        # Try with just root + quality
        simple_key = simple.root
        if simple.quality == ChordQuality.MINOR:
            simple_key += "m"
        
        if simple_key in EASY_GUITAR_VOICINGS:
            return EASY_GUITAR_VOICINGS[simple_key]
        
        return None
    
    def transpose_to_key(
        self,
        chords: ChordList,
        target_key: str,
    ) -> ChordList:
        """
        Transpose chords to a target key.
        
        Args:
            chords: Original chords
            target_key: Target key (e.g., "C major", "Am")
            
        Returns:
            Transposed chord list
        """
        if not chords.key:
            return chords
        
        # Parse current and target keys
        current_root = self._parse_key_root(chords.key)
        target_root = self._parse_key_root(target_key)
        
        if current_root is None or target_root is None:
            return chords
        
        # Calculate semitone difference
        current_idx = self._note_to_index(current_root)
        target_idx = self._note_to_index(target_root)
        semitones = (target_idx - current_idx) % 12
        
        # Choose direction (prefer smaller interval)
        if semitones > 6:
            semitones -= 12
        
        return chords.transpose_all(semitones)
    
    def _parse_key_root(self, key: str) -> Optional[str]:
        """Extract root note from key string."""
        if not key:
            return None
        
        key = key.strip()
        
        # Handle "C major", "A minor", "Am", "C"
        parts = key.split()
        root = parts[0]
        
        # Remove "m" suffix if present
        if root.endswith("m") and len(root) > 1:
            root = root[:-1]
        
        # Validate
        if root[0].upper() in "ABCDEFG":
            return root[0].upper() + root[1:] if len(root) > 1 else root.upper()
        
        return None
    
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
    
    def _quality_to_suffix(self, quality: ChordQuality) -> str:
        """Convert ChordQuality to chord symbol suffix."""
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
            ChordQuality.UNKNOWN: "",
        }
        return suffix_map.get(quality, "")
