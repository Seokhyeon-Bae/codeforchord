"""Sheet music generation using music21 for MusicXML output."""

import logging
from typing import Optional
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
        """Generate a full score with separate melody and chord parts."""
        score = stream.Score()
        score.metadata = self._create_metadata(metadata)
        
        # Melody part
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
        
        # Chord/accompaniment part
        chord_part = stream.Part()
        chord_part.partName = "Accompaniment"
        chord_part.insert(0, instrument.Piano())
        
        chord_part.append(self._parse_time_signature(metadata.time_signature))
        
        if chords and chords.chords:
            self._add_chord_voicings(chord_part, chords.chords, metadata.tempo)
        else:
            chord_part.append(note.Rest(quarterLength=4))
        
        score.append(chord_part)
        
        return score
    
    def _add_melody_notes(
        self, 
        part: stream.Part, 
        notes: list[DetectedNote],
        bpm: int,
    ):
        """Add melody notes to a part."""
        if not notes:
            return
        
        # Convert time to quarter note lengths
        seconds_per_beat = 60.0 / bpm
        
        current_offset = 0.0
        
        for detected_note in notes:
            # Calculate offset from start
            note_offset = detected_note.start_time / seconds_per_beat
            
            # Add rest if there's a gap
            gap = note_offset - current_offset
            if gap > 0.125:  # Minimum gap to add rest
                rest_duration = self._quantize_duration(gap)
                r = note.Rest(quarterLength=rest_duration)
                part.append(r)
                current_offset += rest_duration
            
            # Calculate note duration
            duration = detected_note.duration / seconds_per_beat
            duration = self._quantize_duration(duration)
            
            # Ensure minimum duration
            if duration < 0.125:
                duration = 0.125
            
            # Create note
            n = note.Note(detected_note.pitch)
            n.quarterLength = duration
            
            # Set velocity as dynamics
            n.volume.velocity = min(127, max(1, detected_note.velocity))
            
            part.append(n)
            current_offset += duration
    
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
        """Quantize duration to nearest expressible musical value."""
        # Only use standard note values that MusicXML can express
        # These are all expressible: whole, half, quarter, eighth, sixteenth, 32nd
        # Plus dotted versions (multiply by 1.5)
        valid_durations = [
            4.0,    # whole
            3.0,    # dotted half
            2.0,    # half
            1.5,    # dotted quarter
            1.0,    # quarter
            0.75,   # dotted eighth
            0.5,    # eighth
            0.25,   # sixteenth
            0.125,  # 32nd
        ]
        
        # Ensure duration is positive
        duration = abs(duration)
        
        # Find closest standard duration
        closest = min(valid_durations, key=lambda x: abs(x - duration))
        return max(0.125, closest)  # Minimum 32nd note
    
    def _export_to_musicxml(self, score: stream.Score) -> str:
        """Export score to MusicXML string."""
        from music21.musicxml import m21ToXml
        
        # Quantize all elements to standard durations
        try:
            score = score.quantize(
                quarterLengthDivisors=[4, 3],  # Allow 16th notes and triplets
                processOffsets=True,
                processDurations=True,
            )
        except Exception:
            pass
        
        # Make notation to fix any duration/measure issues
        try:
            score = score.makeNotation()
        except Exception:
            pass  # Continue even if makeNotation fails
        
        exporter = m21ToXml.GeneralObjectExporter(score)
        xml_bytes = exporter.parse()
        
        if isinstance(xml_bytes, bytes):
            return xml_bytes.decode("utf-8")
        return str(xml_bytes)
