"""Integration point for all Hackware devices."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .HackHubServer import HackHubServer, Sample
from .sensor import Device

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
        self.server = HackHubServer(port)
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

    def get_entities(self) -> list[Entity]:
        """Return a list of all the entities we know about."""
        entities: list[Entity] = []
        for d in self.devices.values():
            entities.extend(d.entities)

        return entities

    def set_add_entities_callback(self, cb: AddEntitiesCallback) -> None:
        """Save away the routine to call when we've got new devices."""
        self._add_entities = cb

    async def async_add(self, device: Device) -> None:
        """Add a new device, along with its sensors."""

        _LOGGER.info(f"Device.async_add({device.unique_id}) to {self.entry.entry_id}")
        self.devices[device.unique_id] = device
        await device.async_add_to_hass(self.entry.entry_id)
        if self._add_entities:
            self._add_entities(device.entities)

        # await self.hass.config_entries.async_forward_entry_unload(
        # self.entry, [Platform.SENSOR])
        # await self.hass.config_entries.async_forward_entry_setups(
        # self.entry, [Platform.SENSOR]
        # )
        #
        # if self._add_entities:
        # _LOGGER.info(
        # f"Adding {len(device.get_entities())} entities to {device.unique_id}"
        # )
        # self._add_entities(device.get_entities())

    def update_sensor_value(self, reading: Sample, cbdata) -> None:
        """Handle new readings."""
        if not reading.sensor:
            return

        device: Device = None
        if reading.sensor in self.devices:
            _LOGGER.info(f"Got new value: {reading}. Notify HA.")  # noqa: G004
            device = self.devices[reading.sensor]
        else:
            _LOGGER.info(f"Got new device: {reading.sensor}. Add it.")  # noqa: G004
            device = Device(self.hass, reading.sensor)
            self.hass.add_job(self.async_add.__get__(self, self.__class__), device)

        self.hass.add_job(
            device.async_update_state.__get__(device, device.__class__), reading
        )
