"""The Synology Photo Sync integration."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import voluptuous as vol
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv

from .sync_client import SynologyPhotoSyncClient
from .const import DOMAIN, DEFAULT_NAME, CONF_SOURCES, CONF_URL, CONF_FOLDER_NAME

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class RuntimeData:
    """Runtime data for Synology Photo Sync integration."""

    sync_client: SynologyPhotoSyncClient
    sync_status: dict[str, Any] = field(default_factory=lambda: {
        "status": "idle",
        "last_sync": None,
        "last_error": None,
        "sources_synced": {},
    })
    logs: list[dict[str, Any]] = field(default_factory=list)


# Extend ConfigEntry to type hint runtime_data
type SynologyPhotoSyncConfigEntry = ConfigEntry[RuntimeData]


# Supported platforms
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Synology Photo Sync component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SynologyPhotoSyncConfigEntry) -> bool:
    """Set up Synology Photo Sync from a config entry."""
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    sources = entry.data.get(CONF_SOURCES, [])

    # Get data directory path
    data_dir = hass.config.path("synology_photo_sync")

    # Create sync client
    sync_client = SynologyPhotoSyncClient(hass, data_dir, sources)

    # Store runtime data
    entry.runtime_data = RuntimeData(sync_client=sync_client)

    # Create device registration
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "synology_photo_sync")},
        name=name,
        manufacturer="Synology",
        model="Photo Sync",
    )

    # Register services
    await _register_services(hass, entry)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _register_services(hass: HomeAssistant, entry: SynologyPhotoSyncConfigEntry) -> None:
    """Register device control services."""
    runtime_data = entry.runtime_data
    sync_client = runtime_data.sync_client

    def add_log(message: str, level: str = "info") -> None:
        """Add log entry (synchronous)."""
        log_entry = {
            "timestamp": datetime.now(),
            "level": level,
            "message": message,
        }

        runtime_data.logs.append(log_entry)
        # Keep only the latest 50 logs
        if len(runtime_data.logs) > 50:
            runtime_data.logs.pop(0)

    async def handle_sync_all(call: ServiceCall) -> None:
        """Handle sync all sources service."""
        runtime_data.sync_status["status"] = "running"
        runtime_data.sync_status["last_sync"] = datetime.now()
        runtime_data.sync_status["last_error"] = None

        add_log("Starting sync for all sources")
        try:
            result = await sync_client.sync_all()
            if result["success"]:
                runtime_data.sync_status["status"] = "completed"
                runtime_data.sync_status["sources_synced"] = result["sources"]
                add_log(f"Sync completed: {result['total_downloaded']} files downloaded")
            else:
                runtime_data.sync_status["status"] = "error"
                runtime_data.sync_status["last_error"] = result.get("error", "Unknown error")
                add_log(f"Sync failed: {result.get('error', 'Unknown error')}", "error")
        except Exception as e:
            runtime_data.sync_status["status"] = "error"
            runtime_data.sync_status["last_error"] = str(e)
            add_log(f"Sync error: {str(e)}", "error")
            _LOGGER.exception("Error during sync_all")

    async def handle_sync_source(call: ServiceCall) -> None:
        """Handle sync specific source service."""
        source_name = call.data.get("source_name")
        if not source_name:
            add_log("No source_name provided", "error")
            return

        runtime_data.sync_status["status"] = "running"
        runtime_data.sync_status["last_sync"] = datetime.now()
        runtime_data.sync_status["last_error"] = None

        add_log(f"Starting sync for source: {source_name}")
        try:
            result = await sync_client.sync_source(source_name)
            if result["success"]:
                runtime_data.sync_status["status"] = "completed"
                if source_name not in runtime_data.sync_status["sources_synced"]:
                    runtime_data.sync_status["sources_synced"][source_name] = {}
                runtime_data.sync_status["sources_synced"][source_name] = {
                    "last_sync": datetime.now().isoformat(),
                    "files_downloaded": result.get("files_downloaded", 0),
                }
                add_log(f"Sync completed for {source_name}: {result.get('files_downloaded', 0)} files downloaded")
            else:
                runtime_data.sync_status["status"] = "error"
                runtime_data.sync_status["last_error"] = result.get("error", "Unknown error")
                add_log(f"Sync failed for {source_name}: {result.get('error', 'Unknown error')}", "error")
        except Exception as e:
            runtime_data.sync_status["status"] = "error"
            runtime_data.sync_status["last_error"] = str(e)
            add_log(f"Sync error for {source_name}: {str(e)}", "error")
            _LOGGER.exception(f"Error during sync_source for {source_name}")

    # Register all services
    services = [
        ("sync_all", handle_sync_all, {}),
        ("sync_source", handle_sync_source, {
            vol.Required("source_name"): str,
        }),
    ]

    for service_name, handler, schema in services:
        hass.services.async_register(
            DOMAIN,
            service_name,
            handler,
            schema=vol.Schema(schema)
        )


async def async_unload_entry(hass: HomeAssistant, entry: SynologyPhotoSyncConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove services
        services_to_remove = [
            "sync_all",
            "sync_source",
        ]
        for service in services_to_remove:
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)

    return unload_ok

