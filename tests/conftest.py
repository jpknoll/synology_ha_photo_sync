"""Pytest configuration for Synology Photo Sync tests."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.synology_photo_sync.const import DOMAIN

# Patch HomeAssistant Config.set_time_zone at import time to handle US/Pacific deprecation
try:
    from homeassistant.core import Config
    
    # Store original method
    _original_set_time_zone = Config.set_time_zone
    
    # Create patched version
    def _patched_set_time_zone(self, time_zone_str):
        """Patch set_time_zone to convert deprecated US/Pacific to America/Los_Angeles."""
        if time_zone_str == "US/Pacific":
            time_zone_str = "America/Los_Angeles"
        return _original_set_time_zone(self, time_zone_str)
    
    # Replace the method
    Config.set_time_zone = _patched_set_time_zone
except (ImportError, AttributeError):
    # If patching fails, continue anyway
    pass


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    return hass


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_sources():
    """Sample source configuration."""
    return [
        {
            "url": "https://example.com/mo/sharing/test123",
            "folder_name": "test_photos",
        }
    ]


