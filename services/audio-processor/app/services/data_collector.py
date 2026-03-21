"""Data collector for MusicXML files from public sources."""

import asyncio
import aiohttp
import zipfile
import io
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, AsyncIterator, Tuple
from xml.etree import ElementTree as ET
import tempfile

from app.models.rhythm_patterns import (
    RhythmPattern,
    NoteDuration,
    PatternDatabase,
    TimeSignatureModel,
    BeatPositionStats,
)

logger = logging.getLogger(__name__)


class MusicXMLParser:
    """Parse MusicXML files to extract rhythm information."""
    
    # Duration type to quarter note length mapping
    DURATION_MAP = {
        "whole": 4.0,
        "half": 2.0,
        "quarter": 1.0,
        "eighth": 0.5,
        "16th": 0.25,
        "32nd": 0.125,
        "64th": 0.0625,
    }
    
    def __init__(self):
        self.namespaces = {}
    
    def parse_file(self, filepath: str | Path) -> Dict:
        """
        Parse a MusicXML file and extract rhythm information.
        
        Returns:
            Dict with keys: time_signatures, patterns, measures, duration_stats
        """
        filepath = Path(filepath)
        
        # Handle compressed MusicXML (.mxl)
        if filepath.suffix.lower() == ".mxl":
            return self._parse_mxl(filepath)
        
        # Parse regular XML
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        return self._parse_root(root)
    
    def parse_string(self, xml_content: str) -> Dict:
        """Parse MusicXML from string content."""
        root = ET.fromstring(xml_content)
        return self._parse_root(root)
    
    def _parse_mxl(self, filepath: Path) -> Dict:
        """Parse compressed MusicXML file."""
        with zipfile.ZipFile(filepath, 'r') as z:
            # Find the main XML file
            for name in z.namelist():
                if name.endswith('.xml') and not name.startswith('META-INF'):
                    with z.open(name) as f:
                        content = f.read().decode('utf-8')
                        return self.parse_string(content)
        
        raise ValueError(f"No MusicXML found in {filepath}")
    
    def _parse_root(self, root: ET.Element) -> Dict:
        """Parse the root element of MusicXML."""
        # Handle namespace
        ns = ''
        if root.tag.startswith('{'):
            ns = root.tag.split('}')[0] + '}'
        
        result = {
            "time_signatures": [],
            "patterns": [],
            "measures": [],
            "duration_stats": {},
            "total_measures": 0,
        }
        
        # Find all parts
        parts = root.findall(f'.//{ns}part')
        
        for part in parts:
            measures = part.findall(f'{ns}measure')
            result["total_measures"] = max(result["total_measures"], len(measures))
            
            current_time_sig = "4/4"
            current_divisions = 1
            current_beat_position = 0.0
            
            for measure in measures:
                measure_data = {
                    "durations": [],
                    "time_signature": current_time_sig,
                }
                
                # Check for time signature changes
                attributes = measure.find(f'{ns}attributes')
                if attributes is not None:
                    divisions = attributes.find(f'{ns}divisions')
                    if divisions is not None and divisions.text:
                        current_divisions = int(divisions.text)
                    
                    time = attributes.find(f'{ns}time')
                    if time is not None:
                        beats = time.find(f'{ns}beats')
                        beat_type = time.find(f'{ns}beat-type')
                        if beats is not None and beat_type is not None:
                            current_time_sig = f"{beats.text}/{beat_type.text}"
                            if current_time_sig not in result["time_signatures"]:
                                result["time_signatures"].append(current_time_sig)
                            measure_data["time_signature"] = current_time_sig
                
                # Reset beat position at start of measure
                current_beat_position = 0.0
                
                # Process notes and rests
                for element in measure:
                    tag = element.tag.replace(ns, '')
                    
                    if tag == 'note':
                        duration_elem = element.find(f'{ns}duration')
                        if duration_elem is not None and duration_elem.text:
                            # Duration in divisions
                            divisions_dur = int(duration_elem.text)
                            # Convert to quarter notes
                            quarter_dur = divisions_dur / current_divisions
                            
                            # Check if it's a rest
                            is_rest = element.find(f'{ns}rest') is not None
                            
                            # Check for chord (simultaneous notes)
                            is_chord = element.find(f'{ns}chord') is not None
                            
                            if not is_chord:
                                measure_data["durations"].append(quarter_dur)
                                
                                # Record beat position statistics
                                beat_key = str(round(current_beat_position % 4, 2))
                                if beat_key not in result["duration_stats"]:
                                    result["duration_stats"][beat_key] = {}
                                
                                dur_key = str(round(quarter_dur, 3))
                                result["duration_stats"][beat_key][dur_key] = \
                                    result["duration_stats"][beat_key].get(dur_key, 0) + 1
                                
                                current_beat_position += quarter_dur
                    
                    elif tag == 'forward':
                        duration_elem = element.find(f'{ns}duration')
                        if duration_elem is not None and duration_elem.text:
                            current_beat_position += int(duration_elem.text) / current_divisions
                    
                    elif tag == 'backup':
                        duration_elem = element.find(f'{ns}duration')
                        if duration_elem is not None and duration_elem.text:
                            current_beat_position -= int(duration_elem.text) / current_divisions
                
                if measure_data["durations"]:
                    result["measures"].append(measure_data)
                    
                    # Create pattern from measure
                    if len(measure_data["durations"]) >= 2:
                        pattern = RhythmPattern(
                            durations=measure_data["durations"],
                            time_signature=current_time_sig,
                            beat_count=int(current_time_sig.split("/")[0]),
                            frequency=1,
                        )
                        result["patterns"].append(pattern)
        
        return result


