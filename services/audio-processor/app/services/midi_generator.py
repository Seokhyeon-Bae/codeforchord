"""MIDI file generation using midiutil."""

import io
import base64
from typing import Optional

from midiutil import MIDIFile

from app.models.note import DetectedNote, NoteList
from app.models.chord import DetectedChord, ChordList, ChordQuality
from app.models.sheet import (
    SheetMetadata, 
    GeneratedSheet, 
    OutputFormat, 
    OutputType,
    Instrument,
)
from app.core.constants import MIDI_DEFAULT_VELOCITY


class MidiGenerator:
    """Generate MIDI files from detected notes and chords."""
    
    # General MIDI program numbers
    INSTRUMENT_PROGRAMS = {
        Instrument.PIANO: 0,       # Acoustic Grand Piano
        Instrument.GUITAR: 25,     # Acoustic Guitar (steel)
        Instrument.VOCAL: 52,      # Choir Aahs
    }
    
    def __init__(self):
        self.ticks_per_beat = 480
    
    def generate(
        self,
        notes: Optional[NoteList] = None,
        chords: Optional[ChordList] = None,
        output_type: OutputType = OutputType.LEAD_SHEET,
        metadata: Optional[SheetMetadata] = None,
    ) -> GeneratedSheet:
        """
        Generate MIDI from notes and/or chords.
        
        Args:
            notes: Detected notes (melody)
            chords: Detected chords
            output_type: Type of output
            metadata: Sheet metadata
            
        Returns:
            GeneratedSheet with base64-encoded MIDI content
        """
        metadata = metadata or SheetMetadata()
        
        if output_type == OutputType.CHORDS_ONLY:
            midi = self._generate_chords_only(chords, metadata)
        elif output_type == OutputType.LEAD_SHEET:
            midi = self._generate_lead_sheet(notes, chords, metadata)
        else:
            midi = self._generate_full(notes, chords, metadata)
        
        # Export to bytes and encode as base64
        midi_bytes = self._export_to_bytes(midi)
        midi_base64 = base64.b64encode(midi_bytes).decode("utf-8")
        
        return GeneratedSheet(
            content=midi_base64,
            format=OutputFormat.MIDI,
            output_type=output_type,
            metadata=metadata,
            filename=metadata.title.replace(" ", "_").lower() if metadata.title else "output",
        )
    
    def generate_bytes(
        self,
        notes: Optional[NoteList] = None,
        chords: Optional[ChordList] = None,
        output_type: OutputType = OutputType.LEAD_SHEET,
        metadata: Optional[SheetMetadata] = None,
    ) -> bytes:
        """Generate MIDI and return raw bytes."""
        metadata = metadata or SheetMetadata()
        
        if output_type == OutputType.CHORDS_ONLY:
            midi = self._generate_chords_only(chords, metadata)
        elif output_type == OutputType.LEAD_SHEET:
            midi = self._generate_lead_sheet(notes, chords, metadata)
        else:
            midi = self._generate_full(notes, chords, metadata)
        
        return self._export_to_bytes(midi)
    
    def _generate_chords_only(
        self, 
        chords: Optional[ChordList], 
        metadata: SheetMetadata
    ) -> MIDIFile:
        """Generate MIDI with chord voicings only."""
        midi = MIDIFile(1, deinterleave=False)
        track = 0
        channel = 0
        
        midi.addTempo(track, 0, metadata.tempo)
        midi.addProgramChange(track, channel, 0, self.INSTRUMENT_PROGRAMS.get(metadata.instrument, 0))
        
        if chords and chords.chords:
            self._add_chord_track(midi, track, channel, chords.chords, metadata.tempo)
        
        return midi
    
    def _generate_lead_sheet(
        self,
        notes: Optional[NoteList],
        chords: Optional[ChordList],
        metadata: SheetMetadata,
    ) -> MIDIFile:
        """Generate MIDI with melody and optional chord accompaniment."""
        # Two tracks: melody and chords
        num_tracks = 2 if (chords and chords.chords) else 1
        midi = MIDIFile(num_tracks, deinterleave=False)
        
        # Track 0: Melody
        melody_track = 0
        melody_channel = 0
        midi.addTempo(melody_track, 0, metadata.tempo)
        midi.addProgramChange(
            melody_track, melody_channel, 0, 
            self.INSTRUMENT_PROGRAMS.get(metadata.instrument, 0)
        )
        midi.addTrackName(melody_track, 0, "Melody")
        
        if notes and notes.notes:
            self._add_melody_track(midi, melody_track, melody_channel, notes.notes, metadata.tempo)
        
        # Track 1: Chords (if present)
        if num_tracks > 1 and chords and chords.chords:
            chord_track = 1
            chord_channel = 1
            midi.addTempo(chord_track, 0, metadata.tempo)
            midi.addProgramChange(chord_track, chord_channel, 0, 0)  # Piano for chords
            midi.addTrackName(chord_track, 0, "Chords")
            self._add_chord_track(midi, chord_track, chord_channel, chords.chords, metadata.tempo, velocity=60)
        
        return midi
    
    def _generate_full(
        self,
        notes: Optional[NoteList],
        chords: Optional[ChordList],
        metadata: SheetMetadata,
    ) -> MIDIFile:
        """Generate full MIDI with melody and chord parts."""
        return self._generate_lead_sheet(notes, chords, metadata)
    
    def _add_melody_track(
        self,
        midi: MIDIFile,
        track: int,
        channel: int,
        notes: list[DetectedNote],
        bpm: int,
        velocity: int = MIDI_DEFAULT_VELOCITY,
    ):
        """Add melody notes to a MIDI track."""
        seconds_per_beat = 60.0 / bpm
        
        for detected_note in notes:
            # Convert time to beats
            time = detected_note.start_time / seconds_per_beat
            duration = detected_note.duration / seconds_per_beat
            
            # Ensure minimum duration
            duration = max(0.125, duration)
            
            # Use note's velocity or default
            note_velocity = detected_note.velocity if detected_note.velocity > 0 else velocity
            
            midi.addNote(
                track=track,
                channel=channel,
                pitch=detected_note.pitch,
                time=time,
                duration=duration,
                volume=note_velocity,
            )
    
    def _add_chord_track(
        self,
        midi: MIDIFile,
        track: int,
        channel: int,
        chords: list[DetectedChord],
        bpm: int,
        velocity: int = 70,
    ):
        """Add chord voicings to a MIDI track."""
        seconds_per_beat = 60.0 / bpm
        
        for chord in chords:
            time = chord.timestamp / seconds_per_beat
            duration = chord.duration / seconds_per_beat
            duration = max(0.5, duration)  # Minimum half beat for chords
            
            pitches = self._get_chord_pitches(chord)
            
            for pitch in pitches:
                midi.addNote(
                    track=track,
                    channel=channel,
                    pitch=pitch,
                    time=time,
                    duration=duration,
                    volume=velocity,
                )
    
    def _get_chord_pitches(self, chord: DetectedChord, base_octave: int = 4) -> list[int]:
        """Get MIDI pitches for a chord voicing."""
        # Get root pitch in the specified octave
        note_map = {
            "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
            "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
        }
        
        root_pc = note_map.get(chord.root, 0)
        root_midi = (base_octave + 1) * 12 + root_pc  # Octave 4 = MIDI 60 for C
        
        # Interval patterns
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
            ChordQuality.UNKNOWN: [0, 4, 7],
        }
        
        chord_intervals = intervals.get(chord.quality, [0, 4, 7])
        pitches = [root_midi + i for i in chord_intervals]
        
        # Add bass note if present (one octave lower)
        if chord.bass_note and chord.bass_note != chord.root:
            bass_pc = note_map.get(chord.bass_note, 0)
            bass_midi = (base_octave) * 12 + bass_pc  # One octave lower
            if bass_midi not in pitches:
                pitches.insert(0, bass_midi)
        
        return pitches
    
    def notes_to_midi(
        self,
        notes: list[DetectedNote],
        bpm: int = 120,
        instrument: Instrument = Instrument.PIANO,
    ) -> bytes:
        """Convert a list of notes directly to MIDI bytes."""
        midi = MIDIFile(1, deinterleave=False)
        track = 0
        channel = 0
        
        midi.addTempo(track, 0, bpm)
        midi.addProgramChange(track, channel, 0, self.INSTRUMENT_PROGRAMS.get(instrument, 0))
        
        self._add_melody_track(midi, track, channel, notes, bpm)
        
        return self._export_to_bytes(midi)
    
    def chords_to_midi(
        self,
        chords: list[DetectedChord],
        bpm: int = 120,
    ) -> bytes:
        """Convert a list of chords directly to MIDI bytes."""
        midi = MIDIFile(1, deinterleave=False)
        track = 0
        channel = 0
        
        midi.addTempo(track, 0, bpm)
        midi.addProgramChange(track, channel, 0, 0)  # Piano
        
        self._add_chord_track(midi, track, channel, chords, bpm)
        
        return self._export_to_bytes(midi)
    
    def _export_to_bytes(self, midi: MIDIFile) -> bytes:
        """Export MIDIFile to bytes."""
        buffer = io.BytesIO()
        midi.writeFile(buffer)
        buffer.seek(0)
        return buffer.read()
