"""Merge and combine audio analysis results."""

from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import tempfile
import numpy as np
import librosa

from app.models.note import NoteList
from app.models.chord import ChordList
from app.services.pitch_detector import PitchDetector
from app.services.chord_detector import ChordDetector


class AudioMerger:
    """
    Combine results from multiple audio analysis services.
    
    Handles:
    - Running both pitch and chord detection
    - Aligning results temporally
    - Filtering by instrument type
    """
    
    def __init__(
        self,
        pitch_detector: Optional[PitchDetector] = None,
        chord_detector: Optional[ChordDetector] = None,
    ):
        self.pitch_detector = pitch_detector or PitchDetector()
        self.chord_detector = chord_detector or ChordDetector()
    
    def analyze(
        self, 
        audio_path: str | Path,
        detect_notes: bool = True,
        detect_chords: bool = True,
        min_note_confidence: float = 0.5,
    ) -> Tuple[Optional[NoteList], Optional[ChordList]]:
        """
        Run full audio analysis.
        
        Args:
            audio_path: Path to audio file
            detect_notes: Whether to detect notes
            detect_chords: Whether to detect chords
            min_note_confidence: Minimum confidence for note inclusion
            
        Returns:
            Tuple of (NoteList, ChordList)
        """
        notes = None
        chords = None
        
        if detect_notes:
            notes = self.pitch_detector.detect(audio_path)
            if min_note_confidence > 0:
                notes = notes.filter_by_confidence(min_note_confidence)
        
        if detect_chords:
            chords = self.chord_detector.detect(audio_path)
        
        return notes, chords
    
    def analyze_from_bytes(
        self,
        audio_data: bytes,
        file_extension: str = ".wav",
        detect_notes: bool = True,
        detect_chords: bool = True,
        min_note_confidence: float = 0.5,
    ) -> Tuple[Optional[NoteList], Optional[ChordList]]:
        """
        Run full audio analysis from bytes.
        
        Args:
            audio_data: Raw audio bytes
            file_extension: Audio format extension
            detect_notes: Whether to detect notes
            detect_chords: Whether to detect chords
            min_note_confidence: Minimum note confidence
            
        Returns:
            Tuple of (NoteList, ChordList)
        """
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = Path(tmp.name)
        
        try:
            return self.analyze(
                tmp_path,
                detect_notes=detect_notes,
                detect_chords=detect_chords,
                min_note_confidence=min_note_confidence,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def align_to_beats(
        self,
        notes: NoteList,
        chords: ChordList,
        bpm: int = 120,
    ) -> Tuple[NoteList, ChordList]:
        """
        Quantize note and chord timings to beat grid.
        
        Useful for cleaner sheet music output.
        """
        seconds_per_beat = 60.0 / bpm
        
        # Quantize notes
        quantized_notes = []
        for note in notes.notes:
            # Round to nearest 16th note
            grid = seconds_per_beat / 4
            new_start = round(note.start_time / grid) * grid
            new_end = round(note.end_time / grid) * grid
            
            # Ensure minimum duration
            if new_end <= new_start:
                new_end = new_start + grid
            
            quantized_notes.append(note.model_copy(update={
                "start_time": new_start,
                "end_time": new_end,
            }))
        
        # Quantize chords
        quantized_chords = []
        for chord in chords.chords:
            grid = seconds_per_beat
            new_timestamp = round(chord.timestamp / grid) * grid
            new_duration = round(chord.duration / grid) * grid
            
            if new_duration < grid:
                new_duration = grid
            
            quantized_chords.append(chord.model_copy(update={
                "timestamp": new_timestamp,
                "duration": new_duration,
            }))
        
        return (
            NoteList(
                notes=quantized_notes,
                source_file=notes.source_file,
                duration=notes.duration,
                sample_rate=notes.sample_rate,
            ),
            ChordList(
                chords=quantized_chords,
                source_file=chords.source_file,
                duration=chords.duration,
                key=chords.key,
            ),
        )
    
    def filter_by_instrument(
        self,
        notes: NoteList,
        instrument: str,
    ) -> NoteList:
        """
        Filter notes by typical instrument range.
        
        Args:
            notes: Input notes
            instrument: "piano", "guitar", or "vocal"
            
        Returns:
            Filtered NoteList
        """
        # Typical MIDI ranges
        ranges = {
            "piano": (21, 108),   # A0 to C8
            "guitar": (40, 88),   # E2 to E6
            "vocal": (48, 84),    # C3 to C6
        }
        
        min_pitch, max_pitch = ranges.get(instrument.lower(), (0, 127))
        
        filtered = [
            n for n in notes.notes 
            if min_pitch <= n.pitch <= max_pitch
        ]
        
        return NoteList(
            notes=filtered,
            source_file=notes.source_file,
            duration=notes.duration,
            sample_rate=notes.sample_rate,
        )
    
    def estimate_tempo(self, audio_path: str | Path) -> Dict[str, Any]:
        """
        Estimate tempo from audio using beat tracking.
        
        Returns:
            Dict with 'tempo' (average BPM), 'tempo_range' (min, max),
            'is_variable' (bool), and 'confidence'
        """
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        
        # Get tempo and beat frames
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        
        # Handle numpy array tempo (librosa may return array)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 120.0
        else:
            tempo = float(tempo)
        
        # Analyze tempo variability
        if len(beat_frames) > 2:
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            beat_intervals = np.diff(beat_times)
            
            if len(beat_intervals) > 0:
                # Calculate local tempos
                local_tempos = 60.0 / beat_intervals
                
                # Filter outliers
                valid_tempos = local_tempos[(local_tempos > 40) & (local_tempos < 240)]
                
                if len(valid_tempos) > 0:
                    tempo_std = float(np.std(valid_tempos))
                    tempo_mean = float(np.mean(valid_tempos))
                    tempo_min = float(np.min(valid_tempos))
                    tempo_max = float(np.max(valid_tempos))
                    
                    # Consider variable if std > 5% of mean
                    is_variable = bool(tempo_std > (tempo_mean * 0.05))

                    # Confidence based on consistency
                    confidence = float(max(0.0, min(1.0, 1.0 - (tempo_std / tempo_mean))))

                    return {
                        "tempo": int(round(tempo_mean)),
                        "tempo_range": (int(round(tempo_min)), int(round(tempo_max))),
                        "is_variable": is_variable,
                        "confidence": round(confidence, 2),
                    }
        
        # Fallback
        return {
            "tempo": round(tempo),
            "tempo_range": (round(tempo), round(tempo)),
            "is_variable": False,
            "confidence": 0.5,
        }
    
    def estimate_time_signature(self, audio_path: str | Path) -> Dict[str, Any]:
        """
        Estimate time signature from audio.
        
        Uses beat strength analysis to determine meter.
        
        Returns:
            Dict with 'time_signature' (e.g., "4/4"), 'beats_per_measure',
            and 'confidence'
        """
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        
        # Get onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Get tempo and beat frames
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
        
        if len(beat_frames) < 8:
            return {
                "time_signature": "4/4",
                "beats_per_measure": 4,
                "confidence": 0.3,
            }
        
        # Analyze beat strength patterns
        beat_strengths = onset_env[beat_frames]
        
        # Try different meters and see which has strongest downbeat pattern
        meters = [2, 3, 4, 6]
        best_meter = 4
        best_score = 0.0
        
        for meter in meters:
            if len(beat_strengths) >= meter * 2:
                # Reshape to measures
                n_measures = len(beat_strengths) // meter
                if n_measures > 0:
                    measure_beats = beat_strengths[:n_measures * meter].reshape(n_measures, meter)
                    
                    # Calculate average beat strength per position
                    avg_strengths = np.mean(measure_beats, axis=0)
                    
                    # Score: how much stronger is beat 1 vs others?
                    if len(avg_strengths) > 1:
                        downbeat_ratio = avg_strengths[0] / (np.mean(avg_strengths[1:]) + 1e-6)
                        score = downbeat_ratio
                        
                        if score > best_score:
                            best_score = score
                            best_meter = meter
        
        # Determine confidence
        confidence = float(min(1.0, best_score / 2.0)) if best_score > 0 else 0.3
        
        # Map to time signature
        sig_map = {
            2: "2/4",
            3: "3/4",
            4: "4/4",
            6: "6/8",
        }
        
        return {
            "time_signature": sig_map.get(int(best_meter), "4/4"),
            "beats_per_measure": int(best_meter),
            "confidence": round(confidence, 2),
        }
    
    def analyze_full(
        self,
        audio_path: str | Path,
        detect_notes: bool = True,
        detect_chords: bool = True,
        min_note_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Run comprehensive audio analysis including tempo and time signature.
        
        Returns:
            Dict with notes, chords, tempo_info, time_signature_info
        """
        notes, chords = self.analyze(
            audio_path,
            detect_notes=detect_notes,
            detect_chords=detect_chords,
            min_note_confidence=min_note_confidence,
        )
        
        tempo_info = self.estimate_tempo(audio_path)
        time_sig_info = self.estimate_time_signature(audio_path)
        
        return {
            "notes": notes,
            "chords": chords,
            "tempo_info": tempo_info,
            "time_signature_info": time_sig_info,
        }
