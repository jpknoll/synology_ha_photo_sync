"""Support for Synology Photo Sync sensors."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Synology Photo Sync sensors."""
    name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)

    sensors = [
        SynologySyncStatusSensor(hass, config_entry, name),
        SynologyLastSyncSensor(hass, config_entry, name),
        SynologyFilesDownloadedSensor(hass, config_entry, name),
    ]

    async_add_entities(sensors, True)


class SynologyBaseSensor(SensorEntity):
    """Base class for Synology Photo Sync sensors."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "synology_photo_sync")},
            name=self._device_name,
            manufacturer="Synology",
            model="Photo Sync",
        )

    def _get_sync_status(self) -> dict | None:
        """Get sync status from shared runtime data."""
        runtime_data = self._config_entry.runtime_data
        return runtime_data.sync_status


class SynologySyncStatusSensor(SynologyBaseSensor):
    """Sensor for sync status."""

    _attr_unique_id = "synology_photo_sync_status"
    _attr_translation_key = "sync_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the sync status sensor."""
        super().__init__(hass, config_entry, device_name)

    async def async_update(self) -> None:
        """Update the sensor state."""
        sync_status = self._get_sync_status()
        if sync_status:
            self._attr_native_value = sync_status.get("status", "idle")


class SynologyLastSyncSensor(SynologyBaseSensor):
    """Sensor for last sync time."""

    _attr_unique_id = "synology_photo_sync_last_sync"
    _attr_translation_key = "last_sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the last sync sensor."""
        super().__init__(hass, config_entry, device_name)

    async def async_update(self) -> None:
        """Update the sensor state."""
        sync_status = self._get_sync_status()
        if sync_status:
            last_sync = sync_status.get("last_sync")
            if last_sync:
                if isinstance(last_sync, datetime):
                    self._attr_native_value = last_sync.isoformat()
                else:
                    self._attr_native_value = last_sync
            else:
                self._attr_native_value = "Never"


class SynologyFilesDownloadedSensor(SynologyBaseSensor):
    """Sensor for total files downloaded."""

    _attr_unique_id = "synology_photo_sync_files_downloaded"
    _attr_translation_key = "files_downloaded"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_name: str) -> None:
        """Initialize the files downloaded sensor."""
        super().__init__(hass, config_entry, device_name)

    async def async_update(self) -> None:
        """Update the sensor state."""
        sync_status = self._get_sync_status()
        if sync_status:
            sources_synced = sync_status.get("sources_synced", {})
            total = 0
            for source_data in sources_synced.values():
                if isinstance(source_data, dict):
                    total += source_data.get("files_downloaded", 0)
            self._attr_native_value = total

