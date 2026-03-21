"""
CodeForChord Audio Processor

FastAPI application for audio analysis, chord detection, and sheet music generation.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import detect_router, generate_router, arrange_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()
    
    # Create temp directory if it doesn't exist
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Cleanup on shutdown (optional: clear temp files)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="""
## CodeForChord Audio Processor

A powerful API for music analysis and generation:

### Features

- **Note Detection**: Extract pitches from audio using Spotify's Basic Pitch
- **Chord Detection**: Identify chords using Chordino algorithm
- **Sheet Generation**: Create MusicXML and MIDI files
- **Melody Suggestion**: Generate melodies from chord progressions
- **Arrangement**: Transpose, simplify, and transform music

### Supported Instruments

- Piano
- Guitar  
- Vocal

### Output Formats

- MusicXML (compatible with MuseScore, Finale, etc.)
- MIDI
- JSON
        """,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(detect_router)
    app.include_router(generate_router)
    app.include_router(arrange_router)
    
    return app


# Create app instance
app = create_app()


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "endpoints": {
            "detection": "/detect",
            "generation": "/generate",
            "arrangement": "/arrange",
        }
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "detection": "available",
            "generation": "available",
            "arrangement": "available",
        }
    }


@app.get("/info", tags=["info"])
async def info():
    """Get API information and capabilities."""
    return {
        "supported_formats": {
            "input": [".wav", ".mp3", ".flac", ".ogg", ".m4a"],
            "output": ["musicxml", "midi", "json"],
        },
        "supported_instruments": ["piano", "guitar", "vocal"],
        "features": {
            "detection": {
                "notes": "Polyphonic pitch detection with Basic Pitch",
                "chords": "Chord recognition with Chordino",
            },
            "generation": {
                "lead_sheet": "Melody with chord symbols",
                "chords_only": "Chord chart without melody",
                "full_score": "Complete arrangement with accompaniment",
            },
            "arrangement": {
                "transpose": "Shift by -12 to +12 semitones",
                "mode_conversion": "Major to minor or vice versa",
                "simplify": "Convert complex chords to easy voicings",
                "jazzify": "Add seventh extensions to triads",
            },
            "melody": {
                "styles": ["simple", "arpeggiated", "scalar", "rhythmic"],
                "options": ["passing_tones", "neighbor_tones", "density"],
            },
        },
        "limits": {
            "max_file_size": "50MB",
            "max_duration": "No limit (processing time varies)",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
