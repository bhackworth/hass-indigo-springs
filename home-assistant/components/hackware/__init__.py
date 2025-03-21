"""The sensorhub integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .HackHub import HackHub

_LOGGER = logging.getLogger(__name__)

_PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the entries we know about."""
    _LOGGER.info("In async_setup_entry for Hackware")
    hub = HackHub(hass, entry.data[CONF_PORT], entry)
    hub.start()
    if not hub.is_started():
        raise ConfigEntryNotReady("Can't start the Hackware hub")

    entry.runtime_data = hub
    cancel = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, hub.stop)
    cancel()

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the configuration."""
    _LOGGER.info("Unloading hackware")
    hub = entry.runtime_data
    hub.stop()
    # await hub.async_unload_entities()
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
