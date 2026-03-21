"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def sample_note_data():
    """Sample note data for testing."""
    return {
        "pitch": 60,
        "start_time": 0.0,
        "end_time": 1.0,
        "velocity": 80,
        "confidence": 0.9,
    }


@pytest.fixture
def sample_chord_data():
    """Sample chord data for testing."""
    return {
        "symbol": "C",
        "root": "C",
        "quality": "major",
        "timestamp": 0.0,
        "duration": 2.0,
    }
