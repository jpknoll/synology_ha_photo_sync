"""Config flow for Synology Photo Sync integration."""
from __future__ import annotations

import json
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

# ConfigFlowResult is available in newer Home Assistant versions
try:
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:
    # Fallback for older versions
    ConfigFlowResult = dict

from .const import DOMAIN, CONF_SOURCES, CONF_URL, CONF_FOLDER_NAME, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input."""
    sources = data.get(CONF_SOURCES, [])
    
    if not sources:
        raise InvalidInput("At least one source must be configured")
    
    # Validate each source
    for source in sources:
        url = source.get(CONF_URL, "")
        folder_name = source.get(CONF_FOLDER_NAME, "")
        
        if not url:
            raise InvalidInput("Each source must have a URL")
        if not folder_name:
            raise InvalidInput("Each source must have a folder name")
        
        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            raise InvalidInput(f"Invalid URL format: {url}")
    
    return {"title": data.get("name", DEFAULT_NAME)}


class SynologyPhotoSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Synology Photo Sync."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Parse sources JSON if provided as string
                sources = user_input.get(CONF_SOURCES, [])
                if isinstance(sources, str):
                    try:
                        sources = json.loads(sources)
                    except json.JSONDecodeError:
                        raise InvalidInput("Invalid JSON format for sources")
                
                # Ensure sources is a list
                if not isinstance(sources, list):
                    sources = [sources] if sources else []
                
                # Validate and format sources
                validated_sources = []
                for source in sources:
                    if isinstance(source, dict):
                        validated_sources.append({
                            CONF_URL: source.get(CONF_URL, ""),
                            CONF_FOLDER_NAME: source.get(CONF_FOLDER_NAME, ""),
                        })
                
                user_input[CONF_SOURCES] = validated_sources
                
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input
                )
            except InvalidInput as err:
                errors["base"] = str(err)
            except Exception as err:
                _LOGGER.exception("Unexpected error during config flow: %s", err)
                errors["base"] = "unknown"

        # Build schema - allow JSON string for sources
        schema_dict = {
            vol.Required("name", default=DEFAULT_NAME): str,
            vol.Required(
                CONF_SOURCES,
                default='[{"url": "", "folder_name": ""}]'
            ): str,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "sources_help": "Enter sources as JSON array. Example: [{\"url\": \"https://example.com/sharing/abc\", \"folder_name\": \"photos\"}]"
            },
            errors=errors,
        )

    async def async_step_import(self, import_info: dict) -> ConfigFlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_info)


class InvalidInput(HomeAssistantError):
    """Error to indicate invalid user input."""

