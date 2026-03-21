"""Rhythm correction engine - applies learned patterns to fix timing issues."""

import logging
from typing import List, Tuple, Optional
from pathlib import Path
import numpy as np

from app.models.note import NoteList, DetectedNote
from app.models.rhythm_patterns import (
    PatternDatabase,
    RhythmPattern,
    STANDARD_DURATIONS,
    quantize_duration,
    quantize_to_grid,
)
from app.services.rhythm_analyzer import RhythmAnalyzer

logger = logging.getLogger(__name__)


class RhythmCorrector:
    """
    Corrects rhythm and timing issues in detected notes.
    
    Uses learned patterns from training data to improve accuracy.
    """
    
    DEFAULT_DATABASE_PATH = Path(__file__).parent.parent.parent / "data" / "patterns.json"
    
    def __init__(
        self, 
        database: PatternDatabase = None,
        database_path: str | Path = None,
    ):
        # Load or create database
        if database is not None:
            self.database = database
        elif database_path is not None:
            self.database = PatternDatabase.load(database_path)
        elif self.DEFAULT_DATABASE_PATH.exists():
            self.database = PatternDatabase.load(self.DEFAULT_DATABASE_PATH)
        else:
            # Create with default patterns
            self.database = self._create_default_database()
        
        self.analyzer = RhythmAnalyzer(self.database)
        
        # Correction parameters
        self.default_correction_strength = 0.5
        self.snap_threshold = 0.1  # Max time difference for snapping
        self.min_note_duration = 0.125  # 32nd note minimum
    
    def _create_default_database(self) -> PatternDatabase:
        """Create database with common default patterns."""
        from app.services.data_collector import DataCollector
        import asyncio
        
        collector = DataCollector()
        asyncio.get_event_loop().run_until_complete(
            collector.collect_sample_data(count=100)
        )
        
        # Save for future use
        self.DEFAULT_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        collector.save_database(self.DEFAULT_DATABASE_PATH)
        
        return collector.get_database()
    
    def correct(
        self,
        notes: NoteList,
        time_signature: str = "4/4",
        tempo: int = 120,
        correction_strength: float = None,
    ) -> NoteList:
        """
        Apply rhythm corrections to detected notes.
        
        Args:
            notes: Original detected notes
            time_signature: Time signature for context
            tempo: Tempo in BPM
            correction_strength: 0-1, how aggressively to correct
                                (0 = no correction, 1 = full pattern matching)
        
        Returns:
            Corrected NoteList
        """
        if correction_strength is None:
            correction_strength = self.default_correction_strength
        
        if not notes.notes or correction_strength == 0:
            return notes
        
        logger.info(f"Applying rhythm correction (strength={correction_strength})")
        
        # Sort notes by start time
        sorted_notes = sorted(notes.notes, key=lambda n: n.start_time)
        
        # Convert times to beat-based values
        seconds_per_beat = 60.0 / tempo
        
        # Apply corrections
        corrected_notes = []
        
        for i, note in enumerate(sorted_notes):
            # Step 1: Snap start time to grid
            corrected_start = self._snap_to_beat_grid(
                note.start_time, 
                seconds_per_beat, 
                correction_strength
            )
            
            # Step 2: Correct duration
            original_duration_beats = note.duration / seconds_per_beat
            corrected_duration_beats = self._correct_duration(
                original_duration_beats,
                (note.start_time / seconds_per_beat) % self._get_beats(time_signature),
                time_signature,
                correction_strength,
            )
            corrected_duration = corrected_duration_beats * seconds_per_beat
            
            # Step 3: Ensure minimum duration
            corrected_duration = max(corrected_duration, self.min_note_duration * seconds_per_beat)
            
            # Step 4: Adjust end time to not overlap with next note
            if i < len(sorted_notes) - 1:
                next_start = sorted_notes[i + 1].start_time
                next_start_corrected = self._snap_to_beat_grid(
                    next_start, seconds_per_beat, correction_strength
                )
                max_duration = next_start_corrected - corrected_start - 0.01
                if corrected_duration > max_duration > 0:
                    corrected_duration = max_duration
            
            # Create corrected note
            corrected_notes.append(DetectedNote(
                pitch=note.pitch,
                start_time=corrected_start,
                end_time=corrected_start + corrected_duration,
                velocity=note.velocity,
                confidence=note.confidence,
                pitch_bend=note.pitch_bend,
            ))
        
        # Step 5: Apply pattern-based correction if strength is high
        if correction_strength > 0.4:
            corrected_notes = self._apply_pattern_correction(
                corrected_notes,
                time_signature,
                tempo,
                correction_strength,
            )
        
        return NoteList(
            notes=corrected_notes,
            source_file=notes.source_file,
            duration=notes.duration,
            sample_rate=notes.sample_rate,
        )
    
    def _get_beats(self, time_signature: str) -> int:
        """Get beats per measure from time signature."""
        return int(time_signature.split("/")[0])
    
    def _snap_to_beat_grid(
        self, 
        time: float, 
        seconds_per_beat: float,
        correction_strength: float,
    ) -> float:
        """Snap a time value to the nearest beat grid position."""
        # Determine grid resolution based on correction strength
        # Higher strength = finer grid (more precise snapping)
        if correction_strength > 0.7:
            grid_divisions = 8  # 32nd notes
        elif correction_strength > 0.4:
            grid_divisions = 4  # 16th notes
        else:
            grid_divisions = 2  # 8th notes
        
        grid_size = seconds_per_beat / grid_divisions
        
        # Calculate nearest grid position
        nearest_grid = round(time / grid_size) * grid_size
        
        # Blend between original and snapped based on correction strength
        distance = abs(time - nearest_grid)
        
        if distance < self.snap_threshold * seconds_per_beat:
            # Close to grid - apply full snap
            blend = correction_strength
        else:
            # Far from grid - apply partial snap
            blend = correction_strength * 0.5
        
        return time * (1 - blend) + nearest_grid * blend
    
    def _correct_duration(
        self,
        duration_beats: float,
        beat_position: float,
        time_signature: str,
        correction_strength: float,
    ) -> float:
        """Correct a note duration based on learned patterns."""
        model = self.database.get_model(time_signature)
        
        # Get beat position statistics
        pos_key = str(round(beat_position, 2))
        
        suggested_duration = duration_beats
        
        if pos_key in model.beat_position_stats:
            stats = model.beat_position_stats[pos_key]
            likely_duration = stats.most_likely_duration()
            
            # Weight by how much training data we have
            confidence = min(1.0, stats.total_count / 100)
            
            # Blend original with suggested
            blend = correction_strength * confidence
            suggested_duration = duration_beats * (1 - blend) + likely_duration * blend
        
        # Always quantize to standard duration
        return quantize_duration(suggested_duration)
    
    def _apply_pattern_correction(
        self,
        notes: List[DetectedNote],
        time_signature: str,
        tempo: int,
        correction_strength: float,
    ) -> List[DetectedNote]:
        """Apply pattern-based correction for context-aware fixes."""
        if not notes:
            return notes
        
        seconds_per_beat = 60.0 / tempo
        beats_per_measure = self._get_beats(time_signature)
        
        # Group notes into measures
        measures = self._group_notes_into_measures(
            notes, seconds_per_beat, beats_per_measure
        )
        
        corrected = []
        
        for measure_notes in measures:
            if len(measure_notes) < 2:
                corrected.extend(measure_notes)
                continue
            
            # Extract durations
            durations = [n.duration / seconds_per_beat for n in measure_notes]
            
            # Find best matching pattern
            match = self.analyzer.find_best_pattern_match(durations, time_signature)
            
            if match and match[1] > 0.6:
                pattern, score = match
                
                # Apply pattern if lengths match
                if len(pattern.durations) == len(measure_notes):
                    blend = correction_strength * score * 0.5
                    
                    for note, pattern_dur in zip(measure_notes, pattern.durations):
                        original_dur = note.duration / seconds_per_beat
                        corrected_dur = original_dur * (1 - blend) + pattern_dur * blend
                        corrected_dur = quantize_duration(corrected_dur) * seconds_per_beat
                        
                        corrected.append(DetectedNote(
                            pitch=note.pitch,
                            start_time=note.start_time,
                            end_time=note.start_time + corrected_dur,
                            velocity=note.velocity,
                            confidence=note.confidence,
                            pitch_bend=note.pitch_bend,
                        ))
                else:
                    corrected.extend(measure_notes)
            else:
                corrected.extend(measure_notes)
        
        return corrected
    
    def _group_notes_into_measures(
        self,
        notes: List[DetectedNote],
        seconds_per_beat: float,
        beats_per_measure: int,
    ) -> List[List[DetectedNote]]:
        """Group notes into measures based on timing."""
        measure_duration = seconds_per_beat * beats_per_measure
        
        measures = []
        current_measure = []
        current_measure_start = 0.0
        
        for note in sorted(notes, key=lambda n: n.start_time):
            # Check if note starts in a new measure
            while note.start_time >= current_measure_start + measure_duration:
                if current_measure:
                    measures.append(current_measure)
                    current_measure = []
                current_measure_start += measure_duration
            
            current_measure.append(note)
        
        if current_measure:
            measures.append(current_measure)
        
        return measures
    
    def get_correction_preview(
        self,
        notes: NoteList,
        time_signature: str = "4/4",
        tempo: int = 120,
        correction_strength: float = None,
    ) -> dict:
        """
        Get a preview of corrections without applying them.
        
        Returns:
            Dict with original and corrected durations, timing changes, etc.
        """
        if correction_strength is None:
            correction_strength = self.default_correction_strength
        
        corrected = self.correct(notes, time_signature, tempo, correction_strength)
        
        changes = []
        for orig, corr in zip(notes.notes, corrected.notes):
            time_change = corr.start_time - orig.start_time
            duration_change = corr.duration - orig.duration
            
            if abs(time_change) > 0.01 or abs(duration_change) > 0.01:
                changes.append({
                    "pitch": orig.pitch,
                    "original_start": orig.start_time,
                    "corrected_start": corr.start_time,
                    "time_change": time_change,
                    "original_duration": orig.duration,
                    "corrected_duration": corr.duration,
                    "duration_change": duration_change,
                })
        
        return {
            "total_notes": len(notes.notes),
            "notes_changed": len(changes),
            "changes": changes,
            "correction_strength": correction_strength,
        }
    
    def reload_database(self, path: str | Path = None):
        """Reload the pattern database from disk."""
        if path is None:
            path = self.DEFAULT_DATABASE_PATH
        
        if Path(path).exists():
            self.database = PatternDatabase.load(path)
            self.analyzer = RhythmAnalyzer(self.database)
            logger.info(f"Reloaded pattern database from {path}")
        else:
            logger.warning(f"Database file not found: {path}")
