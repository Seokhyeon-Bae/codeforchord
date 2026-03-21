"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_info(self, client):
        """Test info endpoint."""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "supported_formats" in data
        assert "features" in data


class TestDetectionEndpoints:
    """Test detection endpoints (without actual audio files)."""
    
    def test_detect_health(self, client):
        """Test detection service health."""
        response = client.get("/detect/health")
        assert response.status_code == 200
    
    def test_detect_notes_no_file(self, client):
        """Test note detection without file."""
        response = client.post("/detect/notes")
        assert response.status_code == 422  # Validation error


class TestGenerationEndpoints:
    """Test generation endpoints."""
    
    def test_generate_health(self, client):
        """Test generation service health."""
        response = client.get("/generate/health")
        assert response.status_code == 200
    
    def test_melody_from_chords(self, client):
        """Test melody generation from chord JSON."""
        chords_data = {
            "chords": [
                {
                    "symbol": "C",
                    "root": "C",
                    "quality": "major",
                    "timestamp": 0.0,
                    "duration": 2.0,
                },
                {
                    "symbol": "G",
                    "root": "G",
                    "quality": "major",
                    "timestamp": 2.0,
                    "duration": 2.0,
                },
            ],
            "duration": 4.0,
        }
        
        response = client.post(
            "/generate/melody/from-chords",
            json=chords_data,
            params={"style": "simple", "tempo": 120},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "melody" in data
        assert "midi_base64" in data


class TestArrangementEndpoints:
    """Test arrangement endpoints."""
    
    def test_arrange_health(self, client):
        """Test arrangement service health."""
        response = client.get("/arrange/health")
        assert response.status_code == 200
    
    def test_transpose_chords(self, client):
        """Test chord transposition."""
        chords_data = {
            "chords": [
                {
                    "symbol": "C",
                    "root": "C",
                    "quality": "major",
                    "timestamp": 0.0,
                    "duration": 2.0,
                },
            ],
            "duration": 2.0,
        }
        
        response = client.post(
            "/arrange/transpose/chords",
            json=chords_data,
            params={"semitones": 2},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chords"][0]["root"] == "D"
