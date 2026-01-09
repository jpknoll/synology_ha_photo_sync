"""Media source for Synology Photo Album."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import media_source
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .scraper import SynologyPhotoScraper

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> SynologyPhotoMediaSource:
    """Set up Synology Photo Album media source."""
    return SynologyPhotoMediaSource(hass)


class SynologyPhotoMediaSource(MediaSource):
    """Synology Photo Album media source."""

    name: str = "Synology Photo Album"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media to a playable URL."""
        # Extract the photo URL from the media identifier
        photo_url = item.identifier
        
        return PlayMedia(photo_url, "image/jpeg")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse media."""
        if item.identifier:
            # This shouldn't happen for our use case, but handle it
            return self._create_item(item.identifier, item.identifier, True)

        # Get the sharing URL from config entry
        config_entries = self.hass.config_entries.async_entries(DOMAIN)
        if not config_entries:
            return self._create_error_item("No configuration found")

        config_entry = config_entries[0]
        # Try to get from entry data, fallback to options
        sharing_url = config_entry.data.get("sharing_url") or config_entry.options.get("sharing_url")
        
        if not sharing_url:
            return self._create_error_item("No sharing URL configured")

        # Create root item
        root = BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class="directory",
            media_content_type="image",
            title="Synology Photo Album",
            can_play=False,
            can_expand=True,
            children=[],
        )

        # Fetch photos
        try:
            session = async_get_clientsession(self.hass)
            scraper = SynologyPhotoScraper(sharing_url, session)
            photos = await scraper.get_all_photos()
            
            children = []
            for photo in photos:
                photo_id = str(photo.get("id", ""))
                photo_url = scraper.get_photo_url(photo, size="xl")
                if photo_url:
                    title = photo.get("filename", f"Photo {photo_id}")
                    children.append(
                        self._create_item(
                            photo_url,
                            title,
                            False,
                            thumbnail=scraper.get_photo_url(photo, size="sm"),
                        )
                    )
            
            root.children = children
        except Exception as e:
            _LOGGER.error("Error browsing media: %s", e)
            return self._create_error_item(f"Error loading photos: {str(e)}")

        return root

    def _create_item(
        self,
        identifier: str,
        title: str,
        can_expand: bool,
        thumbnail: str | None = None,
    ) -> BrowseMediaSource:
        """Create a media item."""
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class="image" if not can_expand else "directory",
            media_content_type="image/jpeg",
            title=title,
            can_play=not can_expand,
            can_expand=can_expand,
            thumbnail=thumbnail,
        )

    def _create_error_item(self, message: str) -> BrowseMediaSource:
        """Create an error item."""
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class="directory",
            media_content_type="image",
            title=f"Error: {message}",
            can_play=False,
            can_expand=False,
            children=[],
        )

