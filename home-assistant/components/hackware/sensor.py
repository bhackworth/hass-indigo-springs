"""Hackware sensors."""

from __future__ import annotations

import logging
import random

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .const import DOMAIN
from .HackHubServer import Sample

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> bool:
    """Set up our sensors."""

    hub = entry.runtime_data

    hub.set_add_entities_callback(add_entities)

    for sn in ["418224"]:
        await hub.async_add(Device(hass, sn))

    # _LOGGER.info(f"Add {len(hub.get_entities())} hackware sensor entities")
    # add_entities(hub.get_entities())

    return True


class Device(Entity):
    """Base class for all of our devices."""

    temperature = None
    moisture = None

    should_poll = False
    entity_description = EntityDescription(
        key="hackware", name="Hackware Device", icon="mdi:hub-outline"
    )

    def __init__(self, hass: HomeAssistant, name: str) -> None:
        """Initialize the device that contains some sensors."""

        # self._attr_device_info["name"] = name

        self.unique_id = name
        self.hass = hass
        self.name = "Brian moisture probe"
        self._attr_icon = "mdi:hub-outline"
        self.OBSOLETE_attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="Hackworth",
            # model="PR-01",
            model_id="PROBE-01",
            name=self.name,
            # serial_number="0123",
            sw_version="0.1",
            hw_version="0.1",
        )
        self._attr_state = "online"
        self.entities: list[Entity] = [
            HackwareMoistureSensor(self),
            HackwareTempSensor(self),
        ]

    async def async_update_state(self, sample: Sample) -> None:
        """Update values with a new sample."""
        self.temperature = sample.temperature
        self.moisture = sample.moisture
        if self.hass:
            _LOGGER.info(f"Updating {len(self.entities)} values for {self.unique_id}")
            for s in list(self.entities):
                s.async_write_ha_state()

    async def async_add_to_hass(self, entry_id: str) -> None:
        """Add this device to HA."""
        device_registry = dr.async_get(self.hass)

        device_registry.async_get_or_create(
            config_entry_id=entry_id,
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="Hackworth",
            name="Brian moisture probe",
            model="PROBE",
            model_id="PROBE-01",
            serial_number=self.unique_id,
            sw_version="0.1",
            hw_version="0.1",
        )
        # self.platform.async_add_entities(self.get_entities())


class SensorBase(SensorEntity):
    """Base class for all of our sensors."""

    should_poll = False
    platform = Platform.SENSOR

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""
        self.device = device
        self.hass = device.hass

    @property
    def device_info(self) -> DeviceInfo:
        """Return information to link this entity with a device."""
        return DeviceInfo(identifiers={(DOMAIN, self.device.unique_id)})

    @property
    def available(self) -> bool:
        """Return whether this sensor is available."""
        return True


class HackwareMoistureSensor(SensorBase):
    """Representation of a moisture or moisture sensor."""

    device_class = SensorDeviceClass.HUMIDITY
    _attr_icon = "mdi:water-percent"
    _attr_unit_of_measurement = PERCENTAGE

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_moisture"
        self.name = "Soil moisture"

    @property
    def state(self) -> int:
        """Return the state of the sensor (a percentage)."""
        return self.device.moisture


class HackwareTempSensor(SensorBase):
    """Representation of a temperature sensor."""

    device_class = SensorDeviceClass.TEMPERATURE
    _attr_icon = "mdi:home-thermometer-outline"
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_temperature"
        self.name = "Temperature"

    @property
    def state(self) -> int:
        """Return the state of the sensor (a percentage)."""
        return self.device.temperature
