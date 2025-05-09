"""Indigo Springs sensors."""

from __future__ import annotations
from enum import Enum

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform

from .const import DOMAIN
from .sample import Sample

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> bool:
    """Set up our sensors."""

    hub = entry.runtime_data
    hub.set_add_entities_callback(add_entities)
    return True


class HealthStates(Enum):
    """Health states for the device."""

    HEALTHY = "Healthy"
    UNHEALTHY = "Unhealthy"
    UNKNOWN = "Unknown"

    def __str__(self) -> str:
        """Return the string representation of the state."""
        return self.value


class Device(Entity):
    """Base class for all of our devices."""

    temperature = None
    humidity = None
    moisture = None
    battery = None
    solar = None
    rssi = None
    attempts = None
    errors = None
    health = HealthStates.UNKNOWN

    should_poll = False

    entity_description = EntityDescription(
        key="indigo",
        name="Indigo Springs Device",
        icon="mdi:hub-outline",
        has_entity_name=True,
    )

    def __init__(self, hass: HomeAssistant, sample: Sample) -> None:
        """Initialize the device that contains some sensors."""

        self.sn = sample.sn
        self.hw = sample.hw
        self.sw = sample.sw
        self.temperature = sample.temperature
        self.humidity = sample.humidity
        self.moisture = sample.moisture
        self.solar = sample.solar
        self.battery = sample.battery
        self.rssi = sample.rssi
        self.attempts = sample.attempts
        self.errors = sample.errors
        self.health = HealthStates.HEALTHY
        self.unique_id = f"probe_{self.sn}"
        self.hass = hass
        self.name = f"Probe {self.sn}"
        self._attr_icon = "mdi:hub-outline"
        self._attr_state = "online"
        self.entities: list[Entity] = []
        if self.temperature is not None:
            self.entities.append(IndigoTempSensor(self))
        if self.humidity is not None:
            self.entities.append(IndigoHumiditySensor(self))
        if self.battery is not None:
            self.entities.append(IndigoBatterySensor(self))
        if self.moisture is not None:
            self.entities.append(IndigoMoistureSensor(self))
        if self.solar is not None:
            self.entities.append(IndigoSolarSensor(self))
        if self.rssi is not None:
            self.entities.append(IndigoSignalSensor(self))
        if self.attempts is not None:
            self.entities.append(IndigoHealthSensor(self))

    async def async_update_state(self, sample: Sample) -> None:
        """Update values with a new sample."""
        self.temperature = sample.temperature
        self.humidity = sample.humidity
        self.moisture = sample.moisture
        self.battery = sample.battery
        self.solar = sample.solar
        self.sw = sample.sw
        self.hw = sample.hw
        self.rssi = sample.rssi

        if sample.errors > self.errors:
            _LOGGER.warning(
                "Device %s has %d new connection errors",
                self.sn,
                sample.errors - self.errors,
            )
            self.health = HealthStates.UNHEALTHY
        else:
            self.health = HealthStates.HEALTHY
        self.attempts = sample.attempts
        self.errors = sample.errors

        for s in list(self.entities):
            s.async_write_ha_state()

    async def async_add_to_hass(self, entry_id: str) -> None:
        """Add this device to HA."""
        device_registry = dr.async_get(self.hass)

        device_registry.async_get_or_create(
            config_entry_id=entry_id,
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="Indigo Springs",
            name=self.name,
            model="PROBE",
            model_id="PROBE-01",
            serial_number=self.sn,
            sw_version=self.sw,
            hw_version=self.hw,
        )


class SensorBase(SensorEntity):
    """Base class for all of our sensors."""

    should_poll = False
    platform = Platform.SENSOR
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

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


class IndigoMoistureSensor(SensorBase):
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


class IndigoHumiditySensor(SensorBase):
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


class IndigoTempSensor(SensorBase):
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


class IndigoBatterySensor(SensorBase):
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


class IndigoSolarSensor(SensorBase):
    """Representation of a solar charger."""

    device_class = SensorDeviceClass.VOLTAGE
    _attr_icon = "mdi:solar-power"
    _attr_native_unit_of_measurement = "mV"
    _attr_suggested_display_precision = 0
    _attr_name = "Solar charger"

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_solar"

    @property
    def native_value(self) -> float:
        """Return the solar panel output voltage."""
        return self.device.solar


class IndigoSignalSensor(SensorBase):
    """Representation of a Wi-Fi signal strength."""

    device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_icon = "mdi:wifi"
    _attr_native_unit_of_measurement = "dBm"
    _attr_suggested_display_precision = 0
    _attr_name = "Signal strength"

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_rssi"

    @property
    def native_value(self) -> int:
        """Return the Wi-Fi signal strength."""
        return self.device.rssi


class IndigoHealthSensor(SensorBase):
    """Representation of the device's connection health."""

    device_class = SensorDeviceClass.ENUM
    _attr_state_class = None
    _attr_icon = "mdi:wifi"
    _attr_name = "Connection health"

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""

        super().__init__(device)
        self.unique_id = f"{device.unique_id}_connection"

    @property
    def native_value(self) -> str:
        """Return the connection health."""
        return self.device.health.value
