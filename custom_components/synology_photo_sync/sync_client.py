"""Sync client for downloading images from Synology sharing links using DSM API."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import SUPPORTED_IMAGE_EXTENSIONS

_LOGGER = logging.getLogger(__name__)


class SynologyPhotoSyncClient:
    """Client for syncing photos from Synology sharing links."""

    def __init__(self, hass: HomeAssistant, data_dir: str, sources: list[dict[str, str]]) -> None:
        """Initialize the sync client."""
        self._hass = hass
        self._data_dir = Path(data_dir)
        self._sources = sources
        self._session = async_get_clientsession(hass)

        # Create data directory if it doesn't exist
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def sync_all(self) -> dict[str, Any]:
        """Sync all configured sources."""
        results = {
            "success": True,
            "total_downloaded": 0,
            "sources": {},
            "error": None,
        }

        for source in self._sources:
            source_name = source.get("folder_name", "default")
            url = source.get("url", "")
            
            if not url:
                _LOGGER.warning(f"Skipping source {source_name}: no URL provided")
                continue

            try:
                result = await self.sync_source(source_name)
                if result["success"]:
                    results["total_downloaded"] += result.get("files_downloaded", 0)
                    results["sources"][source_name] = result
                else:
                    results["success"] = False
                    results["error"] = result.get("error", "Unknown error")
                    results["sources"][source_name] = result
            except Exception as e:
                _LOGGER.exception(f"Error syncing source {source_name}")
                results["success"] = False
                results["error"] = str(e)
                results["sources"][source_name] = {
                    "success": False,
                    "error": str(e),
                }

        return results

    async def sync_source(self, source_name: str) -> dict[str, Any]:
        """Sync a specific source by name."""
        # Find the source configuration
        source_config = None
        for source in self._sources:
            if source.get("folder_name") == source_name:
                source_config = source
                break

        if not source_config:
            return {
                "success": False,
                "error": f"Source '{source_name}' not found",
                "files_downloaded": 0,
            }

        url = source_config.get("url", "")
        if not url:
            return {
                "success": False,
                "error": f"No URL configured for source '{source_name}'",
                "files_downloaded": 0,
            }

        # Create folder for this source
        source_folder = self._data_dir / source_name
        source_folder.mkdir(parents=True, exist_ok=True)

        try:
            files_downloaded = await self._download_images_from_url(url, source_folder)
            return {
                "success": True,
                "files_downloaded": files_downloaded,
                "source_name": source_name,
            }
        except Exception as e:
            _LOGGER.exception(f"Error syncing source {source_name}")
            return {
                "success": False,
                "error": str(e),
                "files_downloaded": 0,
            }

    async def _download_images_from_url(self, url: str, target_folder: Path) -> int:
        """Download images from a Synology sharing URL using DSM API."""
        _LOGGER.info(f"Starting download from {url} to {target_folder}")

        # Parse the sharing URL to extract the sharing ID and base URL
        parsed_url = urlparse(url)
        sharing_id = None
        
        # Extract sharing ID from path like /mo/sharing/dRCQK2EDv
        path_match = re.search(r'/sharing/([^/]+)', parsed_url.path)
        if path_match:
            sharing_id = path_match.group(1)
        else:
            raise ValueError(f"Could not extract sharing ID from URL: {url}")

        # Build the base API URL
        # For QuickConnect URLs, we need to use the DSM port (5001 for HTTPS, 5000 for HTTP)
        # Extract host and port from netloc
        netloc = parsed_url.netloc
        if ':' in netloc:
            host, port = netloc.rsplit(':', 1)
        else:
            host = netloc
            # Default to DSM ports: 5001 for HTTPS, 5000 for HTTP
            port = '5001' if parsed_url.scheme == 'https' else '5000'
        
        # Construct base URL for API calls
        base_url = f"{parsed_url.scheme}://{host}:{port}"
        
        files_downloaded = 0

        try:
            # Use Synology DSM API to list and download files
            files_downloaded = await self._sync_via_api(base_url, sharing_id, target_folder)
        except asyncio.TimeoutError:
            raise Exception("Timeout while accessing Synology API")
        except Exception as e:
            _LOGGER.exception(f"Error downloading from {url}")
            raise

        _LOGGER.info(f"Downloaded {files_downloaded} files from {url}")
        return files_downloaded

    async def _sync_via_api(self, base_url: str, sharing_id: str, target_folder: Path) -> int:
        """Sync files using Synology DSM FileStation API."""
        files_downloaded = 0
        
        # Step 1: List files in the sharing link
        file_list = await self._list_files_via_api(base_url, sharing_id)
        
        if not file_list:
            _LOGGER.warning("No files found in sharing link")
            return 0
        
        _LOGGER.info(f"Found {len(file_list)} files in sharing link")
        
        # Step 2: Filter for image files and download them
        for file_info in file_list:
            file_path = file_info.get('path', '')
            file_name = file_info.get('name', '')
            is_dir = file_info.get('isdir', False)
            
            # Skip directories for now (could be enhanced to recurse)
            if is_dir:
                _LOGGER.debug(f"Skipping directory: {file_name}")
                continue
            
            # Check if it's an image file
            if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_IMAGE_EXTENSIONS):
                _LOGGER.debug(f"Skipping non-image file: {file_name}")
                continue
            
            # Check if file already exists locally
            local_file_path = target_folder / file_name
            if local_file_path.exists():
                _LOGGER.debug(f"File already exists, skipping: {file_name}")
                continue
            
            # Download the file
            if await self._download_file_via_api(base_url, sharing_id, file_path, local_file_path):
                files_downloaded += 1
        
        return files_downloaded

    async def _list_files_via_api(self, base_url: str, sharing_id: str) -> list[dict[str, Any]]:
        """List files in a sharing link using SYNO.FileStation.List API."""
        api_params = {
            'api': 'SYNO.FileStation.List',
            'version': '2',
            'method': 'list',
            '_sharing_id': sharing_id,
            'folder_path': '/',
            'additional': '["size","time","perm"]',
        }
        
        api_url = f"{base_url}/webapi/entry.cgi?{urlencode(api_params)}"
        
        try:
            async with async_timeout.timeout(30):
                async with self._session.get(api_url) as response:
                    if response.status != 200:
                        _LOGGER.warning(f"API list request failed: HTTP {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    # Check for API success
                    if not data.get('success', False):
                        error_code = data.get('error', {}).get('code', 'unknown')
                        _LOGGER.error(f"API list request failed: {error_code}")
                        return []
                    
                    # Extract file list from response
                    files = data.get('data', {}).get('files', [])
                    return files
                    
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while listing files via API")
            return []
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Failed to parse API response: {e}")
            return []
        except Exception as e:
            _LOGGER.exception(f"Error listing files via API: {e}")
            return []

    async def _download_file_via_api(
        self, 
        base_url: str, 
        sharing_id: str, 
        file_path: str, 
        target_file_path: Path
    ) -> bool:
        """Download a file using SYNO.FileStation.Download API."""
        api_params = {
            'api': 'SYNO.FileStation.Download',
            'version': '2',
            'method': 'download',
            '_sharing_id': sharing_id,
            'path': file_path,
            'mode': 'download',
        }
        
        api_url = f"{base_url}/webapi/entry.cgi?{urlencode(api_params)}"
        
        try:
            async with async_timeout.timeout(60):
                async with self._session.get(api_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Verify it's actually an image by checking magic bytes
                        if not self._is_image(content):
                            _LOGGER.warning(f"Downloaded content is not an image: {file_path}")
                            return False
                        
                        # Write file
                        target_file_path.write_bytes(content)
                        _LOGGER.info(f"Downloaded: {target_file_path.name}")
                        return True
                    else:
                        _LOGGER.warning(f"Failed to download {file_path}: HTTP {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout while downloading {file_path}")
            return False
        except Exception as e:
            _LOGGER.exception(f"Error downloading file {file_path}: {e}")
            return False


    def _is_image(self, content: bytes) -> bool:
        """Check if content is an image by checking magic bytes."""
        if len(content) < 4:
            return False
        
        # Check common image magic bytes
        magic_bytes = content[:4]
        
        # JPEG: FF D8 FF
        if magic_bytes[:3] == b'\xff\xd8\xff':
            return True
        # PNG: 89 50 4E 47
        if magic_bytes == b'\x89PNG':
            return True
        # GIF: 47 49 46 38
        if magic_bytes[:4] == b'GIF8':
            return True
        # BMP: 42 4D
        if magic_bytes[:2] == b'BM':
            return True
        # WEBP: RIFF...WEBP
        if content[:4] == b'RIFF' and b'WEBP' in content[:12]:
            return True
        
        return False

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to remove invalid characters."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

