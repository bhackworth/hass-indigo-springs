"""Integration point for all Hackware devices."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .sensor import Device
from .service import HubServer, Sample

_LOGGER = logging.getLogger(__name__)


class HackHub:
    """Handle interactions with custom-written sensors."""

    _add_entities: AddEntitiesCallback | None = None

    def __init__(
        self, hass: HomeAssistant, port: int = 8234, entry: ConfigEntry | None = None
    ) -> None:
        """Create a new server instance."""
        super().__init__()
        self.hass = hass
        self.entry = entry
        _LOGGER.info(f"Starting Hackware server on port {port}")  # noqa: G004
        self.server = HubServer(port)
        # Bind the callback to this instance of the hub.
        self.server.add_callback(self.update_sensor_value.__get__(self, self.__class__))
        self.devices: dict[str, Device] = {}

    def start(self) -> None:
        """Start the hub."""
        self.server.start()

    def is_started(self) -> bool:
        """Determine if the hub started."""
        return self.server.is_alive()

    def stop(self):
        """Stop the hub."""
        _LOGGER.info("Stopping the HackHubServer")
        self.server.stop()

    def set_add_entities_callback(self, cb: AddEntitiesCallback) -> None:
        """Save away the routine to call when we've got new devices."""
        self._add_entities = cb

    async def async_add(self, device: Device) -> None:
        """Add a new device, along with its sensors."""

        self.devices[device.unique_id] = device
        await device.async_add_to_hass(self.entry.entry_id)
        if self._add_entities:
            self._add_entities(device.entities)

    def update_sensor_value(self, reading: Sample, cbdata) -> None:
        """Handle new readings."""
        if not reading.sensor:
            return

        device: Device = None
        if reading.sensor in self.devices:
            _LOGGER.info(reading)
            device = self.devices[reading.sensor]
        else:
            _LOGGER.info(f"Add new device: {reading.sensor}")  # noqa: G004
            device = Device(self.hass, reading.sensor)
            self.hass.add_job(self.async_add.__get__(self, self.__class__), device)

        self.hass.add_job(
            device.async_update_state.__get__(device, device.__class__), reading
        )
