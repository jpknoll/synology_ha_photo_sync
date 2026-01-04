"""Tests for __init__.py."""
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.synology_photo_sync import async_setup, async_setup_entry


async def test_async_setup(hass: HomeAssistant):
    """Test async_setup."""
    result = await async_setup(hass, {})
    assert result is True


async def test_async_setup_entry(hass: HomeAssistant):
    """Test async_setup_entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {
        "name": "Test Sync",
        "sources": [
            {
                "url": "https://example.com/mo/sharing/test123",
                "folder_name": "test_photos",
            }
        ],
    }
    entry.entry_id = "test_entry"
    entry.runtime_data = None

    with patch(
        "custom_components.synology_photo_sync.SynologyPhotoSyncClient"
    ) as mock_client_class, patch(
        "custom_components.synology_photo_sync.dr.async_get"
    ) as mock_dr, patch.object(
        hass.config_entries, "async_forward_entry_setups", return_value=True
    ) as mock_forward:
        mock_dr.return_value.async_get_or_create = MagicMock()
        mock_forward.return_value = True

        result = await async_setup_entry(hass, entry)

        assert result is True
        mock_client_class.assert_called_once()
        mock_dr.return_value.async_get_or_create.assert_called_once()

