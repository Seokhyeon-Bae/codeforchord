"""Tests for data models."""

import pytest
from app.models.note import DetectedNote, NoteList
from app.models.chord import DetectedChord, ChordList, ChordQuality


class TestDetectedNote:
    """Tests for DetectedNote model."""
    
    def test_create_note(self):
        """Test basic note creation."""
        note = DetectedNote(
            pitch=60,
            start_time=0.0,
            end_time=1.0,
            velocity=80,
            confidence=0.9,
        )
        assert note.pitch == 60
        assert note.duration == 1.0
        assert note.note_name == "C4"
    
    def test_note_name_calculation(self):
        """Test note name calculation for various pitches."""
        test_cases = [
            (60, "C4"),
            (61, "C#4"),
            (69, "A4"),
            (72, "C5"),
            (48, "C3"),
        ]
        for pitch, expected_name in test_cases:
            note = DetectedNote(pitch=pitch, start_time=0, end_time=1)
            assert note.note_name == expected_name
    
    def test_transpose(self):
        """Test note transposition."""
        note = DetectedNote(pitch=60, start_time=0, end_time=1)
        transposed = note.transpose(5)
        assert transposed.pitch == 65
        
        # Test boundary
        high_note = DetectedNote(pitch=125, start_time=0, end_time=1)
        transposed_high = high_note.transpose(5)
        assert transposed_high.pitch == 127  # Clamped to max


class TestDetectedChord:
    """Tests for DetectedChord model."""
    
    def test_create_chord(self):
        """Test basic chord creation."""
        chord = DetectedChord(
            symbol="Cmaj7",
            root="C",
            quality=ChordQuality.MAJOR_7,
            timestamp=0.0,
            duration=2.0,
        )
        assert chord.symbol == "Cmaj7"
        assert chord.root == "C"
        assert chord.end_time == 2.0
    
    def test_transpose_chord(self):
        """Test chord transposition."""
        chord = DetectedChord(
            symbol="C",
            root="C",
            quality=ChordQuality.MAJOR,
            timestamp=0.0,
            duration=1.0,
        )
        transposed = chord.transpose(2)
        assert transposed.root == "D"
        assert transposed.symbol == "D"
    
    def test_to_minor(self):
        """Test major to minor conversion."""
        major = DetectedChord(
            symbol="C",
            root="C",
            quality=ChordQuality.MAJOR,
            timestamp=0.0,
            duration=1.0,
        )
        minor = major.to_minor()
        assert minor.quality == ChordQuality.MINOR
        assert minor.symbol == "Cm"
    
    def test_to_major(self):
        """Test minor to major conversion."""
        minor = DetectedChord(
            symbol="Am",
            root="A",
            quality=ChordQuality.MINOR,
            timestamp=0.0,
            duration=1.0,
        )
        major = minor.to_major()
        assert major.quality == ChordQuality.MAJOR
        assert major.symbol == "A"
    
    def test_diminish(self):
        """Test chord diminishing."""
        chord = DetectedChord(
            symbol="C",
            root="C",
            quality=ChordQuality.MAJOR,
            timestamp=0.0,
            duration=1.0,
        )
        diminished = chord.diminish()
        assert diminished.quality == ChordQuality.DIMINISHED
        assert diminished.symbol == "Cdim"
    
    def test_augment(self):
        """Test chord augmentation."""
        chord = DetectedChord(
            symbol="C",
            root="C",
            quality=ChordQuality.MAJOR,
            timestamp=0.0,
            duration=1.0,
        )
        augmented = chord.augment()
        assert augmented.quality == ChordQuality.AUGMENTED
        assert augmented.symbol == "Caug"


class TestNoteList:
    """Tests for NoteList collection."""
    
    def test_filter_by_confidence(self):
        """Test confidence filtering."""
        notes = NoteList(notes=[
            DetectedNote(pitch=60, start_time=0, end_time=1, confidence=0.9),
            DetectedNote(pitch=62, start_time=1, end_time=2, confidence=0.3),
            DetectedNote(pitch=64, start_time=2, end_time=3, confidence=0.7),
        ])
        
        filtered = notes.filter_by_confidence(0.5)
        assert len(filtered.notes) == 2
        assert all(n.confidence >= 0.5 for n in filtered.notes)
    
    def test_transpose_all(self):
        """Test transposing all notes."""
        notes = NoteList(notes=[
            DetectedNote(pitch=60, start_time=0, end_time=1),
            DetectedNote(pitch=64, start_time=1, end_time=2),
        ])
        
        transposed = notes.transpose_all(3)
        assert transposed.notes[0].pitch == 63
        assert transposed.notes[1].pitch == 67


class TestChordList:
    """Tests for ChordList collection."""
    
    def test_transpose_all(self):
        """Test transposing all chords."""
        chords = ChordList(chords=[
            DetectedChord(symbol="C", root="C", quality=ChordQuality.MAJOR, timestamp=0, duration=1),
            DetectedChord(symbol="G", root="G", quality=ChordQuality.MAJOR, timestamp=1, duration=1),
        ])
        
        transposed = chords.transpose_all(2)
        assert transposed.chords[0].root == "D"
        assert transposed.chords[1].root == "A"
    
    def test_to_minor_all(self):
        """Test converting all to minor."""
        chords = ChordList(chords=[
            DetectedChord(symbol="C", root="C", quality=ChordQuality.MAJOR, timestamp=0, duration=1),
            DetectedChord(symbol="Am", root="A", quality=ChordQuality.MINOR, timestamp=1, duration=1),
        ])
        
        minor = chords.to_minor_all()
        assert minor.chords[0].quality == ChordQuality.MINOR
        assert minor.chords[1].quality == ChordQuality.MINOR  # Already minor
