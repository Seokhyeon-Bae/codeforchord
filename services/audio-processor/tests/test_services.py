"""Tests for service classes."""

import pytest
from app.models.chord import DetectedChord, ChordList, ChordQuality
from app.models.sheet import Instrument, MelodyStyle, MelodyOptions
from app.services.arranger import Arranger
from app.services.melody_suggester import MelodySuggester


class TestArranger:
    """Tests for Arranger service."""
    
    @pytest.fixture
    def arranger(self):
        return Arranger()
    
    @pytest.fixture
    def sample_chords(self):
        return ChordList(chords=[
            DetectedChord(symbol="C", root="C", quality=ChordQuality.MAJOR, timestamp=0, duration=2),
            DetectedChord(symbol="Am", root="A", quality=ChordQuality.MINOR, timestamp=2, duration=2),
            DetectedChord(symbol="F", root="F", quality=ChordQuality.MAJOR, timestamp=4, duration=2),
            DetectedChord(symbol="G", root="G", quality=ChordQuality.MAJOR, timestamp=6, duration=2),
        ], key="C major")
    
    def test_transpose(self, arranger, sample_chords):
        """Test transposition."""
        _, transposed = arranger.transpose(None, sample_chords, 2)
        
        assert transposed.chords[0].root == "D"
        assert transposed.chords[1].root == "B"
        assert transposed.chords[2].root == "G"
        assert transposed.chords[3].root == "A"
    
    def test_to_minor(self, arranger, sample_chords):
        """Test major to minor conversion."""
        converted = arranger.to_minor(sample_chords)
        
        # C -> Cm
        assert converted.chords[0].quality == ChordQuality.MINOR
        # Am stays Am
        assert converted.chords[1].quality == ChordQuality.MINOR
        # F -> Fm
        assert converted.chords[2].quality == ChordQuality.MINOR
    
    def test_simplify_chords(self, arranger):
        """Test chord simplification."""
        complex_chords = ChordList(chords=[
            DetectedChord(symbol="Cmaj7", root="C", quality=ChordQuality.MAJOR_7, timestamp=0, duration=2),
            DetectedChord(symbol="Am7", root="A", quality=ChordQuality.MINOR_7, timestamp=2, duration=2),
            DetectedChord(symbol="Dm7", root="D", quality=ChordQuality.MINOR_7, timestamp=4, duration=2),
        ])
        
        simplified = arranger.simplify_chords(complex_chords, Instrument.GUITAR)
        
        assert simplified.chords[0].quality == ChordQuality.MAJOR
        assert simplified.chords[1].quality == ChordQuality.MINOR
        assert simplified.chords[2].quality == ChordQuality.MINOR
    
    def test_jazzify_chords(self, arranger, sample_chords):
        """Test adding jazz extensions."""
        jazzified = arranger.jazzify_chords(sample_chords)
        
        # C -> Cmaj7
        assert jazzified.chords[0].quality == ChordQuality.MAJOR_7
        # Am -> Am7
        assert jazzified.chords[1].quality == ChordQuality.MINOR_7


class TestMelodySuggester:
    """Tests for MelodySuggester service."""
    
    @pytest.fixture
    def suggester(self):
        return MelodySuggester(seed=42)  # Fixed seed for reproducibility
    
    @pytest.fixture
    def sample_chords(self):
        return ChordList(chords=[
            DetectedChord(symbol="C", root="C", quality=ChordQuality.MAJOR, timestamp=0, duration=2),
            DetectedChord(symbol="Am", root="A", quality=ChordQuality.MINOR, timestamp=2, duration=2),
            DetectedChord(symbol="F", root="F", quality=ChordQuality.MAJOR, timestamp=4, duration=2),
            DetectedChord(symbol="G", root="G", quality=ChordQuality.MAJOR, timestamp=6, duration=2),
        ], duration=8)
    
    def test_suggest_simple(self, suggester, sample_chords):
        """Test simple melody generation."""
        melody = suggester.suggest(sample_chords, bpm=120)
        
        assert len(melody.notes) > 0
        # Notes should be within reasonable range
        for note in melody.notes:
            assert 48 <= note.pitch <= 84
    
    def test_suggest_arpeggiated(self, suggester, sample_chords):
        """Test arpeggiated melody generation."""
        options = MelodyOptions(style=MelodyStyle.ARPEGGIATED)
        melody = suggester.suggest(sample_chords, options, bpm=120)
        
        assert len(melody.notes) > 0
    
    def test_get_chord_tones(self, suggester):
        """Test chord tone extraction."""
        chord = DetectedChord(
            symbol="C",
            root="C",
            quality=ChordQuality.MAJOR,
            timestamp=0,
            duration=1,
        )
        
        tones = suggester._get_chord_tones(chord, octave=4)
        
        # C major: C, E, G
        assert 60 in tones  # C4
        assert 64 in tones  # E4
        assert 67 in tones  # G4
    
    def test_get_chord_scale(self, suggester):
        """Test chord scale generation."""
        chord = DetectedChord(
            symbol="C",
            root="C",
            quality=ChordQuality.MAJOR,
            timestamp=0,
            duration=1,
        )
        
        scale = suggester.get_chord_scale(chord, octave=4)
        
        # C major scale: C, D, E, F, G, A, B
        assert len(scale) == 7
        assert 60 in scale  # C
        assert 62 in scale  # D
        assert 64 in scale  # E


class TestIntegration:
    """Integration tests for service combinations."""
    
    def test_arrange_and_generate_melody(self):
        """Test arranging chords then generating melody."""
        chords = ChordList(chords=[
            DetectedChord(symbol="C", root="C", quality=ChordQuality.MAJOR, timestamp=0, duration=4),
            DetectedChord(symbol="G", root="G", quality=ChordQuality.MAJOR, timestamp=4, duration=4),
        ], duration=8)
        
        # Transpose up 2 semitones
        arranger = Arranger()
        _, transposed = arranger.transpose(None, chords, 2)
        
        # Generate melody
        suggester = MelodySuggester(seed=42)
        melody = suggester.suggest(transposed, bpm=120)
        
        assert len(melody.notes) > 0
        # Check that melody is in the transposed key
        assert transposed.chords[0].root == "D"
