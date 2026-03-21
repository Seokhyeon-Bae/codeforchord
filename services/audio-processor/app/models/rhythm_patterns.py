"""Data models for rhythm pattern learning and correction."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json
from pathlib import Path


class QuantizationLevel(str, Enum):
    """Standard quantization levels for note durations."""
    
    WHOLE = "whole"           # 4.0 quarter notes
    HALF = "half"             # 2.0 quarter notes
    QUARTER = "quarter"       # 1.0 quarter notes
    EIGHTH = "eighth"         # 0.5 quarter notes
    SIXTEENTH = "sixteenth"   # 0.25 quarter notes
    THIRTY_SECOND = "32nd"    # 0.125 quarter notes
    TRIPLET_QUARTER = "triplet_quarter"  # 0.667 quarter notes
    TRIPLET_EIGHTH = "triplet_eighth"    # 0.333 quarter notes


class NoteDuration(BaseModel):
    """Represents a single note duration in a pattern."""
    
    duration: float = Field(..., description="Duration in quarter notes")
    is_rest: bool = Field(default=False, description="Whether this is a rest")
    beat_position: float = Field(default=0.0, description="Position within the measure (0-based)")
    
    @property
    def quantization_level(self) -> QuantizationLevel:
        """Determine the closest standard quantization level."""
        duration_map = {
            4.0: QuantizationLevel.WHOLE,
            2.0: QuantizationLevel.HALF,
            1.0: QuantizationLevel.QUARTER,
            0.5: QuantizationLevel.EIGHTH,
            0.25: QuantizationLevel.SIXTEENTH,
            0.125: QuantizationLevel.THIRTY_SECOND,
            0.667: QuantizationLevel.TRIPLET_QUARTER,
            0.333: QuantizationLevel.TRIPLET_EIGHTH,
        }
        
        # Find closest match
        closest = min(duration_map.keys(), key=lambda x: abs(x - self.duration))
        return duration_map[closest]


class RhythmPattern(BaseModel):
    """Represents a sequence of note durations forming a rhythmic pattern."""
    
    durations: List[float] = Field(..., description="List of durations in quarter notes")
    time_signature: str = Field(default="4/4", description="Time signature this pattern belongs to")
    beat_count: int = Field(default=4, description="Number of beats in the pattern")
    frequency: int = Field(default=1, description="How often this pattern was seen in training")
    
    @property
    def total_duration(self) -> float:
        """Total duration of the pattern in quarter notes."""
        return sum(self.durations)
    
    @property
    def pattern_hash(self) -> str:
        """Create a unique hash for this pattern."""
        # Round durations to avoid floating point issues
        rounded = [round(d, 3) for d in self.durations]
        return f"{self.time_signature}:{','.join(map(str, rounded))}"
    
    def matches(self, other_durations: List[float], tolerance: float = 0.1) -> bool:
        """Check if another duration sequence matches this pattern within tolerance."""
        if len(other_durations) != len(self.durations):
            return False
        
        for d1, d2 in zip(self.durations, other_durations):
            if abs(d1 - d2) > tolerance:
                return False
        return True
    
    def similarity(self, other_durations: List[float]) -> float:
        """Calculate similarity score (0-1) with another duration sequence."""
        if not other_durations:
            return 0.0
        
        # Pad shorter sequence
        max_len = max(len(self.durations), len(other_durations))
        d1 = list(self.durations) + [0.0] * (max_len - len(self.durations))
        d2 = list(other_durations) + [0.0] * (max_len - len(other_durations))
        
        # Calculate normalized difference
        total_diff = sum(abs(a - b) for a, b in zip(d1, d2))
        max_possible_diff = sum(max(a, b) for a, b in zip(d1, d2)) + 0.001
        
        return 1.0 - (total_diff / max_possible_diff)


class BeatPositionStats(BaseModel):
    """Statistics for note durations at specific beat positions."""
    
    beat_position: float = Field(..., description="Beat position (0, 0.5, 1, 1.5, etc.)")
    duration_counts: Dict[str, int] = Field(
        default_factory=dict, 
        description="Count of each duration at this position"
    )
    total_count: int = Field(default=0, description="Total notes at this position")
    
    def add_duration(self, duration: float):
        """Record a duration observation at this beat position."""
        # Round to standard value
        key = str(round(duration, 3))
        self.duration_counts[key] = self.duration_counts.get(key, 0) + 1
        self.total_count += 1
    
    def most_likely_duration(self) -> float:
        """Get the most common duration at this beat position."""
        if not self.duration_counts:
            return 1.0  # Default to quarter note
        
        best_key = max(self.duration_counts.keys(), key=lambda k: self.duration_counts[k])
        return float(best_key)
    
    def probability(self, duration: float) -> float:
        """Get probability of a specific duration at this position."""
        if self.total_count == 0:
            return 0.0
        
        key = str(round(duration, 3))
        count = self.duration_counts.get(key, 0)
        return count / self.total_count


class TimeSignatureModel(BaseModel):
    """Learned model for a specific time signature."""
    
    time_signature: str = Field(..., description="Time signature (e.g., '4/4')")
    beats_per_measure: int = Field(..., description="Number of beats per measure")
    beat_unit: int = Field(default=4, description="Note value that gets one beat")
    
    # Learned statistics
    patterns: List[RhythmPattern] = Field(
        default_factory=list,
        description="Common rhythm patterns for this time signature"
    )
    beat_position_stats: Dict[str, BeatPositionStats] = Field(
        default_factory=dict,
        description="Duration statistics by beat position"
    )
    common_subdivisions: List[float] = Field(
        default_factory=lambda: [1.0, 0.5, 0.25],
        description="Common beat subdivisions"
    )
    
    def add_pattern(self, pattern: RhythmPattern):
        """Add or update a pattern in the model."""
        for existing in self.patterns:
            if existing.pattern_hash == pattern.pattern_hash:
                existing.frequency += pattern.frequency
                return
        
        self.patterns.append(pattern)
    
    def get_top_patterns(self, n: int = 10) -> List[RhythmPattern]:
        """Get the n most frequent patterns."""
        sorted_patterns = sorted(self.patterns, key=lambda p: p.frequency, reverse=True)
        return sorted_patterns[:n]
    
    def get_best_match(self, durations: List[float]) -> Optional[RhythmPattern]:
        """Find the best matching pattern for a duration sequence."""
        best_pattern = None
        best_score = 0.0
        
        for pattern in self.patterns:
            score = pattern.similarity(durations) * (pattern.frequency ** 0.5)
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        return best_pattern


class PatternDatabase(BaseModel):
    """Collection of learned rhythm patterns across time signatures."""
    
    time_signatures: Dict[str, TimeSignatureModel] = Field(
        default_factory=dict,
        description="Models for each time signature"
    )
    total_songs_analyzed: int = Field(default=0, description="Number of songs used for training")
    total_patterns_learned: int = Field(default=0, description="Total unique patterns learned")
    version: str = Field(default="1.0", description="Database version")
    
    def get_model(self, time_signature: str) -> TimeSignatureModel:
        """Get or create a model for a time signature."""
        if time_signature not in self.time_signatures:
            # Parse time signature
            parts = time_signature.split("/")
            beats = int(parts[0]) if len(parts) > 0 else 4
            unit = int(parts[1]) if len(parts) > 1 else 4
            
            self.time_signatures[time_signature] = TimeSignatureModel(
                time_signature=time_signature,
                beats_per_measure=beats,
                beat_unit=unit,
            )
        
        return self.time_signatures[time_signature]
    
    def add_pattern(self, pattern: RhythmPattern):
        """Add a pattern to the appropriate time signature model."""
        model = self.get_model(pattern.time_signature)
        model.add_pattern(pattern)
        self.total_patterns_learned = sum(
            len(m.patterns) for m in self.time_signatures.values()
        )
    
    def save(self, path: str | Path):
        """Save database to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2)
    
    @classmethod
    def load(cls, path: str | Path) -> "PatternDatabase":
        """Load database from JSON file."""
        path = Path(path)
        
        if not path.exists():
            return cls()
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return cls.model_validate(data)
    
    def get_correction_candidates(
        self, 
        durations: List[float], 
        time_signature: str = "4/4",
        top_n: int = 5,
    ) -> List[Tuple[RhythmPattern, float]]:
        """
        Get top pattern matches for a duration sequence.
        
        Returns list of (pattern, similarity_score) tuples.
        """
        model = self.get_model(time_signature)
        
        candidates = []
        for pattern in model.patterns:
            score = pattern.similarity(durations)
            # Weight by frequency (more common patterns are more likely correct)
            weighted_score = score * (1 + 0.1 * min(pattern.frequency, 100))
            candidates.append((pattern, weighted_score))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]


# Standard duration values for quantization
STANDARD_DURATIONS = [
    4.0,    # whole
    3.0,    # dotted half
    2.0,    # half
    1.5,    # dotted quarter
    1.0,    # quarter
    0.75,   # dotted eighth
    0.5,    # eighth
    0.375,  # dotted sixteenth
    0.25,   # sixteenth
    0.125,  # thirty-second
    # Triplets
    0.667,  # quarter triplet
    0.333,  # eighth triplet
    0.167,  # sixteenth triplet
]


def quantize_duration(duration: float, allowed: List[float] = None) -> float:
    """Quantize a duration to the nearest standard value."""
    if allowed is None:
        allowed = STANDARD_DURATIONS
    
    return min(allowed, key=lambda x: abs(x - duration))


def quantize_to_grid(time: float, grid_size: float = 0.25) -> float:
    """Quantize a time value to the nearest grid position."""
    return round(time / grid_size) * grid_size
