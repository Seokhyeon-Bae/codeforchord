# CodeForChord

**ML-driven music assistant app** that detects chords and notes from audio, generates sheet music, suggests melodies, and provides intelligent music arrangement tools.

---

## Tech Stack

### Frontend
- **Vue.js 3** with Vite for fast development
- **Pinia** for state management
- **Tailwind CSS** for modern, responsive UI
- **OpenSheetMusicDisplay** for rendering MusicXML sheet music
- **Web Audio API** for in-browser audio recording (exports to WAV)

### Backend
- **Python 3.11** with FastAPI for high-performance async API
- **Basic Pitch** (Spotify) for ML-based note/pitch detection
- **Librosa** for audio analysis and chord detection
- **Music21** for MusicXML generation and music theory operations
- **MIDIUtil** for MIDI file generation

### Database & Authentication
- **MongoDB** - User data, history, saved sheets, and preferences
- **Auth0** - Secure authentication and user privacy protection
- **Azure Blob Storage** - Cloud storage for audio recordings (with LRU cache policy)

---

## Features

### Core Features
- **Chord Detection** - Identify chords from uploaded or recorded audio
- **Note Extraction** - Extract individual pitches using ML-based pitch detection
- **Sheet Music Generation** - Generate professional piano sheets (grand staff with treble/bass clefs)
- **Live Recording** - Record audio directly in the browser, converts to WAV format
- **Auto Tempo/Time Signature Detection** - Automatically detects BPM and time signature

### Music Arrangement
- **Transpose** - Shift music up/down by semitones
- **Mode Conversion** - Convert between major and minor keys
- **Chord Simplification** - Simplify complex chords for easier playing
- **Melody Suggestion** - Generate complementary melodies from chord progressions

### Export Options
- **MusicXML** - Standard format for notation software (MuseScore, Finale, etc.)
- **MIDI** - For DAWs and music production software
- **Download** - Save generated sheets and audio recordings locally

---

## Data Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Audio Input    │────▶│  Audio Processor │────▶│  Sheet Output   │
│  (Upload/Record)│     │  (FastAPI)       │     │  (MusicXML/MIDI)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Azure Blob     │     │  MongoDB         │     │  User Download  │
│  Storage        │     │  (History/Data)  │     │                 │
│  (LRU Cache)    │     └──────────────────┘     └─────────────────┘
└─────────────────┘
```

### Azure Storage with LRU Cache
- Audio recordings are stored in **Azure Blob Storage**
- **LRU (Least Recently Used) cache policy** manages storage space efficiently
- Frequently accessed recordings remain available; old unused files are automatically cleaned up
- Reduces storage costs while maintaining user experience

### Processing Pipeline
1. **Audio Input** → Upload file or record in browser
2. **Preprocessing** → Convert to standard format, normalize audio
3. **ML Detection** → Basic Pitch extracts notes, Librosa analyzes chords
4. **Rhythm Correction** → Apply learned patterns to improve accuracy
5. **Sheet Generation** → Music21 creates properly formatted notation
6. **Export** → MusicXML or MIDI output

---

## ML Techniques

### Note Detection (Basic Pitch)
- Uses **Spotify's Basic Pitch** neural network
- Trained on large datasets of polyphonic music
- Outputs MIDI note numbers, onset times, durations, and velocities
- Handles multiple simultaneous notes (polyphonic detection)

### Chord Detection
- **Chroma feature extraction** using Librosa
- **Template matching** against known chord patterns (major, minor, 7th, diminished, etc.)
- Analyzes harmonic content across time windows

### Rhythm Correction System
We trained a custom rhythm correction model using MusicXML training data:

#### Training Process
1. **Data Collection** - Collected MusicXML files from professional sheet music
2. **Pattern Extraction** - Analyzed rhythm patterns, beat positions, and note durations
3. **Statistical Learning** - Built probability distributions for:
   - Common duration values at each beat position
   - Typical rhythm patterns in different time signatures
   - Note groupings and phrase structures

#### How It Works
```python
# Training: Extract patterns from MusicXML files
python scripts/train_patterns.py --input ./musicxml_folder

# Runtime: Apply learned patterns to detected notes
corrector.correct(notes, correction_strength=0.5)
```

#### Correction Algorithm
1. **Beat Grid Snapping** - Aligns note onsets to nearest beat subdivision
2. **Duration Quantization** - Maps raw durations to standard musical values
3. **Pattern Matching** - Compares detected rhythms against learned patterns
4. **Weighted Blending** - Adjusts based on `correction_strength` (0.0 - 1.0)

The trained pattern database (`data/patterns.json`) contains:
- 500+ rhythm patterns from professional sheet music
- Beat position statistics for common time signatures
- Duration frequency distributions

---

## How to Run the Code

### Prerequisites
- **Python 3.11** (recommended: use Conda)
- **Node.js 18+** and npm
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/codeforchord.git
cd codeforchord
```

### 2. Set Up the Backend

```bash
# Create and activate conda environment
conda create -n codeforchord python=3.11 -y
conda activate codeforchord

# Install Python dependencies
cd services/audio-processor
pip install -r requirements.txt

# Run the backend server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. Set Up the Frontend

```bash
# In a new terminal
cd apps/web

# Install dependencies
npm install

# Run the development server
npm run dev
```

The web app will be available at `http://localhost:3000` (or next available port)

### 4. Train Rhythm Patterns (Optional)

To train the rhythm correction model with your own MusicXML files:

```bash
cd services/audio-processor
conda activate codeforchord

# Place MusicXML files in a folder, then run:
python scripts/train_patterns.py --input /path/to/your/musicxml/folder
```

---

## API Endpoints

### Detection
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/detect/notes` | POST | Extract notes from audio |
| `/detect/chords` | POST | Extract chords from audio |
| `/detect/full` | POST | Full analysis (notes + chords + tempo + time signature) |

### Generation
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate/sheet` | POST | Generate MusicXML sheet music |
| `/generate/melody` | POST | Generate melody from audio |

### Arrangement
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/arrange/transpose` | POST | Transpose by semitones |
| `/arrange/convert-mode` | POST | Convert major/minor |
| `/arrange/simplify` | POST | Simplify chord voicings |

---

## Project Structure

```
codeforchord/
├── apps/
│   └── web/                    # Vue.js frontend
│       ├── src/
│       │   ├── components/     # Vue components
│       │   ├── stores/         # Pinia stores
│       │   └── api/            # API client
│       └── package.json
├── services/
│   └── audio-processor/        # Python backend
│       ├── app/
│       │   ├── api/routes/     # FastAPI endpoints
│       │   ├── services/       # Core ML/audio processing
│       │   ├── models/         # Pydantic data models
│       │   └── core/           # Configuration
│       ├── data/
│       │   └── patterns.json   # Trained rhythm patterns
│       ├── scripts/
│       │   └── train_patterns.py
│       └── requirements.txt
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |
| `CFC_DEBUG` | `false` | Enable debug mode |
| `CFC_SAMPLE_RATE` | `22050` | Audio sample rate |
| `CFC_MAX_UPLOAD_SIZE` | `52428800` | Max upload size (50MB) |

---

## License

MIT
