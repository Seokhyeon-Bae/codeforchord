"""Sheet music generation using music21 for MusicXML output."""

import logging
import math
from typing import Optional, List, Tuple
from music21 import (
    stream, 
    note, 
    chord as m21_chord, 
    meter, 
    key as m21_key, 
    tempo,
    harmony,
    instrument,
    expressions,
    clef,
    layout,
    duration,
)

from app.models.note import DetectedNote, NoteList
from app.models.chord import DetectedChord, ChordList, ChordQuality
from app.models.sheet import (
    OutputType, 
    SheetMetadata, 
    GeneratedSheet, 
    OutputFormat,
    Instrument,
)

logger = logging.getLogger(__name__)

# Standard quantization grid values (in quarter notes)
# Using only common, "normal" note values - no 32nd or 64th notes
QUANTIZE_GRID = [
    4.0,    # whole
    3.0,    # dotted half
    2.0,    # half
    1.5,    # dotted quarter
    1.0,    # quarter
    0.75,   # dotted eighth
    0.5,    # eighth
]

# Minimum note duration - use eighth note as minimum for readability
MIN_NOTE_DURATION = 0.5  # eighth note

# Beat positions for snapping - use half-beat grid for cleaner notation
BEAT_SUBDIVISIONS = [0.0, 0.5]  # On beat and off-beat only


class SheetGenerator:
    """Generate MusicXML sheet music from detected notes and chords."""
    
    def __init__(self, enable_correction: bool = True):
        self.ticks_per_beat = 480
        self.enable_correction = enable_correction
        self._corrector = None
    
    @property
    def corrector(self):
        """Lazy-load the rhythm corrector."""
        if self._corrector is None and self.enable_correction:
            try:
                from app.services.rhythm_corrector import RhythmCorrector
                self._corrector = RhythmCorrector()
            except Exception as e:
                logger.warning(f"Could not load rhythm corrector: {e}")
                self._corrector = False  # Mark as failed
        return self._corrector if self._corrector else None
    
    def generate(
        self,
        notes: Optional[NoteList] = None,
        chords: Optional[ChordList] = None,
        output_type: OutputType = OutputType.LEAD_SHEET,
        metadata: Optional[SheetMetadata] = None,
        correction_strength: float = 0.5,
    ) -> GeneratedSheet:
        """
        Generate sheet music from notes and/or chords.
        
        Args:
            notes: Detected notes (melody line)
            chords: Detected chords
            output_type: Type of sheet to generate
            metadata: Sheet metadata (title, tempo, etc.)
            correction_strength: 0-1, rhythm correction strength (0=off)
            
        Returns:
            GeneratedSheet with MusicXML content
        """
        metadata = metadata or SheetMetadata()
        
        # Apply rhythm correction if enabled
        if notes and correction_strength > 0 and self.corrector:
            try:
                notes = self.corrector.correct(
                    notes,
                    time_signature=metadata.time_signature,
                    tempo=metadata.tempo,
                    correction_strength=correction_strength,
                )
                logger.info(f"Applied rhythm correction (strength={correction_strength})")
            except Exception as e:
                logger.warning(f"Rhythm correction failed: {e}")
        
        if output_type == OutputType.CHORDS_ONLY:
            score = self._generate_chords_only(chords, metadata)
        elif output_type == OutputType.LEAD_SHEET:
            score = self._generate_lead_sheet(notes, chords, metadata)
        else:  # FULL_SCORE
            score = self._generate_full_score(notes, chords, metadata)
        
        # Export to MusicXML string
        musicxml_content = self._export_to_musicxml(score)
        
        return GeneratedSheet(
            content=musicxml_content,
            format=OutputFormat.MUSICXML,
            output_type=output_type,
            metadata=metadata,
            filename=metadata.title.replace(" ", "_").lower() if metadata.title else "output",
        )
    
    def _generate_chords_only(
        self, 
        chords: Optional[ChordList], 
        metadata: SheetMetadata
    ) -> stream.Score:
        """Generate a chord chart without melody."""
        score = stream.Score()
        score.metadata = self._create_metadata(metadata)
        
        part = stream.Part()
        part.partName = "Chords"
        
        # Add instrument based on metadata
        part.insert(0, self._get_instrument(metadata.instrument))
        
        # Add time signature and tempo
        ts = self._parse_time_signature(metadata.time_signature)
        part.append(ts)
        part.append(tempo.MetronomeMark(number=metadata.tempo))
        
        # Add key signature if provided
        if metadata.key_signature:
            ks = self._parse_key_signature(metadata.key_signature)
            if ks:
                part.append(ks)
        
        # Add chord symbols as slash notation or rhythmic notation
        if chords and chords.chords:
            self._add_chord_symbols(part, chords.chords, ts.beatCount)
        else:
            # Add empty measures if no chords
            part.append(note.Rest(quarterLength=4))
        
        score.append(part)
        return score
    
    def _generate_lead_sheet(
        self,
        notes: Optional[NoteList],
        chords: Optional[ChordList],
        metadata: SheetMetadata,
    ) -> stream.Score:
        """Generate a lead sheet with melody and chord symbols."""
        score = stream.Score()
        score.metadata = self._create_metadata(metadata)
        
        part = stream.Part()
        part.partName = "Lead"
        
        # Add instrument
        part.insert(0, self._get_instrument(metadata.instrument))
        
        # Add time signature and tempo
        ts = self._parse_time_signature(metadata.time_signature)
        part.append(ts)
        part.append(tempo.MetronomeMark(number=metadata.tempo))
        
        # Add key signature
        if metadata.key_signature:
            ks = self._parse_key_signature(metadata.key_signature)
            if ks:
                part.append(ks)
        elif chords and chords.key:
            ks = self._parse_key_signature(chords.key)
            if ks:
                part.append(ks)
        
        # Add appropriate clef for instrument
        if metadata.instrument == Instrument.GUITAR:
            part.append(clef.TrebleClef())
        elif metadata.instrument == Instrument.VOCAL:
            part.append(clef.TrebleClef())
        
        # Add melody notes
        if notes and notes.notes:
            self._add_melody_notes(part, notes.notes, metadata.tempo)
        
        # Add chord symbols above the staff
        if chords and chords.chords:
            self._add_chord_symbols_to_part(part, chords.chords, metadata.tempo)
        
        score.append(part)
        return score
    
    def _generate_full_score(
        self,
        notes: Optional[NoteList],
        chords: Optional[ChordList],
        metadata: SheetMetadata,
    ) -> stream.Score:
        """Generate a full piano score with grand staff (treble + bass clefs)."""
        score = stream.Score()
        score.metadata = self._create_metadata(metadata)
        
        # For piano, create a proper grand staff
        if metadata.instrument == Instrument.PIANO or not notes:
            return self._generate_piano_grand_staff(notes, chords, metadata)
        
        # For other instruments, use melody + accompaniment
        melody_part = stream.Part()
        melody_part.partName = "Melody"
        melody_part.insert(0, self._get_instrument(metadata.instrument))
        
        ts = self._parse_time_signature(metadata.time_signature)
        melody_part.append(ts)
        melody_part.append(tempo.MetronomeMark(number=metadata.tempo))
        
        if metadata.key_signature:
            ks = self._parse_key_signature(metadata.key_signature)
            if ks:
                melody_part.append(ks)
        
        if notes and notes.notes:
            self._add_melody_notes(melody_part, notes.notes, metadata.tempo)
        else:
            melody_part.append(note.Rest(quarterLength=4))
        
        score.append(melody_part)
        
        # Piano accompaniment part
        chord_part = stream.Part()
        chord_part.partName = "Piano"
        chord_part.insert(0, instrument.Piano())
        chord_part.append(self._parse_time_signature(metadata.time_signature))
        
        if chords and chords.chords:
            self._add_chord_voicings(chord_part, chords.chords, metadata.tempo)
        else:
            chord_part.append(note.Rest(quarterLength=4))
        
        score.append(chord_part)
        
        return score
    
    def _generate_piano_grand_staff(
        self,
        notes: Optional[NoteList],
        chords: Optional[ChordList],
        metadata: SheetMetadata,
    ) -> stream.Score:
        """Generate a proper piano grand staff with treble and bass clefs."""
        score = stream.Score()
        score.metadata = self._create_metadata(metadata)
        
        ts = self._parse_time_signature(metadata.time_signature)
        beats_per_measure = ts.numerator
        beat_type = ts.denominator
        quarter_notes_per_measure = (4.0 / beat_type) * beats_per_measure
        
        # Split notes into right hand (treble) and left hand (bass)
        SPLIT_PITCH = 60  # Middle C
        
        right_hand_notes = []
        left_hand_notes = []
        
        if notes and notes.notes:
            for n in notes.notes:
                if n.pitch >= SPLIT_PITCH:
                    right_hand_notes.append(n)
                else:
                    left_hand_notes.append(n)
        
        # Calculate total duration needed
        seconds_per_beat = 60.0 / metadata.tempo
        total_duration = 0.0
        if notes and notes.notes:
            for n in notes.notes:
                end_time = n.start_time + n.duration
                total_duration = max(total_duration, end_time)
        if chords and chords.chords:
            for c in chords.chords:
                end_time = c.timestamp + c.duration
                total_duration = max(total_duration, end_time)
        
        total_quarter_notes = total_duration / seconds_per_beat
        num_measures = max(1, math.ceil(total_quarter_notes / quarter_notes_per_measure))
        
        # Create key signature
        key_sig = None
        if metadata.key_signature:
            key_sig = self._parse_key_signature(metadata.key_signature)
        elif chords and chords.key:
            key_sig = self._parse_key_signature(chords.key)
        
        # Right hand part (treble clef)
        right_part = stream.Part()
        right_part.partName = "Piano"
        right_part.insert(0, instrument.Piano())
        right_part.insert(0, clef.TrebleClef())
        right_part.insert(0, ts)
        right_part.insert(0, tempo.MetronomeMark(number=metadata.tempo))
        if key_sig:
            right_part.insert(0, key_sig)
        
        # Add right hand notes with proper alignment
        self._add_aligned_notes(
            right_part, 
            right_hand_notes, 
            metadata.tempo, 
            quarter_notes_per_measure,
            num_measures
        )
        
        # Add chord symbols above treble staff
        if chords and chords.chords:
            self._add_chord_symbols_to_part(right_part, chords.chords, metadata.tempo)
        
        # Left hand part (bass clef)
        left_part = stream.Part()
        left_part.partName = "Piano"
        left_part.insert(0, instrument.Piano())
        left_part.insert(0, clef.BassClef())
        left_part.insert(0, self._parse_time_signature(metadata.time_signature))
        if key_sig:
            left_part.insert(0, self._parse_key_signature(
                metadata.key_signature or (chords.key if chords else None) or "C"
            ))
        
        # Add left hand notes or chord voicings
        if left_hand_notes:
            self._add_aligned_notes(
                left_part, 
                left_hand_notes, 
                metadata.tempo, 
                quarter_notes_per_measure,
                num_measures
            )
        elif chords and chords.chords:
            self._add_aligned_chord_voicings(
                left_part, 
                chords.chords, 
                metadata.tempo, 
                quarter_notes_per_measure,
                num_measures
            )
        else:
            # Fill with rests to match right hand
            self._fill_with_rests(left_part, quarter_notes_per_measure, num_measures)
        
        # Add parts to score
        score.append(right_part)
        score.append(left_part)
        
        # Create staff group for grand staff appearance
        try:
            staff_group = layout.StaffGroup(
                [right_part, left_part],
                symbol='brace',
                barTogether=True,
            )
            score.insert(0, staff_group)
        except Exception:
            pass
        
        return score
    
    def _snap_to_grid(self, value: float, grid_size: float = 0.5) -> float:
        """Snap a value to the nearest grid point.
        
        Default grid is half-beat (0.5) for cleaner notation.
        """
        return round(value / grid_size) * grid_size
    
    def _add_aligned_notes(
        self,
        part: stream.Part,
        notes: List[DetectedNote],
        bpm: int,
        quarter_notes_per_measure: float,
        num_measures: int,
    ):
        """Add notes with proper beat grid alignment.
        
        Uses half-beat grid (eighth notes) for cleaner, more readable notation.
        """
        if not notes:
            self._fill_with_rests(part, quarter_notes_per_measure, num_measures)
            return
        
        seconds_per_beat = 60.0 / bpm
        total_duration = quarter_notes_per_measure * num_measures
        
        # Convert notes to (offset, duration, pitch, velocity) with grid snapping
        aligned_notes = []
        for n in notes:
            offset = n.start_time / seconds_per_beat
            dur = n.duration / seconds_per_beat
            
            # Snap offset to half-beat grid (eighth notes) for cleaner notation
            offset = self._snap_to_grid(offset, 0.5)
            
            # Quantize duration to simple values
            dur = self._quantize_duration(dur)
            
            # Ensure note fits within total duration
            if offset >= total_duration:
                continue
            if offset + dur > total_duration:
                dur = total_duration - offset
                dur = self._quantize_duration(dur)
            
            aligned_notes.append((offset, dur, n.pitch, n.velocity))
        
        # Sort by offset
        aligned_notes.sort(key=lambda x: x[0])
        
        # Merge very close notes (within half beat) - pick the louder one
        merged_notes = []
        for note_data in aligned_notes:
            if merged_notes and abs(note_data[0] - merged_notes[-1][0]) < 0.5:
                # Same position - keep the louder note or merge as chord
                if note_data[3] > merged_notes[-1][3]:
                    merged_notes[-1] = note_data
            else:
                merged_notes.append(note_data)
        
        # Build the part
        current_offset = 0.0
        
        for offset, dur, pitch, velocity in merged_notes:
            # Add rest if there's a gap
            gap = offset - current_offset
            if gap >= 0.5:  # At least an eighth note gap
                self._add_quantized_rest(part, gap)
                current_offset = offset
            elif gap > 0:
                # Small gap - adjust to grid
                current_offset = offset
            
            # Add the note
            n = note.Note(pitch)
            n.quarterLength = dur
            n.volume.velocity = min(127, max(1, velocity))
            part.append(n)
            current_offset += dur
        
        # Fill remaining time with rests
        remaining = total_duration - current_offset
        if remaining >= 0.25:
            self._add_quantized_rest(part, remaining)
    
    def _add_quantized_rest(self, part: stream.Part, duration: float):
        """Add rests that sum to the given duration using standard note values.
        
        Uses only common rest values (minimum eighth note) for readability.
        """
        remaining = duration
        
        while remaining >= 0.5:  # Minimum eighth note rest
            # Find largest standard duration that fits
            for std_dur in QUANTIZE_GRID:
                if std_dur <= remaining + 0.0001:  # Small tolerance
                    r = note.Rest(quarterLength=std_dur)
                    part.append(r)
                    remaining -= std_dur
                    break
            else:
                # Fallback: use eighth note
                r = note.Rest(quarterLength=0.5)
                part.append(r)
                remaining -= 0.5
        
        # Ignore very small remainders (less than eighth note)
    
    def _fill_with_rests(
        self,
        part: stream.Part,
        quarter_notes_per_measure: float,
        num_measures: int,
    ):
        """Fill part with whole measure rests."""
        for _ in range(num_measures):
            r = note.Rest(quarterLength=quarter_notes_per_measure)
            part.append(r)
    
    def _add_aligned_chord_voicings(
        self,
        part: stream.Part,
        chords: List[DetectedChord],
        bpm: int,
        quarter_notes_per_measure: float,
        num_measures: int,
    ):
        """Add chord voicings with proper beat alignment."""
        if not chords:
            self._fill_with_rests(part, quarter_notes_per_measure, num_measures)
            return
        
        seconds_per_beat = 60.0 / bpm
        total_duration = quarter_notes_per_measure * num_measures
        
        current_offset = 0.0
        
        for chord_obj in chords:
            chord_offset = chord_obj.timestamp / seconds_per_beat
            chord_dur = chord_obj.duration / seconds_per_beat
            
            # Snap to beat grid (half note for bass typically)
            chord_offset = self._snap_to_grid(chord_offset, 0.5)
            chord_dur = max(1.0, self._quantize_duration(chord_dur))  # Min quarter note
            
            if chord_offset >= total_duration:
                continue
            
            # Add rest if there's a gap
            gap = chord_offset - current_offset
            if gap >= 0.5:
                self._add_quantized_rest(part, gap)
                current_offset = chord_offset
            
            # Ensure chord fits
            if current_offset + chord_dur > total_duration:
                chord_dur = total_duration - current_offset
                chord_dur = max(0.5, self._quantize_duration(chord_dur))
            
            # Get bass voicing
            root_midi = chord_obj.root_midi - 12  # One octave lower
            pitches = self._get_bass_voicing(chord_obj, root_midi)
            
            if pitches:
                c = m21_chord.Chord(pitches)
                c.quarterLength = chord_dur
                part.append(c)
            else:
                n = note.Note(max(36, chord_obj.root_midi - 12))
                n.quarterLength = chord_dur
                part.append(n)
            
            current_offset += chord_dur
        
        # Fill remaining
        remaining = total_duration - current_offset
        if remaining >= 0.5:
            self._add_quantized_rest(part, remaining)
    
    def _add_bass_chord_voicings(
        self,
        part: stream.Part,
        chords: List[DetectedChord],
        bpm: int,
    ):
        """Add bass chord voicings for left hand piano part with alignment."""
        seconds_per_beat = 60.0 / bpm
        current_offset = 0.0
        
        for chord_obj in chords:
            chord_offset = chord_obj.timestamp / seconds_per_beat
            chord_offset = self._snap_to_grid(chord_offset, 0.5)  # Snap to half beat
            
            # Add rest if there's a gap
            gap = chord_offset - current_offset
            if gap >= 0.5:
                self._add_quantized_rest(part, gap)
                current_offset = chord_offset
            
            # Get bass note and chord tones for left hand (lower octave)
            root_midi = chord_obj.root_midi - 12  # One octave lower
            pitches = self._get_bass_voicing(chord_obj, root_midi)
            
            dur = chord_obj.duration / seconds_per_beat
            dur = max(1.0, self._quantize_duration(dur))  # Min quarter note
            
            if pitches:
                c = m21_chord.Chord(pitches)
                c.quarterLength = dur
                part.append(c)
            else:
                n = note.Note(max(36, root_midi))
                n.quarterLength = dur
                part.append(n)
            
            current_offset += dur
    
    def _get_bass_voicing(self, chord_obj: DetectedChord, root_midi: int) -> List[int]:
        """Get bass voicing pitches for left hand."""
        # Keep in reasonable bass range (MIDI 36-60)
        root = max(36, min(48, root_midi))
        
        # Simple bass voicing: root + fifth
        fifth = root + 7
        
        # For seventh chords, add the seventh
        if chord_obj.quality in [ChordQuality.DOMINANT_7, ChordQuality.MAJOR_7, 
                                  ChordQuality.MINOR_7, ChordQuality.DIMINISHED_7]:
            if chord_obj.quality == ChordQuality.MAJOR_7:
                seventh = root + 11
            elif chord_obj.quality == ChordQuality.MINOR_7:
                seventh = root + 10
            else:
                seventh = root + 10
            return [root, fifth, seventh]
        
        return [root, fifth]
    
    def _add_melody_notes(
        self, 
        part: stream.Part, 
        notes: list[DetectedNote],
        bpm: int,
    ):
        """Add melody notes to a part with proper grid alignment.
        
        Uses half-beat grid for cleaner, more readable notation.
        """
        if not notes:
            return
        
        seconds_per_beat = 60.0 / bpm
        
        # Convert and align notes
        aligned_notes = []
        for n in notes:
            offset = n.start_time / seconds_per_beat
            dur = n.duration / seconds_per_beat
            
            # Snap offset to half-beat grid (eighth notes)
            offset = self._snap_to_grid(offset, 0.5)
            dur = self._quantize_duration(dur)
            
            aligned_notes.append((offset, dur, n.pitch, n.velocity))
        
        # Sort by offset
        aligned_notes.sort(key=lambda x: x[0])
        
        # Merge very close notes
        merged_notes = []
        for note_data in aligned_notes:
            if merged_notes and abs(note_data[0] - merged_notes[-1][0]) < 0.5:
                if note_data[3] > merged_notes[-1][3]:
                    merged_notes[-1] = note_data
            else:
                merged_notes.append(note_data)
        
        current_offset = 0.0
        
        for offset, dur, pitch, velocity in merged_notes:
            # Add rest if there's a gap
            gap = offset - current_offset
            if gap >= 0.5:
                self._add_quantized_rest(part, gap)
                current_offset = offset
            
            # Create note
            n = note.Note(pitch)
            n.quarterLength = dur
            n.volume.velocity = min(127, max(1, velocity))
            
            part.append(n)
            current_offset += dur
    
    def _add_chord_symbols(
        self, 
        part: stream.Part, 
        chords: list[DetectedChord],
        beats_per_measure: int,
    ):
        """Add chord symbols as rhythm slashes or whole note chord symbols."""
        for chord in chords:
            # Create chord symbol
            cs = harmony.ChordSymbol(chord.symbol)
            cs.quarterLength = max(1.0, self._quantize_duration(chord.duration))
            part.append(cs)
    
    def _add_chord_symbols_to_part(
        self,
        part: stream.Part,
        chords: list[DetectedChord],
        bpm: int,
    ):
        """Add chord symbols above existing melody."""
        seconds_per_beat = 60.0 / bpm
        
        for chord in chords:
            offset = chord.timestamp / seconds_per_beat
            # Quantize offset to nearest beat subdivision
            offset = self._quantize_offset(offset)
            cs = harmony.ChordSymbol(chord.symbol)
            part.insert(offset, cs)
    
    def _quantize_offset(self, offset: float) -> float:
        """Quantize offset to nearest eighth note position."""
        # Round to nearest 0.5 (eighth note)
        return round(offset * 2) / 2
    
    def _add_chord_voicings(
        self,
        part: stream.Part,
        chords: list[DetectedChord],
        bpm: int,
    ):
        """Add chord voicings as actual notes."""
        seconds_per_beat = 60.0 / bpm
        
        for chord in chords:
            pitches = self._get_chord_pitches(chord)
            duration = chord.duration / seconds_per_beat
            duration = self._quantize_duration(duration)
            
            if pitches:
                c = m21_chord.Chord(pitches)
                c.quarterLength = duration
                part.append(c)
            else:
                # Fallback: create from chord symbol
                cs = harmony.ChordSymbol(chord.symbol)
                cs.quarterLength = duration
                part.append(cs)
    
    def _get_chord_pitches(self, chord: DetectedChord) -> list[int]:
        """Get MIDI pitches for a chord voicing."""
        root_midi = chord.root_midi
        
        # Interval patterns for different chord qualities
        intervals = {
            ChordQuality.MAJOR: [0, 4, 7],
            ChordQuality.MINOR: [0, 3, 7],
            ChordQuality.DIMINISHED: [0, 3, 6],
            ChordQuality.AUGMENTED: [0, 4, 8],
            ChordQuality.DOMINANT_7: [0, 4, 7, 10],
            ChordQuality.MAJOR_7: [0, 4, 7, 11],
            ChordQuality.MINOR_7: [0, 3, 7, 10],
            ChordQuality.DIMINISHED_7: [0, 3, 6, 9],
            ChordQuality.HALF_DIMINISHED_7: [0, 3, 6, 10],
            ChordQuality.SUSPENDED_2: [0, 2, 7],
            ChordQuality.SUSPENDED_4: [0, 5, 7],
            ChordQuality.ADD_9: [0, 4, 7, 14],
        }
        
        chord_intervals = intervals.get(chord.quality, [0, 4, 7])
        pitches = [root_midi + i for i in chord_intervals]
        
        # Add bass note if different from root
        if chord.bass_note:
            bass_map = {
                "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
                "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, 
                "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
            }
            bass_pitch = 48 + bass_map.get(chord.bass_note, 0)  # Octave 3
            pitches.insert(0, bass_pitch)
        
        return pitches
    
    def _create_metadata(self, metadata: SheetMetadata):
        """Create music21 metadata object."""
        from music21 import metadata as m21_metadata
        md = m21_metadata.Metadata()
        md.title = metadata.title
        if metadata.composer:
            md.composer = metadata.composer
        return md
    
    def _get_instrument(self, inst: Instrument):
        """Get music21 instrument object."""
        if inst == Instrument.GUITAR:
            return instrument.AcousticGuitar()
        elif inst == Instrument.VOCAL:
            return instrument.Vocalist()
        else:
            return instrument.Piano()
    
    def _parse_time_signature(self, ts_string: str) -> meter.TimeSignature:
        """Parse time signature string to music21 object."""
        try:
            return meter.TimeSignature(ts_string)
        except Exception:
            return meter.TimeSignature("4/4")
    
    def _parse_key_signature(self, key_string: str) -> Optional[m21_key.Key]:
        """Parse key signature string to music21 object."""
        try:
            key_string = key_string.strip()
            
            # Handle formats like "C major", "Am", "A minor"
            if " major" in key_string.lower():
                root = key_string.lower().replace(" major", "").strip().upper()
                return m21_key.Key(root, "major")
            elif " minor" in key_string.lower():
                root = key_string.lower().replace(" minor", "").strip().upper()
                return m21_key.Key(root, "minor")
            elif key_string.endswith("m") and len(key_string) <= 3:
                root = key_string[:-1].upper()
                return m21_key.Key(root, "minor")
            else:
                return m21_key.Key(key_string.upper())
        except Exception:
            return None
    
    def _quantize_duration(self, duration: float) -> float:
        """Quantize duration to nearest common musical value.
        
        Uses only "normal" note values (no 32nd/64th notes) for readability.
        Prioritizes simpler values over accuracy.
        """
        # Only use common, readable note values
        # No 16th, 32nd, or 64th notes - keep it simple
        valid_durations = [
            4.0,    # whole
            3.0,    # dotted half
            2.0,    # half
            1.5,    # dotted quarter
            1.0,    # quarter
            0.75,   # dotted eighth
            0.5,    # eighth
        ]
        
        # Ensure duration is positive
        duration = abs(duration)
        
        # For very short notes, round up to eighth note
        if duration < 0.5:
            return 0.5
        
        # For notes close to standard values, snap to them
        # Prefer rounding up to larger values for cleaner notation
        for std_dur in valid_durations:
            if abs(duration - std_dur) < 0.25:
                return std_dur
        
        # Find closest standard duration
        closest = min(valid_durations, key=lambda x: abs(x - duration))
        return max(0.5, closest)  # Minimum eighth note
    
    def _export_to_musicxml(self, score: stream.Score) -> str:
        """Export score to MusicXML string with proper formatting."""
        from music21.musicxml import m21ToXml
        
        # Quantize all elements to standard durations
        # Use only 2 (8th notes) for cleaner notation - no 16ths/32nds
        try:
            score = score.quantize(
                quarterLengthDivisors=[2],  # Only 8th notes for cleaner look
                processOffsets=True,
                processDurations=True,
            )
        except Exception as e:
            logger.warning(f"Quantize failed: {e}")
        
        # Make notation to organize into measures and fix issues
        try:
            score = score.makeNotation(
                inPlace=False,
                cautionaryNotImmediateRepeat=False,
            )
        except Exception as e:
            logger.warning(f"makeNotation failed: {e}")
        
        # Ensure all parts have proper measure alignment
        try:
            for part in score.parts:
                # Make sure measures are properly defined
                if not part.hasMeasures():
                    part.makeMeasures(inPlace=True)
        except Exception as e:
            logger.warning(f"makeMeasures failed: {e}")
        
        exporter = m21ToXml.GeneralObjectExporter(score)
        xml_bytes = exporter.parse()
        
        if isinstance(xml_bytes, bytes):
            return xml_bytes.decode("utf-8")
        return str(xml_bytes)
