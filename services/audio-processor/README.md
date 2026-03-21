# CodeForChord Audio Processor

A FastAPI-based audio processing service for chord detection, note extraction, and sheet music generation.

## Features

- **Note Detection**: Extract pitches from audio using Spotify's Basic Pitch
- **Chord Detection**: Identify chords using Chordino/NNLS-Chroma
- **Sheet Generation**: Create MusicXML and MIDI files
- **Melody Suggestion**: Generate melodies from chord progressions
- **Arrangement**: Transpose, simplify, and transform music

## Requirements

- Python 3.10 or 3.11
- VAMP plugin SDK (for Chordino)
- FFmpeg (for audio format conversion)

## Installation

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install libsndfile1 ffmpeg vamp-plugin-sdk
```

**macOS:**
```bash
brew install libsndfile ffmpeg vamp-plugin-sdk
```

**Windows:**
- Install FFmpeg from https://ffmpeg.org/
- Download VAMP SDK from https://vamp-plugins.org/

### 2. Install Chordino VAMP Plugin

Download from: https://code.soundsoftware.ac.uk/projects/nnls-chroma

Place the `.dll` (Windows), `.so` (Linux), or `.dylib` (macOS) files in:
- Windows: `C:\Program Files\Vamp Plugins\`
- Linux: `/usr/local/lib/vamp/`
- macOS: `/Library/Audio/Plug-Ins/Vamp/`

### 3. Install Python Dependencies

```bash
cd services/audio-processor
pip install -r requirements.txt
```

## Running the Service

### Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

```bash
docker build -t codeforchord-audio .
docker run -p 8000:8000 codeforchord-audio
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Detection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/detect/notes` | POST | Extract notes from audio |
| `/detect/chords` | POST | Extract chords from audio |
| `/detect/full` | POST | Full analysis (notes + chords) |

### Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate/sheet` | POST | Generate MusicXML/MIDI sheet |
| `/generate/sheet/download` | POST | Download generated sheet file |
| `/generate/melody` | POST | Generate melody from audio |
| `/generate/melody/from-chords` | POST | Generate melody from chord JSON |

### Arrangement

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/arrange/transpose` | POST | Transpose by semitones |
| `/arrange/convert-mode` | POST | Convert major/minor |
| `/arrange/simplify` | POST | Simplify chord voicings |
| `/arrange/jazzify` | POST | Add jazz extensions |
| `/arrange/full` | POST | Apply multiple transformations |

## Example Usage

### Detect Chords from Audio

```bash
curl -X POST "http://localhost:8000/detect/chords" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@song.mp3"
```

### Generate Sheet Music

```bash
curl -X POST "http://localhost:8000/generate/sheet" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@song.wav" \
  -F "output_format=musicxml" \
  -F "output_type=lead_sheet" \
  -F "title=My Song" \
  -F "tempo=120"
```

### Transpose and Download

```bash
curl -X POST "http://localhost:8000/arrange/transpose" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@song.mp3" \
  -F "semitones=2" \
  -F "output_format=midi" \
  --output transposed.mid
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CFC_DEBUG` | `false` | Enable debug mode |
| `CFC_SAMPLE_RATE` | `22050` | Audio sample rate |
| `CFC_MAX_UPLOAD_SIZE` | `52428800` | Max upload size (50MB) |
| `CFC_TEMP_DIR` | `./temp` | Temporary file directory |

## Project Structure

```
services/audio-processor/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   └── routes/          # API endpoints
│   │       ├── detect.py    # Detection routes
│   │       ├── generate.py  # Generation routes
│   │       └── arrange.py   # Arrangement routes
│   ├── services/            # Core business logic
│   │   ├── pitch_detector.py
│   │   ├── chord_detector.py
│   │   ├── sheet_generator.py
│   │   ├── midi_generator.py
│   │   ├── arranger.py
│   │   └── melody_suggester.py
│   ├── models/              # Pydantic models
│   └── core/                # Configuration
├── tests/                   # Test suite
├── requirements.txt
├── Dockerfile
└── README.md
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT
