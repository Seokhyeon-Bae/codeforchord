# CodeForChord

**ML-driven music assistant app** that detects chords and notes from audio, generates sheet music, suggests melodies, and provides intelligent music arrangement tools.

---

## Tech Stack

### Frontend (Web)
- **Vue.js 3** with Vite for fast development
- **Pinia** for state management
- **Tailwind CSS** for modern, responsive UI
- **OpenSheetMusicDisplay** for rendering MusicXML sheet music
- **Web Audio API** for in-browser audio recording (exports to WAV)

### Mobile App (Native iOS)
- **SwiftUI** + **URLSession** — open `apps/ios/CodeForChord.xcodeproj` in **Xcode** and press Run (no Flutter / CocoaPods)
- **iOS 16+**, dark UI aligned with the web app
- See [apps/ios/docs/XCODE_AND_REMOTE.md](apps/ios/docs/XCODE_AND_REMOTE.md) for simulator, device IP, and CI
- **GitHub Actions** (`.github/workflows/ios-native.yml`) builds the app on **macOS** with `xcodebuild`

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
- Reduces storage costs while enhancing data-privacy and maintaining user experience

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
- **Xcode 15+** (macOS only — for the native iOS app)
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

### 4. Native iOS app (Xcode on a Mac)

```bash
open apps/ios/CodeForChord.xcodeproj
```

1. Select an **iPhone simulator** (or your device).
2. Press **Run** (⌘R).
3. Ensure the backend is on port **8000**. Default API URL is `http://127.0.0.1:8000` (simulator). On a **physical iPhone**, use the in-app **Settings** (gear) and set your Mac’s LAN IP, e.g. `http://192.168.1.10:8000`.

More detail: [apps/ios/docs/XCODE_AND_REMOTE.md](apps/ios/docs/XCODE_AND_REMOTE.md).

### 5. Train Rhythm Patterns (Optional)

To train the rhythm correction model with your own MusicXML files:

```bash
cd services/audio-processor
conda activate codeforchord

# Place MusicXML files in a folder, then run:
python scripts/train_patterns.py --input /path/to/your/musicxml/folder
```

---

## Deploying the web app (Vercel)

The **Vue** frontend in `apps/web` can be hosted on Vercel. The **Python API** must run elsewhere (e.g. Railway, Render, Azure, a VPS); point the UI at it with `VITE_API_URL`.

### Option A — Repository root (recommended for this monorepo)

1. Import the GitHub repo in Vercel; leave **Root Directory** empty (or `.`).
2. Vercel reads the root [`vercel.json`](vercel.json): installs and builds from `apps/web`, output `apps/web/dist`.
3. In **Project → Settings → Environment Variables**, add (Production / Preview as needed):
   - `VITE_API_URL` — your public API base URL, e.g. `https://api.yourdomain.com` (**no trailing slash**).
   - **`VITE_APP_ORIGIN`** — your deployed frontend origin, e.g. `https://your-app.vercel.app` (**no trailing slash**). Used as Auth0 `redirect_uri` and logout `returnTo` so it always matches **Allowed Callback URLs** in production.
   - Auth0: `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`.
4. Redeploy after changing env vars (they are baked in at **build** time for `VITE_*`).

### Option B — Root directory `apps/web`

1. Set **Root Directory** to `apps/web`.
2. Uses [`apps/web/vercel.json`](apps/web/vercel.json) (Vite preset + SPA rewrites). Build/install use that folder’s `package.json`.
3. Set the same `VITE_*` variables in Vercel.

### What the config does

- **SPA fallback**: unknown paths rewrite to `index.html` so client routing and refreshes work.
- **Caching**: long cache for `/assets/*` (Vite hashed filenames).
- **Headers**: `X-Content-Type-Options`, `Referrer-Policy`.
- **Node**: `apps/web/.nvmrc` and `package.json` `engines` prefer **Node 20+**.

### Auth0

Set **`VITE_APP_ORIGIN`** in Vercel to the same URL you list in Auth0 (e.g. `https://your-app.vercel.app`).

In the Auth0 dashboard (**Applications → your SPA → Settings**), add that exact URL to **Allowed Callback URLs**, **Allowed Logout URLs**, and **Allowed Web Origins**. For **Preview** deployments with different URLs, either add each preview URL, use an Auth0-allowed wildcard pattern for `*.vercel.app` if your plan supports it, or set **`VITE_APP_ORIGIN`** per Preview branch to the preview URL.

### CORS

The API uses permissive CORS in development; for production, restrict `allow_origins` to your Vercel domain in `services/audio-processor/app/main.py` if you tighten security.

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
│   ├── web/                    # Vue.js web frontend
│   │   ├── src/
│   │   │   ├── components/     # Vue components
│   │   │   ├── stores/         # Pinia stores
│   │   │   └── api/            # API client
│   │   ├── vercel.json         # Vercel (when Root Directory = apps/web)
│   │   └── package.json
│   └── ios/                    # Native SwiftUI iOS app
│       ├── CodeForChord.xcodeproj
│       ├── CodeForChord/       # Swift sources, Info.plist, assets
│       └── docs/
│           └── XCODE_AND_REMOTE.md
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
├── vercel.json                 # Vercel (monorepo build from repo root)
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL (set in Vercel for production builds) |
| `CFC_DEBUG` | `false` | Enable debug mode |
| `CFC_SAMPLE_RATE` | `22050` | Audio sample rate |
| `CFC_MAX_UPLOAD_SIZE` | `52428800` | Max upload size (50MB) |

---

## License

MIT
