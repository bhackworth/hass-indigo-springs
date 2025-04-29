"""The sensorhub integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .hub import Hub

_LOGGER = logging.getLogger(__name__)

_PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the entries we know about."""

    hub = Hub(hass, entry)
    entry.runtime_data = hub
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the configuration."""

    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
