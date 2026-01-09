"""Scraper for Synology Photos sharing page."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp

_LOGGER = logging.getLogger(__name__)


class SynologyPhotoScraper:
    """Scraper for Synology Photos sharing pages."""

    def __init__(self, sharing_url: str, session: aiohttp.ClientSession) -> None:
        """Initialize the scraper."""
        self.sharing_url = sharing_url
        self.session = session
        self.base_url = None
        self.passphrase = None
        self._extract_url_info()

    def _extract_url_info(self) -> None:
        """Extract base URL and passphrase from sharing URL."""
        parsed = urlparse(self.sharing_url)
        # Extract passphrase from path (e.g., /mo/sharing/dRCQK2EDv)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 3 and path_parts[0] == "mo" and path_parts[1] == "sharing":
            self.passphrase = path_parts[2]
        
        # Build base URL
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

    async def fetch_page(self) -> str:
        """Fetch the sharing page HTML."""
        try:
            async with self.session.get(self.sharing_url) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            _LOGGER.error("Failed to fetch sharing page: %s", e)
            raise

    async def get_album_info(self) -> dict[str, Any] | None:
        """Get album information by calling the API endpoint."""
        if not self.passphrase:
            _LOGGER.error("No passphrase found in URL")
            return None

        api_url = f"{self.base_url}/mo/sharing/webapi/entry.cgi/SYNO.Foto.Browse.Album"
        
        # The API expects form data
        data = {
            "api": "SYNO.Foto.Browse.Album",
            "version": "1",
            "method": "get",
            "passphrase": self.passphrase,
            "additional": '["thumbnail"]',
        }

        try:
            async with self.session.post(api_url, data=data) as response:
                response.raise_for_status()
                result = await response.json()
                if result.get("success"):
                    return result.get("data", {})
        except Exception as e:
            _LOGGER.error("Failed to get album info: %s", e)
        
        return None

    async def get_photo_items(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Get photo items from the album."""
        if not self.passphrase:
            _LOGGER.error("No passphrase found in URL")
            return []

        api_url = f"{self.base_url}/mo/sharing/webapi/entry.cgi/SYNO.Foto.Browse.Item"
        
        data = {
            "api": "SYNO.Foto.Browse.Item",
            "version": "1",
            "method": "list",
            "passphrase": self.passphrase,
            "offset": str(offset),
            "limit": str(limit),
            "additional": '["thumbnail", "resolution", "orientation", "video_convert"]',
        }

        try:
            async with self.session.post(api_url, data=data) as response:
                response.raise_for_status()
                result = await response.json()
                if result.get("success"):
                    items = result.get("data", {}).get("list", [])
                    return items
        except Exception as e:
            _LOGGER.error("Failed to get photo items: %s", e)
        
        return []

    def get_photo_url(self, item: dict[str, Any], size: str = "xl") -> str | None:
        """Get the full URL for a photo item."""
        if not self.passphrase or not self.base_url:
            return None

        item_id = item.get("id")
        cache_key = item.get("cache_key", "")
        
        if not item_id:
            return None

        # Build thumbnail URL (we can use this to get the full image)
        # The API structure: /synofoto/api/v2/p/Thumbnail/get?id=...&passphrase=...&_sharing_id=...
        photo_url = (
            f"{self.base_url}/synofoto/api/v2/p/Thumbnail/get"
            f"?id={item_id}"
            f"&cache_key={cache_key}"
            f"&type=unit"
            f"&size={size}"
            f"&passphrase={self.passphrase}"
            f"&_sharing_id={self.passphrase}"
        )
        
        return photo_url

    async def get_all_photos(self) -> list[dict[str, Any]]:
        """Get all photos from the album."""
        all_photos = []
        offset = 0
        limit = 100

        while True:
            photos = await self.get_photo_items(limit=limit, offset=offset)
            if not photos:
                break
            
            all_photos.extend(photos)
            
            if len(photos) < limit:
                break
            
            offset += limit

        return all_photos

    async def get_photo_urls(self) -> list[str]:
        """Get all photo URLs from the sharing page."""
        photos = await self.get_all_photos()
        urls = []
        
        for photo in photos:
            url = self.get_photo_url(photo, size="xl")
            if url:
                urls.append(url)
        
        return urls

