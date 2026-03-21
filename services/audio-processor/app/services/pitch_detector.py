"""Pitch detection service using Spotify's Basic Pitch."""

import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

from app.models.note import DetectedNote, NoteList
from app.core.config import get_settings


class PitchDetector:
    """Wrapper around Basic Pitch for note/pitch detection from audio."""
    
    def __init__(
        self,
        onset_threshold: float = 0.5,
        frame_threshold: float = 0.3,
        min_note_length: float = 0.058,
        min_frequency: Optional[float] = None,
        max_frequency: Optional[float] = None,
    ):
        self.onset_threshold = onset_threshold
        self.frame_threshold = frame_threshold
        self.min_note_length = min_note_length
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency
        self.settings = get_settings()
    
    def detect(self, audio_path: str | Path) -> NoteList:
        """
        Extract notes from audio file using Basic Pitch.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            NoteList containing all detected notes
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Run Basic Pitch prediction
        model_output, midi_data, note_events = predict(
            str(audio_path),
            onset_threshold=self.onset_threshold,
            frame_threshold=self.frame_threshold,
            minimum_note_length=self.min_note_length,
            minimum_frequency=self.min_frequency,
            maximum_frequency=self.max_frequency,
        )
        
        # Convert note_events to DetectedNote objects
        notes = self._convert_note_events(note_events, model_output)
        
        # Calculate audio duration from model output
        duration = self._get_audio_duration(model_output)
        
        return NoteList(
            notes=notes,
            source_file=str(audio_path.name),
            duration=duration,
            sample_rate=self.settings.sample_rate,
        )
    
    def detect_from_bytes(self, audio_data: bytes, file_extension: str = ".wav") -> NoteList:
        """
        Detect notes from audio bytes.
        
        Args:
            audio_data: Raw audio file bytes
            file_extension: File extension (e.g., ".wav", ".mp3")
            
        Returns:
            NoteList containing all detected notes
        """
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = Path(tmp.name)
        
        try:
            return self.detect(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def _convert_note_events(
        self, 
        note_events: list, 
        model_output: dict
    ) -> list[DetectedNote]:
        """
        Convert Basic Pitch note events to DetectedNote objects.
        
        Note events format from Basic Pitch:
        [(start_time, end_time, pitch, velocity, [pitch_bend])]
        """
        notes = []
        
        for event in note_events:
            start_time = float(event[0])
            end_time = float(event[1])
            pitch = int(event[2])
            # Ensure velocity is at least 1 (MIDI valid range is 1-127)
            velocity = max(1, min(127, int(event[3])))
            
            # Handle optional pitch bend - may be a list or single value
            pitch_bend = None
            if len(event) > 4 and event[4] is not None:
                pb = event[4]
                # Basic Pitch may return an array of pitch bends - take the mean
                if isinstance(pb, (list, np.ndarray)):
                    if len(pb) > 0:
                        pitch_bend = float(np.mean(pb))
                else:
                    pitch_bend = float(pb)
            
            # Estimate confidence from model activation
            confidence = self._estimate_confidence(
                model_output, start_time, end_time, pitch
            )
            
            notes.append(DetectedNote(
                pitch=pitch,
                start_time=start_time,
                end_time=end_time,
                velocity=velocity,
                confidence=confidence,
                pitch_bend=pitch_bend,
            ))
        
        return sorted(notes, key=lambda n: (n.start_time, n.pitch))
    
    def _estimate_confidence(
        self, 
        model_output: dict, 
        start_time: float, 
        end_time: float, 
        pitch: int
    ) -> float:
        """
        Estimate detection confidence from model activations.
        
        Uses the mean activation value in the note region.
        """
        try:
            note_activation = model_output.get("note")
            if note_activation is None:
                return 1.0
            
            # Basic Pitch uses ~43 fps (frames per second)
            fps = 43.0
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            
            # Pitch range in Basic Pitch is 21-108 (88 piano keys)
            pitch_idx = pitch - 21
            
            if 0 <= pitch_idx < note_activation.shape[1]:
                region = note_activation[start_frame:end_frame, pitch_idx]
                if len(region) > 0:
                    return float(np.mean(region))
        except Exception:
            pass
        
        return 1.0
    
    def _get_audio_duration(self, model_output: dict) -> float:
        """Calculate audio duration from model output."""
        try:
            note_activation = model_output.get("note")
            if note_activation is not None:
                # Basic Pitch uses ~43 fps
                return note_activation.shape[0] / 43.0
        except Exception:
            pass
        return 0.0
    
    def get_midi_data(self, audio_path: str | Path) -> Tuple[bytes, NoteList]:
        """
        Get both MIDI data and note list from audio.
        
        Returns:
            Tuple of (MIDI bytes, NoteList)
        """
        audio_path = Path(audio_path)
        
        model_output, midi_data, note_events = predict(
            str(audio_path),
            onset_threshold=self.onset_threshold,
            frame_threshold=self.frame_threshold,
            minimum_note_length=self.min_note_length,
        )
        
        notes = self._convert_note_events(note_events, model_output)
        duration = self._get_audio_duration(model_output)
        
        note_list = NoteList(
            notes=notes,
            source_file=str(audio_path.name),
            duration=duration,
        )
        
        # Convert MIDI object to bytes
        import io
        midi_buffer = io.BytesIO()
        midi_data.write(midi_buffer)
        midi_bytes = midi_buffer.getvalue()
        
        return midi_bytes, note_list
