"""
CodeForChord Audio Processor

FastAPI application for audio analysis, chord detection, and sheet music generation.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import detect_router, generate_router, arrange_router, audio_router, sheets_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()

    # Create temp directory if it doesn't exist
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)

    # Initialize storage services if Azure and MongoDB are configured
    app.state.mongo = None
    app.state.blob = None
    app.state.audio_storage = None
    app.state.lru_task = None

    if settings.azure_storage_connection_string and settings.mongodb_url:
        from app.services.mongo_service import MongoService
        from app.services.azure_blob_service import AzureBlobService
        from app.services.audio_storage_service import AudioStorageService
        from app.services.lru_eviction_service import LRUEvictionService, EvictionConfig

        mongo = MongoService(settings.mongodb_url, settings.mongodb_database)
        await mongo.create_indexes()
        app.state.mongo = mongo

        blob = AzureBlobService(
            connection_string=settings.azure_storage_connection_string,
            account_name=settings.azure_storage_account_name,
            account_key=settings.azure_storage_account_key,
        )
        await blob.ensure_container(settings.azure_container_uploads)
        await blob.ensure_container(settings.azure_container_recordings)
        app.state.blob = blob

        app.state.audio_storage = AudioStorageService(
            mongo=mongo,
            blob=blob,
            container_uploads=settings.azure_container_uploads,
            container_recordings=settings.azure_container_recordings,
            sas_expiry_minutes=settings.azure_sas_expiry_minutes,
            max_upload_size_bytes=settings.azure_max_upload_size_bytes,
        )

        eviction_cfg = EvictionConfig(
            max_storage_bytes=settings.azure_max_storage_bytes,
            audio_ttl_hours=settings.azure_audio_ttl_hours,
            min_retention_hours=settings.azure_audio_min_retention_hours,
            interval_seconds=settings.lru_interval_seconds,
            batch_size=settings.lru_eviction_batch_size,
        )
        lru = LRUEvictionService(mongo=mongo, blob=blob, config=eviction_cfg)
        app.state.lru_task = asyncio.create_task(lru.run_forever())

    yield

    # Shutdown
    if app.state.lru_task:
        app.state.lru_task.cancel()
        try:
            await app.state.lru_task
        except asyncio.CancelledError:
            pass
    if app.state.blob:
        await app.state.blob.close()
    if app.state.mongo:
        await app.state.mongo.close()


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
    app.include_router(audio_router)
    app.include_router(sheets_router)
    
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
            "input": [".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"],
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
