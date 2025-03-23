"""Hackware sensors."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .const import DOMAIN
from .service import Sample

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> bool:
    """Set up our sensors."""

    hub = entry.runtime_data

    hub.set_add_entities_callback(add_entities)

    return True


class Device(Entity):
    """Base class for all of our devices."""

    temperature = None
    humidity = None
    moisture = None
    battery = None

    should_poll = False
    entity_description = EntityDescription(
        key="hackware", name="Hackware Device", icon="mdi:hub-outline"
    )

    def __init__(self, hass: HomeAssistant, sample: Sample) -> None:
        """Initialize the device that contains some sensors."""

        self.sn = sample.sn
        self.temperature = sample.temperature
        self.humidity = sample.humidity
        self.moisture = sample.moisture
        self.battery = sample.battery
        self.unique_id = f"probe_{self.sn}"
        self.hass = hass
        self.name = f"Probe {self.sn}"
        self._attr_icon = "mdi:hub-outline"
        self._attr_state = "online"
        self.entities: list[Entity] = [
            HackwareMoistureSensor(self),
            HackwareTempSensor(self),
            HackwareHumiditySensor(self),
            HackwareBatterySensor(self),
        ]

    async def async_update_state(self, sample: Sample) -> None:
        """Update values with a new sample."""
        self.temperature = sample.temperature
        self.humidity = sample.humidity
        self.moisture = sample.moisture
        self.battery = sample.battery

        for s in list(self.entities):
            s.async_write_ha_state()

    async def async_add_to_hass(self, entry_id: str) -> None:
        """Add this device to HA."""
        device_registry = dr.async_get(self.hass)

        device_registry.async_get_or_create(
            config_entry_id=entry_id,
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="Hackworth",
            name=self.name,
            model="PROBE",
            model_id="PROBE-01",
            serial_number=self.sn,
            sw_version="0.1",
            hw_version="0.1",
        )


class SensorBase(SensorEntity):
    """Base class for all of our sensors."""

    should_poll = False
    platform = Platform.SENSOR
    _attr_has_entity_name = True

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""
        self.device = device

    @property
    def device_info(self) -> DeviceInfo:
        """Return information to link this entity with a device."""
        return DeviceInfo(identifiers={(DOMAIN, self.device.unique_id)})

    @property
    def available(self) -> bool:
        """Return whether this sensor is available."""
        return True


class HackwareMoistureSensor(SensorBase):
    """Representation of a soil moisture sensor."""

    device_class = SensorDeviceClass.HUMIDITY
    _attr_icon = "mdi:water-percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1
    _attr_name = "Soil moisture"

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_moisture"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor (a percentage)."""
        return self.device.moisture


class HackwareHumiditySensor(SensorBase):
    """Representation of a relative humidity sensor."""

    device_class = SensorDeviceClass.HUMIDITY
    _attr_icon = "mdi:water-percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1
    _attr_name = "Humidity"

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_humidity"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor (a percentage)."""
        return self.device.humidity


class HackwareTempSensor(SensorBase):
    """Representation of a battery sensor."""

    device_class = SensorDeviceClass.TEMPERATURE
    _attr_icon = "mdi:home-thermometer-outline"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 0
    _attr_name = "Temperature"

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_temperature"

    @property
    def native_value(self) -> float:
        """Return the temperature."""
        return self.device.temperature


class HackwareBatterySensor(SensorBase):
    """Representation of a battery sensor."""

    device_class = SensorDeviceClass.BATTERY
    _attr_icon = "mdi:battery"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0
    _attr_name = "Battery"

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_battery"

    @property
    def native_value(self) -> float:
        """Return the battery level."""
        return self.device.battery
