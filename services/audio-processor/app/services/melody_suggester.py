"""Rule-based melody generation from chord progressions."""

import random
from typing import Optional

from app.models.note import DetectedNote, NoteList
from app.models.chord import DetectedChord, ChordList, ChordQuality
from app.models.sheet import MelodyStyle, MelodyOptions
from app.core.constants import MIDI_DEFAULT_VELOCITY


class MelodySuggester:
    """
    Generate melodic suggestions based on chord progressions.
    
    Uses rule-based algorithms to create melodies from:
    - Chord tones (root, 3rd, 5th, 7th)
    - Passing tones (chromatic/diatonic)
    - Neighbor tones (upper/lower)
    """
    
    # Chord quality to intervals mapping
    CHORD_TONES = {
        ChordQuality.MAJOR: [0, 4, 7],           # 1, 3, 5
        ChordQuality.MINOR: [0, 3, 7],           # 1, b3, 5
        ChordQuality.DIMINISHED: [0, 3, 6],      # 1, b3, b5
        ChordQuality.AUGMENTED: [0, 4, 8],       # 1, 3, #5
        ChordQuality.DOMINANT_7: [0, 4, 7, 10],  # 1, 3, 5, b7
        ChordQuality.MAJOR_7: [0, 4, 7, 11],     # 1, 3, 5, 7
        ChordQuality.MINOR_7: [0, 3, 7, 10],     # 1, b3, 5, b7
        ChordQuality.DIMINISHED_7: [0, 3, 6, 9], # 1, b3, b5, bb7
        ChordQuality.HALF_DIMINISHED_7: [0, 3, 6, 10],  # 1, b3, b5, b7
        ChordQuality.SUSPENDED_2: [0, 2, 7],     # 1, 2, 5
        ChordQuality.SUSPENDED_4: [0, 5, 7],     # 1, 4, 5
        ChordQuality.ADD_9: [0, 4, 7, 14],       # 1, 3, 5, 9
        ChordQuality.UNKNOWN: [0, 4, 7],
    }
    
    # Rhythm patterns (quarter note = 1.0)
    RHYTHM_PATTERNS = {
        MelodyStyle.SIMPLE: [
            [1.0, 1.0, 1.0, 1.0],           # Quarter notes
            [2.0, 2.0],                      # Half notes
            [1.0, 1.0, 2.0],                 # Quarter, quarter, half
        ],
        MelodyStyle.ARPEGGIATED: [
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # Eighth notes
            [0.5, 0.5, 1.0, 0.5, 0.5, 1.0],            # Mixed
            [0.25, 0.25, 0.25, 0.25, 0.5, 0.5, 0.5, 0.5, 1.0],  # 16ths to 8ths
        ],
        MelodyStyle.SCALAR: [
            [0.5, 0.5, 0.5, 0.5, 1.0, 1.0],  # Scale runs
            [0.25, 0.25, 0.25, 0.25, 0.5, 0.5, 1.0, 1.0],
        ],
        MelodyStyle.RHYTHMIC: [
            [0.75, 0.25, 1.0, 0.75, 0.25, 1.0],  # Dotted rhythms
            [0.5, 0.25, 0.25, 0.5, 0.5, 1.0, 1.0],  # Syncopation
            [1.5, 0.5, 1.0, 1.0],  # Dotted quarter
        ],
    }
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize melody suggester.
        
        Args:
            seed: Random seed for reproducible melodies
        """
        if seed is not None:
            random.seed(seed)
    
    def suggest(
        self,
        chords: ChordList,
        options: Optional[MelodyOptions] = None,
        bpm: int = 120,
    ) -> NoteList:
        """
        Generate a melody suggestion from chord progression.
        
        Args:
            chords: Chord progression to base melody on
            options: Melody generation options
            bpm: Tempo in BPM (for timing calculations)
            
        Returns:
            NoteList containing suggested melody
        """
        options = options or MelodyOptions()
        
        melody_notes = []
        previous_pitch = None
        
        for chord in chords.chords:
            chord_notes = self._generate_for_chord(
                chord,
                options,
                bpm,
                previous_pitch,
            )
            melody_notes.extend(chord_notes)
            
            if chord_notes:
                previous_pitch = chord_notes[-1].pitch
        
        return NoteList(
            notes=melody_notes,
            source_file=chords.source_file,
            duration=chords.duration,
        )
    
    def _generate_for_chord(
        self,
        chord: DetectedChord,
        options: MelodyOptions,
        bpm: int,
        previous_pitch: Optional[int] = None,
    ) -> list[DetectedNote]:
        """Generate melody notes for a single chord."""
        # Get chord tones
        chord_tones = self._get_chord_tones(chord, options.octave)
        
        # Get rhythm pattern
        pattern = self._get_rhythm_pattern(options.style, chord.duration, bpm)
        
        # Scale pattern by density
        if options.density != 1.0:
            pattern = self._scale_pattern(pattern, options.density)
        
        # Generate notes
        notes = []
        current_time = chord.timestamp
        seconds_per_beat = 60.0 / bpm
        
        for i, duration_beats in enumerate(pattern):
            duration_seconds = duration_beats * seconds_per_beat
            
            # Choose pitch
            if i == 0 and previous_pitch is not None:
                # Start with smooth voice leading
                pitch = self._smooth_voice_lead(previous_pitch, chord_tones)
            elif options.style == MelodyStyle.ARPEGGIATED:
                # Arpeggiate through chord tones
                pitch = chord_tones[i % len(chord_tones)]
            elif options.style == MelodyStyle.SCALAR:
                # Use scale approach
                pitch = self._scalar_approach(chord_tones, i, len(pattern))
            else:
                # Default: weighted random from chord tones
                pitch = self._weighted_choice(chord_tones, i, len(pattern))
            
            # Add passing/neighbor tones
            if i > 0 and i < len(pattern) - 1:
                if options.include_passing_tones and random.random() < 0.3:
                    pitch = self._add_passing_tone(notes[-1].pitch if notes else pitch, pitch)
                elif options.include_neighbor_tones and random.random() < 0.2:
                    pitch = self._add_neighbor_tone(pitch, chord_tones)
            
            notes.append(DetectedNote(
                pitch=pitch,
                start_time=current_time,
                end_time=current_time + duration_seconds,
                velocity=self._calculate_velocity(i, len(pattern)),
                confidence=0.8,
            ))
            
            current_time += duration_seconds
        
        return notes
    
    def _get_chord_tones(self, chord: DetectedChord, octave: int = 4) -> list[int]:
        """Get MIDI pitches for chord tones in specified octave."""
        note_map = {
            "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
            "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
        }
        
        root_pc = note_map.get(chord.root, 0)
        root_midi = (octave + 1) * 12 + root_pc
        
        intervals = self.CHORD_TONES.get(chord.quality, [0, 4, 7])
        
        return [root_midi + interval for interval in intervals]
    
    def _get_rhythm_pattern(
        self, 
        style: MelodyStyle, 
        chord_duration: float,
        bpm: int,
    ) -> list[float]:
        """Get a rhythm pattern for the chord duration."""
        patterns = self.RHYTHM_PATTERNS.get(style, self.RHYTHM_PATTERNS[MelodyStyle.SIMPLE])
        
        # Convert chord duration to beats
        seconds_per_beat = 60.0 / bpm
        chord_beats = chord_duration / seconds_per_beat
        
        # Find pattern that fits
        for pattern in patterns:
            pattern_total = sum(pattern)
            if pattern_total <= chord_beats + 0.5:
                # Scale pattern to fit exactly
                scale = chord_beats / pattern_total
                return [d * scale for d in pattern]
        
        # Default: fill with quarter notes
        num_quarters = max(1, int(chord_beats))
        return [chord_beats / num_quarters] * num_quarters
    
    def _scale_pattern(self, pattern: list[float], density: float) -> list[float]:
        """Scale pattern duration by density factor."""
        if density == 1.0:
            return pattern
        
        if density < 1.0:
            # Fewer notes, longer durations
            step = int(1.0 / density)
            new_pattern = []
            i = 0
            while i < len(pattern):
                total = sum(pattern[i:i+step])
                new_pattern.append(total)
                i += step
            return new_pattern if new_pattern else pattern
        else:
            # More notes, shorter durations
            factor = int(density)
            return [d / factor for d in pattern for _ in range(factor)]
    
    def _smooth_voice_lead(self, previous: int, targets: list[int]) -> int:
        """Choose chord tone closest to previous pitch."""
        # Consider octave above and below
        all_targets = []
        for t in targets:
            all_targets.extend([t - 12, t, t + 12])
        
        # Filter to reasonable range
        all_targets = [t for t in all_targets if 48 <= t <= 84]
        
        if not all_targets:
            return targets[0] if targets else 60
        
        return min(all_targets, key=lambda x: abs(x - previous))
    
    def _scalar_approach(self, chord_tones: list[int], position: int, total: int) -> int:
        """Generate scalar motion through chord tones."""
        if not chord_tones:
            return 60
        
        # Direction based on position
        ascending = position < total // 2
        
        # Map position to chord tone index
        idx = position % len(chord_tones)
        if not ascending:
            idx = len(chord_tones) - 1 - idx
        
        base = chord_tones[idx % len(chord_tones)]
        
        # Add scalar motion
        step = (position % 3) - 1  # -1, 0, or 1
        return base + step
    
    def _weighted_choice(self, chord_tones: list[int], position: int, total: int) -> int:
        """Choose chord tone with weighted probability."""
        if not chord_tones:
            return 60
        
        # Weight root and fifth more heavily
        weights = [3, 1, 2, 1][:len(chord_tones)]  # Root, 3rd, 5th, 7th
        
        # On beat 1, prefer root
        if position == 0:
            weights[0] *= 2
        
        # On last beat, prepare resolution
        if position == total - 1:
            weights[0] *= 1.5
        
        # Normalize and choose
        total_weight = sum(weights)
        r = random.random() * total_weight
        
        cumulative = 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return chord_tones[i]
        
        return chord_tones[0]
    
    def _add_passing_tone(self, from_pitch: int, to_pitch: int) -> int:
        """Add a chromatic passing tone between two pitches."""
        if from_pitch == to_pitch:
            return from_pitch
        
        direction = 1 if to_pitch > from_pitch else -1
        # Return chromatic passing tone
        return from_pitch + direction
    
    def _add_neighbor_tone(self, pitch: int, chord_tones: list[int]) -> int:
        """Add an upper or lower neighbor tone."""
        # Choose upper or lower
        direction = random.choice([-1, 1])
        neighbor = pitch + direction
        
        # If neighbor is a chord tone, go further
        if neighbor in chord_tones:
            neighbor += direction
        
        return neighbor
    
    def _calculate_velocity(self, position: int, total: int) -> int:
        """Calculate velocity based on metric position."""
        base_velocity = MIDI_DEFAULT_VELOCITY
        
        # Downbeat accent
        if position == 0:
            return min(127, base_velocity + 15)
        
        # Weak beats softer
        if position % 2 == 1:
            return max(50, base_velocity - 10)
        
        return base_velocity
    
    def suggest_from_single_chord(
        self,
        chord: DetectedChord,
        duration: float = 4.0,
        options: Optional[MelodyOptions] = None,
        bpm: int = 120,
    ) -> NoteList:
        """
        Generate melody for a single chord.
        
        Useful for practicing or improvisation suggestions.
        """
        # Create temporary chord list
        temp_chord = DetectedChord(
            symbol=chord.symbol,
            root=chord.root,
            quality=chord.quality,
            timestamp=0.0,
            duration=duration,
            bass_note=chord.bass_note,
            confidence=chord.confidence,
        )
        
        temp_list = ChordList(chords=[temp_chord], duration=duration)
        
        return self.suggest(temp_list, options, bpm)
    
    def get_chord_scale(self, chord: DetectedChord, octave: int = 4) -> list[int]:
        """
        Get the recommended scale for improvising over a chord.
        
        Returns MIDI pitches for one octave of the scale.
        """
        note_map = {
            "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
            "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
        }
        
        root = note_map.get(chord.root, 0)
        root_midi = (octave + 1) * 12 + root
        
        # Scale patterns (intervals from root)
        scale_map = {
            ChordQuality.MAJOR: [0, 2, 4, 5, 7, 9, 11],  # Major scale
            ChordQuality.MINOR: [0, 2, 3, 5, 7, 8, 10],  # Natural minor
            ChordQuality.DOMINANT_7: [0, 2, 4, 5, 7, 9, 10],  # Mixolydian
            ChordQuality.MINOR_7: [0, 2, 3, 5, 7, 9, 10],  # Dorian
            ChordQuality.MAJOR_7: [0, 2, 4, 5, 7, 9, 11],  # Major scale
            ChordQuality.DIMINISHED: [0, 2, 3, 5, 6, 8, 9, 11],  # Diminished scale
            ChordQuality.AUGMENTED: [0, 3, 4, 7, 8, 11],  # Augmented scale
        }
        
        intervals = scale_map.get(chord.quality, [0, 2, 4, 5, 7, 9, 11])
        
        return [root_midi + i for i in intervals]
