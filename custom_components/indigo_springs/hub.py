"""Integration point for all Indigo Springs devices."""

import json
import logging

from homeassistant import core as ha
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import URL_API
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.http import HomeAssistantView, HTTPStatus, web

from .sample import Sample
from .sensor import Device

_LOGGER = logging.getLogger(__name__)


class Hub:
    """Handle interactions with custom-written sensors."""

    _add_entities: AddEntitiesCallback | None = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry | None = None) -> None:
        """Create a new server instance."""

        super().__init__()
        self.hass = hass
        self.entry = entry
        hass.http.register_view(APIIndigoSamplesView(self))

        self.devices: dict[str, Device] = {}

    def set_add_entities_callback(self, cb: AddEntitiesCallback) -> None:
        """Save away the routine to call when we've got new devices."""
        self._add_entities = cb

    async def async_add(self, device: Device) -> None:
        """Add a new device, along with its sensors."""

        self.devices[device.sn] = device
        await device.async_add_to_hass(self.entry.entry_id)
        if self._add_entities:
            self._add_entities(device.entities)

    def update_sensor_value(self, reading: Sample) -> None:
        """Handle new readings."""
        if not reading.sn:
            return

        _LOGGER.info(reading)

        device: Device = None
        if reading.sn in self.devices:
            device = self.devices[reading.sn]
        else:
            _LOGGER.info(f"Add new device: {reading.sn}")  # noqa: G004
            device = Device(self.hass, reading)
            self.hass.add_job(self.async_add.__get__(self, self.__class__), device)

        self.hass.add_job(
            device.async_update_state.__get__(device, device.__class__), reading
        )


class APIIndigoSamplesView(HomeAssistantView):
    """View to handle Status requests."""

    url = URL_API + "indigo-springs/samples"
    name = "indigo-springs:samples"

    def __init__(self, hub: Hub) -> None:
        """Initialize the view."""
        super().__init__()
        self.hub = hub

    @ha.callback
    def get(self, request: web.Request) -> web.Response:
        """Get status of the service."""
        return self.json({"status": "OK"})

    @ha.callback
    async def post(self, request: web.Request) -> web.Response:
        """Add a sample."""
        body = await request.text()
        try:
            data = json.loads(body) if body else None
        except ValueError:
            return self.json_message(
                "Data should be valid JSON.", HTTPStatus.BAD_REQUEST
            )
        if not data:
            return self.json({"status": "error", "message": "No data"}, status=400)
        if "sn" not in data:
            return self.json({"status": "error", "message": "No SN"}, status=400)

        sample = Sample(**data)
        self.hub.update_sensor_value(sample)
        return self.json({"status": "OK", "sn": f"{sample.sn}"})
