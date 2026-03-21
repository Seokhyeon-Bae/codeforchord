"""Music theory constants and mappings."""

# Note names
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Enharmonic equivalents
ENHARMONIC_MAP = {
    "C#": "Db", "Db": "C#",
    "D#": "Eb", "Eb": "D#",
    "F#": "Gb", "Gb": "F#",
    "G#": "Ab", "Ab": "G#",
    "A#": "Bb", "Bb": "A#",
}

# Chord quality intervals (semitones from root)
CHORD_INTERVALS = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "diminished": [0, 3, 6],
    "augmented": [0, 4, 8],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dom7": [0, 4, 7, 10],
    "dim7": [0, 3, 6, 9],
    "half-dim7": [0, 3, 6, 10],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "add9": [0, 4, 7, 14],
}

# Chord symbol parsing patterns
CHORD_QUALITY_MAP = {
    "": "major",
    "m": "minor",
    "min": "minor",
    "-": "minor",
    "dim": "diminished",
    "o": "diminished",
    "aug": "augmented",
    "+": "augmented",
    "maj7": "maj7",
    "M7": "maj7",
    "7": "dom7",
    "m7": "min7",
    "min7": "min7",
    "-7": "min7",
    "dim7": "dim7",
    "o7": "dim7",
    "m7b5": "half-dim7",
    "ø7": "half-dim7",
    "sus2": "sus2",
    "sus4": "sus4",
    "add9": "add9",
}

# Simple guitar voicings (MIDI pitches for standard tuning, root on 6th string)
EASY_GUITAR_VOICINGS = {
    "C": [None, 3, 2, 0, 1, 0],   # x32010
    "D": [None, None, 0, 2, 3, 2], # xx0232
    "E": [0, 2, 2, 1, 0, 0],       # 022100
    "G": [3, 2, 0, 0, 0, 3],       # 320003
    "A": [None, 0, 2, 2, 2, 0],    # x02220
    "Am": [None, 0, 2, 2, 1, 0],   # x02210
    "Em": [0, 2, 2, 0, 0, 0],      # 022000
    "Dm": [None, None, 0, 2, 3, 1], # xx0231
}

# Supported instruments
INSTRUMENTS = ["piano", "guitar", "vocal"]

# MIDI constants
MIDI_MIN_VELOCITY = 1
MIDI_MAX_VELOCITY = 127
MIDI_DEFAULT_VELOCITY = 80