class DataCollector:
    """Collect MusicXML files from various public sources."""
    
    # Public domain MusicXML sources
    SOURCES = {
        "musescore": {
            "base_url": "https://musescore.com/api",
            "search_url": "https://musescore.com/sheetmusic",
        },
        "wikifonia": {
            "archive_url": "https://www.wikifonia.org",
        },
    }
    
    def __init__(self, data_dir: str | Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "training"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.parser = MusicXMLParser()
        self.database = PatternDatabase()
    
    async def collect_from_directory(self, directory: str | Path) -> int:
        """
        Collect MusicXML files from a local directory.
        
        Returns number of files processed.
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Directory {directory} does not exist")
            return 0
        
        count = 0
        for filepath in directory.rglob("*.xml"):
            try:
                await self._process_file(filepath)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to process {filepath}: {e}")
        
        for filepath in directory.rglob("*.mxl"):
            try:
                await self._process_file(filepath)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to process {filepath}: {e}")
        
        for filepath in directory.rglob("*.musicxml"):
            try:
                await self._process_file(filepath)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to process {filepath}: {e}")
        
        self.database.total_songs_analyzed = count
        return count
    
    async def _process_file(self, filepath: Path):
        """Process a single MusicXML file."""
        logger.info(f"Processing {filepath}")
        
        result = self.parser.parse_file(filepath)
        
        # Add patterns to database
        for pattern in result["patterns"]:
            self.database.add_pattern(pattern)
        
        # Update beat position statistics
        for beat_pos, durations in result["duration_stats"].items():
            for time_sig in result["time_signatures"] or ["4/4"]:
                model = self.database.get_model(time_sig)
                
                if beat_pos not in model.beat_position_stats:
                    model.beat_position_stats[beat_pos] = BeatPositionStats(
                        beat_position=float(beat_pos)
                    )
                
                stats = model.beat_position_stats[beat_pos]
                for dur_key, count in durations.items():
                    for _ in range(count):
                        stats.add_duration(float(dur_key))
    
    async def download_from_url(self, url: str, save_as: str = None) -> Optional[Path]:
        """Download a MusicXML file from URL."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to download {url}: HTTP {response.status}")
                        return None
                    
                    content = await response.read()
                    
                    # Determine filename
                    if save_as is None:
                        save_as = url.split("/")[-1]
                        if not save_as.endswith(('.xml', '.mxl', '.musicxml')):
                            save_as += '.xml'
                    
                    filepath = self.data_dir / save_as
                    filepath.write_bytes(content)
                    
                    return filepath
            
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                return None
    
    async def collect_sample_data(self, count: int = 100) -> int:
        """
        Generate sample training data from built-in patterns.
        
        This creates synthetic training data based on common rhythm patterns
        when external data sources are not available.
        """
        logger.info(f"Generating {count} sample patterns...")
        
        # Common rhythm patterns for 4/4 time
        common_patterns_4_4 = [
            # Basic patterns
            [1.0, 1.0, 1.0, 1.0],  # Four quarters
            [2.0, 2.0],            # Two halves
            [4.0],                 # Whole note
            [2.0, 1.0, 1.0],       # Half + two quarters
            [1.0, 1.0, 2.0],       # Two quarters + half
            
            # Eighth note patterns
            [0.5, 0.5, 1.0, 1.0, 1.0],
            [1.0, 0.5, 0.5, 1.0, 1.0],
            [1.0, 1.0, 0.5, 0.5, 1.0],
            [0.5, 0.5, 0.5, 0.5, 2.0],
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # All eighths
            
            # Syncopated patterns
            [0.5, 1.0, 0.5, 1.0, 1.0],
            [1.0, 0.5, 0.5, 0.5, 0.5, 1.0],
            [0.5, 1.5, 0.5, 1.5],
            
            # Dotted patterns
            [1.5, 0.5, 1.0, 1.0],
            [1.0, 1.5, 0.5, 1.0],
            [1.5, 0.5, 1.5, 0.5],
            
            # 16th note patterns
            [0.25, 0.25, 0.5, 1.0, 1.0, 1.0],
            [1.0, 0.25, 0.25, 0.25, 0.25, 1.0, 1.0],
        ]
        
        # Common patterns for 3/4 time
        common_patterns_3_4 = [
            [1.0, 1.0, 1.0],       # Three quarters
            [2.0, 1.0],            # Half + quarter
            [1.0, 2.0],            # Quarter + half
            [3.0],                 # Dotted half
            [0.5, 0.5, 1.0, 1.0],
            [1.0, 0.5, 0.5, 1.0],
            [0.5, 0.5, 0.5, 0.5, 1.0],
        ]
        
        # Common patterns for 6/8 time
        common_patterns_6_8 = [
            [1.5, 1.5],            # Two dotted quarters
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # Six eighths
            [1.0, 0.5, 1.0, 0.5],
            [0.5, 0.5, 0.5, 1.5],
            [1.5, 0.5, 0.5, 0.5],
        ]
        
        # Add patterns with varying frequencies
        patterns_added = 0
        
        for i, durations in enumerate(common_patterns_4_4):
            # More common patterns get higher frequency
            freq = max(1, count // len(common_patterns_4_4) - i)
            pattern = RhythmPattern(
                durations=durations,
                time_signature="4/4",
                beat_count=4,
                frequency=freq,
            )
            self.database.add_pattern(pattern)
            patterns_added += 1
        
        for i, durations in enumerate(common_patterns_3_4):
            freq = max(1, (count // 3) // len(common_patterns_3_4) - i)
            pattern = RhythmPattern(
                durations=durations,
                time_signature="3/4",
                beat_count=3,
                frequency=freq,
            )
            self.database.add_pattern(pattern)
            patterns_added += 1
        
        for i, durations in enumerate(common_patterns_6_8):
            freq = max(1, (count // 4) // len(common_patterns_6_8) - i)
            pattern = RhythmPattern(
                durations=durations,
                time_signature="6/8",
                beat_count=6,
                frequency=freq,
            )
            self.database.add_pattern(pattern)
            patterns_added += 1
        
        # Add beat position statistics
        self._add_beat_position_stats("4/4", 4)
        self._add_beat_position_stats("3/4", 3)
        self._add_beat_position_stats("6/8", 6)
        
        self.database.total_songs_analyzed = patterns_added
        
        logger.info(f"Generated {patterns_added} sample patterns")
        return patterns_added
    
    def _add_beat_position_stats(self, time_sig: str, beats: int):
        """Add common beat position statistics for a time signature."""
        model = self.database.get_model(time_sig)
        
        # Common subdivisions
        positions = []
        for beat in range(beats):
            positions.extend([beat, beat + 0.25, beat + 0.5, beat + 0.75])
        
        for pos in positions:
            pos_key = str(round(pos, 2))
            if pos_key not in model.beat_position_stats:
                model.beat_position_stats[pos_key] = BeatPositionStats(
                    beat_position=pos
                )
            
            stats = model.beat_position_stats[pos_key]
            
            # Add typical durations with frequencies
            # Downbeats tend to have longer notes
            if pos == int(pos):  # On the beat
                for _ in range(10):
                    stats.add_duration(1.0)
                for _ in range(5):
                    stats.add_duration(2.0)
                for _ in range(3):
                    stats.add_duration(0.5)
            elif pos % 0.5 == 0:  # On eighth note
                for _ in range(8):
                    stats.add_duration(0.5)
                for _ in range(4):
                    stats.add_duration(1.0)
                for _ in range(2):
                    stats.add_duration(0.25)
            else:  # On sixteenth note
                for _ in range(6):
                    stats.add_duration(0.25)
                for _ in range(3):
                    stats.add_duration(0.5)
    
    def save_database(self, path: str | Path = None):
        """Save the pattern database to disk."""
        if path is None:
            path = self.data_dir / "patterns.json"
        
        self.database.save(path)
        logger.info(f"Saved pattern database to {path}")
    
    def load_database(self, path: str | Path = None) -> PatternDatabase:
        """Load pattern database from disk."""
        if path is None:
            path = self.data_dir / "patterns.json"
        
        self.database = PatternDatabase.load(path)
        logger.info(f"Loaded pattern database from {path}")
        return self.database
    
    def get_database(self) -> PatternDatabase:
        """Get the current pattern database."""
        return self.database
