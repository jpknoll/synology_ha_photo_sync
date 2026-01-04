"""Tests for SynologyPhotoSyncClient."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponse

from custom_components.synology_photo_sync.sync_client import SynologyPhotoSyncClient


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
def client(mock_hass, mock_session, tmp_path):
    """Create a SynologyPhotoSyncClient instance."""
    with patch(
        "custom_components.synology_photo_sync.sync_client.async_get_clientsession",
        return_value=mock_session,
    ):
        sources = [
            {
                "url": "https://example.com/mo/sharing/test123",
                "folder_name": "test_photos",
            }
        ]
        client = SynologyPhotoSyncClient(mock_hass, str(tmp_path), sources)
        return client


async def test_sync_source_success(client, mock_session, tmp_path):
    """Test successful sync of a source."""
    # Mock API list response
    list_response = MagicMock(spec=ClientResponse)
    list_response.status = 200
    list_response.json = AsyncMock(
        return_value={
            "success": True,
            "data": {
                "files": [
                    {
                        "name": "photo1.jpg",
                        "path": "/photo1.jpg",
                        "isdir": False,
                    },
                    {
                        "name": "photo2.png",
                        "path": "/photo2.png",
                        "isdir": False,
                    },
                    {
                        "name": "folder",
                        "path": "/folder",
                        "isdir": True,
                    },
                ]
            },
        }
    )

    # Mock download responses
    download_response1 = MagicMock(spec=ClientResponse)
    download_response1.status = 200
    download_response1.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0\x00\x10JFIF")

    download_response2 = MagicMock(spec=ClientResponse)
    download_response2.status = 200
    download_response2.read = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n")

    # Set up session.get to return an async context manager
    # Create async context managers for each response
    responses = [list_response, download_response1, download_response2]
    context_managers = []
    for resp in responses:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=resp)
        cm.__aexit__ = AsyncMock(return_value=False)
        context_managers.append(cm)
    
    # aiohttp session.get is a regular method that returns an async context manager
    mock_session.get = MagicMock(side_effect=context_managers)

    result = await client.sync_source("test_photos")

    assert result["success"] is True
    assert result["files_downloaded"] == 2
    assert result["source_name"] == "test_photos"

    # Verify files were created
    assert (tmp_path / "test_photos" / "photo1.jpg").exists()
    assert (tmp_path / "test_photos" / "photo2.png").exists()
    assert not (tmp_path / "test_photos" / "folder").exists()


async def test_sync_source_not_found(client):
    """Test sync when source is not found."""
    result = await client.sync_source("nonexistent")

    assert result["success"] is False
    assert "not found" in result["error"].lower()
    assert result["files_downloaded"] == 0


async def test_sync_source_no_url(client, tmp_path):
    """Test sync when source has no URL."""
    client._sources = [{"folder_name": "test_photos", "url": ""}]

    result = await client.sync_source("test_photos")

    assert result["success"] is False
    assert "no url" in result["error"].lower()
    assert result["files_downloaded"] == 0


async def test_sync_all_success(client, mock_session, tmp_path):
    """Test successful sync of all sources."""
    # Mock API list response
    list_response = MagicMock(spec=ClientResponse)
    list_response.status = 200
    list_response.json = AsyncMock(
        return_value={
            "success": True,
            "data": {
                "files": [
                    {
                        "name": "photo1.jpg",
                        "path": "/photo1.jpg",
                        "isdir": False,
                    }
                ]
            },
        }
    )

    # Mock download response
    download_response = MagicMock(spec=ClientResponse)
    download_response.status = 200
    download_response.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0\x00\x10JFIF")

    # Create async context managers for each response
    responses = [list_response, download_response]
    context_managers = []
    for resp in responses:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=resp)
        cm.__aexit__ = AsyncMock(return_value=False)
        context_managers.append(cm)
    
    # aiohttp session.get is a regular method that returns an async context manager
    mock_session.get = MagicMock(side_effect=context_managers)

    result = await client.sync_all()

    assert result["success"] is True
    assert result["total_downloaded"] == 1
    assert "test_photos" in result["sources"]


async def test_list_files_api_success(client, mock_session):
    """Test successful API list call."""
    response = MagicMock(spec=ClientResponse)
    response.status = 200
    response.json = AsyncMock(
        return_value={
            "success": True,
            "data": {
                "files": [
                    {"name": "photo1.jpg", "path": "/photo1.jpg", "isdir": False}
                ]
            },
        }
    )

    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    # aiohttp session.get is a regular method that returns an async context manager
    mock_session.get = MagicMock(return_value=context_manager)

    files = await client._list_files_via_api("https://example.com:5001", "test123")

    assert len(files) == 1
    assert files[0]["name"] == "photo1.jpg"


async def test_list_files_api_failure(client, mock_session):
    """Test API list call failure."""
    response = MagicMock(spec=ClientResponse)
    response.status = 200
    response.json = AsyncMock(return_value={"success": False, "error": {"code": 400}})

    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    # aiohttp session.get is a regular method that returns an async context manager
    mock_session.get = MagicMock(return_value=context_manager)

    files = await client._list_files_via_api("https://example.com:5001", "test123")

    assert len(files) == 0


async def test_download_file_api_success(client, mock_session, tmp_path):
    """Test successful file download via API."""
    response = MagicMock(spec=ClientResponse)
    response.status = 200
    response.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0\x00\x10JFIF")

    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    # aiohttp session.get is a regular method that returns an async context manager
    mock_session.get = MagicMock(return_value=context_manager)

    target_file = tmp_path / "test.jpg"
    result = await client._download_file_via_api(
        "https://example.com:5001", "test123", "/test.jpg", target_file
    )

    assert result is True
    assert target_file.exists()
    assert target_file.read_bytes() == b"\xff\xd8\xff\xe0\x00\x10JFIF"


async def test_download_file_api_not_image(client, mock_session, tmp_path):
    """Test download of non-image file."""
    response = MagicMock(spec=ClientResponse)
    response.status = 200
    response.read = AsyncMock(return_value=b"not an image")

    # Create async context manager mock
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    # aiohttp session.get is a regular method that returns an async context manager
    mock_session.get = MagicMock(return_value=context_manager)

    target_file = tmp_path / "test.txt"
    result = await client._download_file_via_api(
        "https://example.com:5001", "test123", "/test.txt", target_file
    )

    assert result is False
    assert not target_file.exists()


async def test_download_images_from_url_invalid_sharing_id(client, tmp_path):
    """Test download with invalid sharing URL."""
    with pytest.raises(ValueError, match="Could not extract sharing ID"):
        await client._download_images_from_url("https://example.com/invalid", tmp_path)


def test_is_image_jpeg(client):
    """Test JPEG image detection."""
    jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    assert client._is_image(jpeg_data) is True


def test_is_image_png(client):
    """Test PNG image detection."""
    png_data = b"\x89PNG\r\n\x1a\n"
    assert client._is_image(png_data) is True


def test_is_image_invalid(client):
    """Test invalid image detection."""
    invalid_data = b"not an image"
    assert client._is_image(invalid_data) is False


def test_sanitize_filename(client):
    """Test filename sanitization."""
    assert client._sanitize_filename("test<file>.jpg") == "test_file_.jpg"
    assert client._sanitize_filename("normal_file.jpg") == "normal_file.jpg"

