"""Rhythm pattern analyzer - learns patterns from training data."""

import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np

from app.models.rhythm_patterns import (
    PatternDatabase,
    RhythmPattern,
    TimeSignatureModel,
    BeatPositionStats,
    STANDARD_DURATIONS,
    quantize_duration,
)
from app.models.note import NoteList, DetectedNote

logger = logging.getLogger(__name__)


class RhythmAnalyzer:
    """Analyzes rhythm patterns and builds statistical models."""
    
    def __init__(self, database: PatternDatabase = None):
        self.database = database or PatternDatabase()
        
        # Analysis parameters
        self.min_pattern_frequency = 2  # Minimum times a pattern must appear
        self.max_pattern_length = 16    # Maximum notes in a pattern
        self.similarity_threshold = 0.8  # Threshold for pattern matching
    
    def analyze_notes(
        self, 
        notes: List[DetectedNote], 
        time_signature: str = "4/4",
        tempo: int = 120,
    ) -> Dict:
        """
        Analyze a sequence of detected notes to extract rhythm patterns.
        
        Returns:
            Dict with analysis results including patterns, statistics
        """
        if not notes:
            return {"patterns": [], "stats": {}}
        
        # Convert note times to durations in quarter notes
        seconds_per_beat = 60.0 / tempo
        durations = []
        beat_positions = []
        
        for note in sorted(notes, key=lambda n: n.start_time):
            duration = note.duration / seconds_per_beat
            beat_pos = (note.start_time / seconds_per_beat) % self._get_beats_per_measure(time_signature)
            
            durations.append(duration)
            beat_positions.append(beat_pos)
        
        # Extract patterns from sequences
        patterns = self._extract_patterns(durations, time_signature)
        
        # Calculate duration statistics
        stats = self._calculate_duration_stats(durations, beat_positions)
        
        return {
            "patterns": patterns,
            "stats": stats,
            "durations": durations,
            "beat_positions": beat_positions,
        }
    
    def _get_beats_per_measure(self, time_signature: str) -> int:
        """Get number of beats per measure from time signature."""
        parts = time_signature.split("/")
        return int(parts[0]) if parts else 4
    
    def _extract_patterns(
        self, 
        durations: List[float], 
        time_signature: str
    ) -> List[RhythmPattern]:
        """Extract rhythm patterns from a duration sequence."""
        patterns = []
        beats_per_measure = self._get_beats_per_measure(time_signature)
        
        # Group durations into measures
        measures = self._group_into_measures(durations, beats_per_measure)
        
        for measure_durations in measures:
            if len(measure_durations) >= 2:
                # Quantize durations
                quantized = [quantize_duration(d) for d in measure_durations]
                
                pattern = RhythmPattern(
                    durations=quantized,
                    time_signature=time_signature,
                    beat_count=beats_per_measure,
                    frequency=1,
                )
                patterns.append(pattern)
        
        return patterns
    
    def _group_into_measures(
        self, 
        durations: List[float], 
        beats_per_measure: int
    ) -> List[List[float]]:
        """Group durations into measures."""
        measures = []
        current_measure = []
        current_duration = 0.0
        
        for dur in durations:
            current_measure.append(dur)
            current_duration += dur
            
            if current_duration >= beats_per_measure - 0.1:
                measures.append(current_measure)
                current_measure = []
                current_duration = 0.0
        
        if current_measure:
            measures.append(current_measure)
        
        return measures
    
    def _calculate_duration_stats(
        self, 
        durations: List[float], 
        beat_positions: List[float]
    ) -> Dict:
        """Calculate statistics about duration distributions."""
        if not durations:
            return {}
        
        # Group by beat position (quantized to 0.25)
        position_durations = defaultdict(list)
        for dur, pos in zip(durations, beat_positions):
            quantized_pos = round(pos * 4) / 4
            position_durations[quantized_pos].append(dur)
        
        stats = {
            "mean_duration": float(np.mean(durations)),
            "std_duration": float(np.std(durations)),
            "min_duration": float(min(durations)),
            "max_duration": float(max(durations)),
            "duration_distribution": {},
            "position_stats": {},
        }
        
        # Duration distribution
        duration_counts = defaultdict(int)
        for dur in durations:
            quantized = quantize_duration(dur)
            duration_counts[quantized] += 1
        
        total = len(durations)
        stats["duration_distribution"] = {
            str(k): v / total for k, v in duration_counts.items()
        }
        
        # Position-specific statistics
        for pos, durs in position_durations.items():
            if durs:
                stats["position_stats"][str(pos)] = {
                    "mean": float(np.mean(durs)),
                    "most_common": quantize_duration(np.median(durs)),
                    "count": len(durs),
                }
        
        return stats
    
    def find_best_pattern_match(
        self, 
        durations: List[float], 
        time_signature: str = "4/4"
    ) -> Optional[Tuple[RhythmPattern, float]]:
        """
        Find the best matching pattern for a duration sequence.
        
        Returns:
            Tuple of (best_pattern, similarity_score) or None
        """
        model = self.database.get_model(time_signature)
        
        if not model.patterns:
            return None
        
        best_match = None
        best_score = 0.0
        
        for pattern in model.patterns:
            score = pattern.similarity(durations)
            weighted_score = score * (1 + 0.05 * min(pattern.frequency, 50))
            
            if weighted_score > best_score:
                best_score = weighted_score
                best_match = pattern
        
        if best_match and best_score >= self.similarity_threshold:
            return (best_match, best_score)
        
        return None
    
    def suggest_corrections(
        self, 
        durations: List[float], 
        beat_positions: List[float],
        time_signature: str = "4/4",
        correction_strength: float = 0.5,
    ) -> List[float]:
        """
        Suggest corrected durations based on learned patterns.
        
        Args:
            durations: Original detected durations
            beat_positions: Beat positions for each note
            time_signature: Time signature
            correction_strength: 0-1, how aggressively to correct
            
        Returns:
            Corrected duration list
        """
        if not durations:
            return []
        
        model = self.database.get_model(time_signature)
        corrected = []
        
        for i, (dur, pos) in enumerate(zip(durations, beat_positions)):
            # Get suggested duration for this beat position
            pos_key = str(round(pos % 4, 2))
            suggested = dur
            
            if pos_key in model.beat_position_stats:
                stats = model.beat_position_stats[pos_key]
                likely_dur = stats.most_likely_duration()
                
                # Blend between original and suggested based on correction strength
                if correction_strength > 0:
                    # Check how close we are to a standard duration
                    original_quantized = quantize_duration(dur)
                    
                    if abs(dur - original_quantized) > 0.1:
                        # Original is far from standard, apply more correction
                        blend = correction_strength
                    else:
                        # Original is close to standard, apply less
                        blend = correction_strength * 0.5
                    
                    suggested = dur * (1 - blend) + likely_dur * blend
            
            # Always quantize to standard duration
            corrected.append(quantize_duration(suggested))
        
        # Try pattern matching for more context-aware correction
        if correction_strength > 0.3:
            corrected = self._apply_pattern_correction(
                corrected, time_signature, correction_strength
            )
        
        return corrected
    
    def _apply_pattern_correction(
        self, 
        durations: List[float], 
        time_signature: str,
        correction_strength: float,
    ) -> List[float]:
        """Apply pattern-based correction to durations."""
        model = self.database.get_model(time_signature)
        beats_per_measure = self._get_beats_per_measure(time_signature)
        
        # Group into measures
        measures = self._group_into_measures(durations, beats_per_measure)
        
        corrected = []
        for measure in measures:
            # Find best matching pattern
            match = self.find_best_pattern_match(measure, time_signature)
            
            if match and match[1] > 0.7:
                pattern, score = match
                
                # Use pattern durations if good match
                if len(pattern.durations) == len(measure):
                    # Blend based on score and correction strength
                    blend = correction_strength * score
                    for orig, pat in zip(measure, pattern.durations):
                        corrected.append(orig * (1 - blend) + pat * blend)
                else:
                    corrected.extend(measure)
            else:
                corrected.extend(measure)
        
        # Re-quantize
        return [quantize_duration(d) for d in corrected]
    
    def get_common_patterns(
        self, 
        time_signature: str = "4/4", 
        top_n: int = 10
    ) -> List[RhythmPattern]:
        """Get the most common patterns for a time signature."""
        model = self.database.get_model(time_signature)
        return model.get_top_patterns(top_n)
    
    def add_to_database(
        self, 
        notes: List[DetectedNote],
        time_signature: str = "4/4",
        tempo: int = 120,
    ):
        """Add analyzed patterns to the database."""
        analysis = self.analyze_notes(notes, time_signature, tempo)
        
        for pattern in analysis["patterns"]:
            self.database.add_pattern(pattern)
        
        # Update beat position statistics
        model = self.database.get_model(time_signature)
        for dur, pos in zip(analysis["durations"], analysis["beat_positions"]):
            pos_key = str(round(pos % 4, 2))
            if pos_key not in model.beat_position_stats:
                model.beat_position_stats[pos_key] = BeatPositionStats(
                    beat_position=float(pos_key)
                )
            model.beat_position_stats[pos_key].add_duration(dur)
